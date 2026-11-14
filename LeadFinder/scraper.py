import base64
import html
import re
from urllib.parse import unquote, urljoin, urlparse
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

CHALLENGE_KEYWORDS = [
    "checking your browser",
    "just a moment",
    "attention required",
    "cf-browser-verification",
    "cf-chl-bypass",
    "ddos-guard",
    "verifying you are human",
    "enable javascript and cookies",
    "please wait while your request is being verified",
]

SHORTENER_OR_REDIRECT_HINTS = [
    "wa.link", "bit.ly", "s.id", "linktr.ee", "cutt.ly", "tinyurl.com",
    "t.ly", "rebrand.ly", "is.gd", "lynk.id", "taplink.cc", "heylink.me",
    "bio.link", "/wa", "/whatsapp", "/chat", "/hubungi", "/konsultasi",
    "/order", "/cs", "/admin", "/go/", "/redirect"
]

CONTACT_PAGE_KEYWORDS = [
    "contact", "kontak", "hubungi", "about", "tentang",
    "lokasi", "cabang", "cs", "customer-service", "konsultasi", "order"
]

VALID_ID_CELLULAR_PREFIXES = {
    "11", "12", "13", "14", "15", "16", "17", "18", "19",
    "21", "22", "23",
    "31", "32", "33", "35", "38",
    "51", "52", "53", "55", "56", "57", "58", "59",
    "77", "78",
    "81", "82", "83", "84", "85", "86", "87", "88", "89",
    "95", "96", "97", "98", "99",
}

WA_URL_REGEX = re.compile(
    r'(?:wa\.me/|api\.whatsapp\.com/send\?[^"\'\s<>\)]*?phone=|web\.whatsapp\.com/send\?[^"\'\s<>\)]*?phone=|whatsapp://send\?[^"\'\s<>\)]*?phone=)(\+?[\d\s\-\(\)%2B]{8,25})',
    re.IGNORECASE
)

ID_MOBILE_REGEX = re.compile(
    r'(?<!\d)(?:\+62|62|0)[\s\-\.]?8[1-9][0-9][\s\-\.\(\)0-9]{6,14}(?!\d)'
)

DATE_OR_PRICE_FALSE_POSITIVE = re.compile(
    r'^(?:08[\-\/\.]\d{2}[\-\/\.]20\d{2}|0800|0804|0807|0809)'
)


def is_bot_challenge(html_text: str, status_code: int = 200) -> bool:
    """Mendeteksi apakah halaman tertahan verifikasi anti-bot / Cloudflare."""
    if not html_text:
        return True
    sample = html_text[:5000].lower()
    if any(kw in sample for kw in CHALLENGE_KEYWORDS):
        return True
    if status_code in (403, 503) and len(html_text) < 15000:
        return True
    return False


def normalize_and_validate_id_mobile(raw: str) -> str | None:
    """Membersihkan & memvalidasi ketat nomor seluler Indonesia ke format 628xxx."""
    if not raw:
        return None
    cleaned_raw = html.unescape(unquote(str(raw))).strip()
    if DATE_OR_PRICE_FALSE_POSITIVE.match(cleaned_raw):
        return None

    digits = re.sub(r'\D', '', cleaned_raw)

    if digits.startswith('08'):
        digits = '62' + digits[1:]
    elif digits.startswith('8') and 9 <= len(digits) <= 13:
        digits = '62' + digits

    if not digits.startswith('628') or not (11 <= len(digits) <= 14):
        return None
    if digits.startswith('6280'):
        return None
    if digits[3:5] not in VALID_ID_CELLULAR_PREFIXES:
        return None
    if len(set(digits[3:])) <= 2:
        return None

    return digits


class LeadCollector:
    """Menyimpan kontak WA unik beserta status verifikasi & sumber deteksinya."""

    def __init__(self):
        self.items: dict[str, dict] = {}

    def add(self, raw_num: str, source: str, verified: bool, confidence: int = 50):
        norm = normalize_and_validate_id_mobile(raw_num)
        if not norm:
            return

        score = 100 if verified else confidence
        if norm not in self.items:
            self.items[norm] = {
                "number": norm,
                "display": f"+{norm[:2]} {norm[2:5]}-{norm[5:9]}-{norm[9:]}",
                "wa_link": f"https://wa.me/{norm}",
                "source": source,
                "verified": verified,
                "_score": score,
            }
        else:
            existing = self.items[norm]
            if (verified and not existing["verified"]) or score > existing["_score"]:
                existing["verified"] = verified or existing["verified"]
                existing["source"] = source
                existing["_score"] = max(existing["_score"], score)

    def to_list(self) -> list[dict]:
        ordered = sorted(
            self.items.values(),
            key=lambda x: (not x["verified"], -x["_score"], x["number"])
        )
        return [
            {
                "number": item["number"],
                "display": item["display"],
                "wa_link": item["wa_link"],
                "source": item["source"],
                "verified": item["verified"],
            }
            for item in ordered
        ]

    def has_verified(self) -> bool:
        return any(item["verified"] for item in self.items.values())


def resolve_potential_wa_redirect(target_url: str, session: requests.Session) -> str | None:
    """Mengikuti redirect dari shortlink (bit.ly, wa.link, s.id, /wa) ke nomor WA tujuan."""
    try:
        resp = session.get(target_url, headers=HEADERS, timeout=5, allow_redirects=True)
        chain_urls = [r.url for r in resp.history] + [resp.url]

        for u in chain_urls:
            for match in WA_URL_REGEX.findall(unquote(u)):
                norm = normalize_and_validate_id_mobile(match)
                if norm:
                    return norm

        snippet = html.unescape(unquote(resp.text[:4000]))
        for match in WA_URL_REGEX.findall(snippet):
            norm = normalize_and_validate_id_mobile(match)
            if norm:
                return norm
    except Exception:
        pass
    return None


def decode_possible_base64_tokens(text: str) -> str:
    """Mendekode token Base64 yang dipakai plugin WA untuk menyembunyikan nomor."""
    decoded_chunks = []
    for token in re.findall(r'[A-Za-z0-9+/=]{16,120}', text):
        if len(token) % 4 != 0:
            continue
        try:
            raw_bytes = base64.b64decode(token, validate=True)
            decoded_str = raw_bytes.decode('utf-8', errors='ignore')
            if any(k in decoded_str.lower() for k in ['wa.me', 'whatsapp', '628', '08']):
                decoded_chunks.append(decoded_str)
        except Exception:
            continue
    return " ".join(decoded_chunks)


def scan_html_for_contacts(
    raw_html: str,
    base_url: str,
    collector: LeadCollector,
    session: requests.Session,
    page_suffix: str = "",
    follow_redirects: bool = True,
):
    """Memindai tautan <a>, gambar/banner link, atribut data-*/onclick, script widget, Base64, dan teks."""
    unescaped_html = html.unescape(raw_html)
    soup = BeautifulSoup(unescaped_html, 'html.parser')
    redirect_candidates = []

    # 1. Pindai seluruh tag <a> (termasuk tautan di balik gambar/ikon/banner)
    for a_tag in soup.find_all('a', href=True):
        raw_href = str(a_tag.get('href', '')).strip()
        href_decoded = unquote(raw_href)
        has_media = bool(a_tag.find(['img', 'svg', 'i', 'picture']))

        img_tag = a_tag.find('img')
        img_meta = (
            f"{img_tag.get('alt', '')} {img_tag.get('title', '')} {img_tag.get('src', '')} {' '.join(img_tag.get('class', []))}"
            if img_tag else ""
        )
        a_context = (
            f"{a_tag.get_text(' ', strip=True)} {a_tag.get('title', '')} "
            f"{a_tag.get('aria-label', '')} {' '.join(a_tag.get('class', []))} {a_tag.get('id', '')} {img_meta}"
        ).lower()

        is_wa_context = any(
            k in a_context
            for k in ['wa', 'whatsapp', 'chat', 'hubungi', 'konsultasi', 'cs', 'admin', 'sales', 'marketing']
        )
        label_base = "Gambar / Banner WA" if has_media else "Link WhatsApp"

        matched_direct = False
        for match in WA_URL_REGEX.findall(href_decoded):
            collector.add(match, f"{label_base}{page_suffix}", verified=True, confidence=100)
            matched_direct = True

        if not matched_direct:
            if href_decoded.lower().startswith('tel:'):
                collector.add(
                    href_decoded[4:],
                    f"{'Gambar Tel' if has_media else 'Link Tel'}{page_suffix}",
                    verified=is_wa_context,
                    confidence=85 if is_wa_context else 65
                )
            elif is_wa_context:
                for match in ID_MOBILE_REGEX.findall(href_decoded):
                    collector.add(match, f"{label_base}{page_suffix}", verified=True, confidence=95)

        if follow_redirects and not matched_direct and raw_href and not raw_href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            full_href = urljoin(base_url, raw_href)
            if is_wa_context or any(hint in full_href.lower() for hint in SHORTENER_OR_REDIRECT_HINTS):
                if full_href not in redirect_candidates:
                    redirect_candidates.append(full_href)

    # 2. Ikuti redirect shortlink (maksimal 6 per halaman agar tetap cepat di Vercel)
    if follow_redirects:
        for cand_url in redirect_candidates[:6]:
            resolved_num = resolve_potential_wa_redirect(cand_url, session)
            if resolved_num:
                collector.add(resolved_num, f"Redirect / Shortlink WA{page_suffix}", verified=True, confidence=100)

    # 3. Pindai atribut onclick & data-* pada semua elemen
    target_attrs = [
        'onclick', 'data-phone', 'data-wa', 'data-whatsapp', 'data-number',
        'data-href', 'data-url', 'data-link', 'data-target', 'data-settings',
        'data-tel', 'data-mobile', 'data-contact'
    ]
    for tag in soup.find_all(True):
        tag_classes = ' '.join(tag.get('class', [])).lower()
        tag_id = str(tag.get('id', '')).lower()
        is_wa_widget = any(
            w in f"{tag_classes} {tag_id}"
            for w in [
                'wa', 'whatsapp', 'joinchat', 'ht-ctc', 'qlwapp', 'floating-wpp',
                'elfsight', 'getbutton', 'qontak', 'wati', 'sleekflow', 'buttonizer'
            ]
        )

        for attr in target_attrs:
            val = tag.get(attr)
            if not val:
                continue
            val_str = html.unescape(unquote(str(val)))
            decoded_b64 = decode_possible_base64_tokens(val_str)
            combined_val = f"{val_str} {decoded_b64}"

            src_label = (
                f"Atribut Gambar{page_suffix}" if tag.name in ['img', 'svg']
                else f"Widget / Atribut{page_suffix}"
            )

            for match in WA_URL_REGEX.findall(combined_val):
                collector.add(match, src_label, verified=True, confidence=100)

            if is_wa_widget or any(k in attr for k in ['wa', 'whatsapp', 'phone', 'mobile']) or 'whatsapp' in combined_val.lower():
                for match in ID_MOBILE_REGEX.findall(combined_val):
                    collector.add(match, src_label, verified=True, confidence=95)

    # 4. Pindai <script> inline, JSON-LD, __NEXT_DATA__, & Base64 dalam script
    for script in soup.find_all('script'):
        if not script.string:
            continue
        script_str = html.unescape(unquote(script.string))
        decoded_b64 = decode_possible_base64_tokens(script_str)
        full_script = f"{script_str} {decoded_b64}"

        for match in WA_URL_REGEX.findall(full_script):
            collector.add(match, f"Widget / Script WA{page_suffix}", verified=True, confidence=100)

        if any(k in full_script.lower() for k in [
            'whatsapp', 'joinchat', 'ht_ctc', 'qlwapp', 'wa_number',
            'whatsappnumber', 'qontak', 'wati', 'sleekflow', 'telephone'
        ]):
            for m in re.finditer(ID_MOBILE_REGEX, full_script):
                start = max(0, m.start() - 90)
                end = min(len(full_script), m.end() + 90)
                window_ctx = full_script[start:end].lower()
                if any(w in window_ctx for w in ['wa', 'whatsapp', 'phone', 'telephone', 'number', 'chat', 'mobile']):
                    is_explicit_wa = any(w in window_ctx for w in ['wa', 'whatsapp', 'joinchat', 'ht_ctc', 'qlwapp'])
                    collector.add(
                        m.group(0),
                        f"Config Widget WA{page_suffix}" if is_explicit_wa else f"Schema / JSON Kontak{page_suffix}",
                        verified=is_explicit_wa,
                        confidence=95 if is_explicit_wa else 75
                    )

    # 5. Pindai teks bersih halaman dengan analisis konteks sekitar
    clean_text = " ".join(soup.get_text(separator=' ').split())
    for m in re.finditer(ID_MOBILE_REGEX, clean_text):
        start = max(0, m.start() - 75)
        end = min(len(clean_text), m.end() + 75)
        surrounding = clean_text[start:end].lower()

        has_wa_keyword = bool(re.search(r'\b(?:wa|w\.a|whatsapp|whats\s*app)\b', surrounding))
        has_contact_keyword = bool(re.search(r'\b(?:hubungi|kontak|contact|telp|telepon|hp|mobile|cs|admin|sales|marketing|konsultasi)\b', surrounding))

        if has_wa_keyword:
            collector.add(m.group(0), f"Teks Terlabel WA{page_suffix}", verified=True, confidence=95)
        elif has_contact_keyword:
            collector.add(m.group(0), f"Nomor HP Kontak{page_suffix}", verified=False, confidence=70)
        else:
            collector.add(m.group(0), f"Nomor HP Halaman{page_suffix}", verified=False, confidence=45)


def fetch_via_cloud_reader(target_url: str, session: requests.Session) -> tuple[str | None, str | None]:
    """
    Zero-config cloud headless reader fallback (tanpa API key & tanpa browser lokal)
    untuk menembus situs anti-bot / Cloudflare dan merender JS langsung di server Vercel.
    """
    reader_url = f"https://r.jina.ai/{target_url}"
    reader_headers = {
        "User-Agent": HEADERS["User-Agent"],
        "X-With-Links-Summary": "true",
    }
    try:
        resp = session.get(reader_url, headers=reader_headers, timeout=18)
        if resp.status_code == 200 and len(resp.text) > 200 and not is_bot_challenge(resp.text):
            title_match = re.search(r'^Title:\s*(.+)$', resp.text, re.MULTILINE)
            extracted_title = title_match.group(1).strip() if title_match else None
            return resp.text, extracted_title
    except Exception:
        pass
    return None, None


def scan_markdown_reader_output(reader_text: str, collector: LeadCollector):
    """Mengekstrak tautan WA dan nomor HP dari hasil render Jina Cloud Reader."""
    decoded = html.unescape(unquote(reader_text))

    for match in WA_URL_REGEX.findall(decoded):
        collector.add(match, "Cloud Render Link WA", verified=True, confidence=100)

    clean_flat = " ".join(decoded.split())
    for m in re.finditer(ID_MOBILE_REGEX, clean_flat):
        start = max(0, m.start() - 75)
        end = min(len(clean_flat), m.end() + 75)
        surrounding = clean_flat[start:end].lower()

        has_wa_keyword = bool(re.search(r'\b(?:wa|w\.a|whatsapp|whats\s*app)\b', surrounding))
        if has_wa_keyword:
            collector.add(m.group(0), "Cloud Render Teks WA", verified=True, confidence=95)
        else:
            collector.add(m.group(0), "Cloud Render Nomor HP", verified=False, confidence=70)


def find_contact_subpages(raw_html: str, base_url: str) -> list[str]:
    """Mencari tautan internal halaman Kontak / Hubungi Kami / Tentang Kami."""
    soup = BeautifulSoup(raw_html, 'html.parser')
    base_netloc = urlparse(base_url).netloc.lower().replace('www.', '')
    scored_links = {}

    for a_tag in soup.find_all('a', href=True):
        href = str(a_tag.get('href', '')).strip()
        if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            continue

        full_url = urljoin(base_url, href).split('#')[0]
        parsed = urlparse(full_url)
        link_netloc = parsed.netloc.lower().replace('www.', '')

        if link_netloc != base_netloc or full_url.rstrip('/') == base_url.rstrip('/'):
            continue
        if any(full_url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.zip', '.mp4']):
            continue

        combined = f"{parsed.path} {a_tag.get_text(' ', strip=True)}".lower()
        score = 0
        for idx, kw in enumerate(CONTACT_PAGE_KEYWORDS):
            if kw in combined:
                score += (len(CONTACT_PAGE_KEYWORDS) - idx)

        if score > 0:
            scored_links[full_url] = max(scored_links.get(full_url, 0), score)

    return sorted(scored_links.keys(), key=lambda u: scored_links[u], reverse=True)[:3]


def extract_company_name(soup: BeautifulSoup, fallback_domain: str) -> str:
    """Mengambil Nama PT / Bisnis dari tag <h1> atau <title>."""
    for h1 in soup.find_all('h1'):
        text = " ".join(h1.get_text(strip=True).split())
        if 2 <= len(text) <= 95 and not is_bot_challenge(text):
            return text

    if soup.title and soup.title.string:
        title_clean = " ".join(soup.title.string.strip().split())
        if not is_bot_challenge(title_clean):
            for sep in [' | ', ' - ', ' – ', ' — ', ' : ']:
                if sep in title_clean:
                    title_clean = title_clean.split(sep)[0].strip()
            if title_clean:
                return title_clean[:95]

    return fallback_domain


def scrape_website(url: str) -> dict:
    """Pipeline lengkap ekstraksi kontak WA & audit website target (Vercel-Optimized)."""
    raw_url = url.strip()
    if not raw_url.startswith(('http://', 'https://')):
        raw_url = 'https://' + raw_url

    domain = urlparse(raw_url).netloc or raw_url
    session = requests.Session()
    collector = LeadCollector()

    html_content = ""
    final_url = raw_url
    iframe_blocked = False
    used_cloud_render = False
    cloud_title = None

    # Lapis 1: Permintaan HTTP Cepat
    try:
        resp = session.get(raw_url, headers=HEADERS, timeout=9, allow_redirects=True)
        final_url = resp.url
        html_content = resp.text

        xfo = resp.headers.get('X-Frame-Options', '').upper()
        csp = resp.headers.get('Content-Security-Policy', '').lower()
        iframe_blocked = ('DENY' in xfo or 'SAMEORIGIN' in xfo) or (
            'frame-ancestors' in csp and 'frame-ancestors *' not in csp
        )

        if not is_bot_challenge(html_content, resp.status_code):
            scan_html_for_contacts(html_content, final_url, collector, session)
    except Exception:
        pass

    # Lapis 2: Cloud Headless Reader Fallback (menembus anti-bot / Cloudflare / JS tanpa browser lokal)
    if is_bot_challenge(html_content) or not collector.has_verified():
        rendered_md, c_title = fetch_via_cloud_reader(final_url, session)
        if rendered_md:
            used_cloud_render = True
            cloud_title = c_title
            scan_markdown_reader_output(rendered_md, collector)

    # Lapis 3: Telusuri sub-halaman Kontak / Hubungi Kami jika WA terverifikasi masih kosong
    if html_content and not is_bot_challenge(html_content) and not collector.has_verified():
        subpages = find_contact_subpages(html_content, final_url)
        for sub_url in subpages:
            try:
                sub_resp = session.get(sub_url, headers=HEADERS, timeout=7, allow_redirects=True)
                if not is_bot_challenge(sub_resp.text, sub_resp.status_code):
                    scan_html_for_contacts(
                        sub_resp.text, sub_url, collector, session,
                        page_suffix=" (Sub-halaman)", follow_redirects=True
                    )
                    if collector.has_verified():
                        break
            except Exception:
                continue

    is_https = final_url.startswith('https://')
    wa_leads = collector.to_list()

    if (not html_content or is_bot_challenge(html_content)) and not used_cloud_render:
        return {
            "status": "blocked",
            "company_name": domain,
            "url": final_url,
            "domain": urlparse(final_url).netloc or domain,
            "is_https": is_https,
            "has_viewport": False,
            "iframe_allowed": False,
            "wa_leads": wa_leads,
            "notes": ["Situs memblokir akses / gagal dimuat"]
        }

    if html_content and not is_bot_challenge(html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        company_name = extract_company_name(soup, urlparse(final_url).netloc or domain)
        has_viewport = bool(soup.find('meta', attrs={'name': re.compile(r'^viewport$', re.I)}))
    else:
        company_name = (cloud_title.split('|')[0].split('-')[0].strip()[:95] if cloud_title else domain)
        has_viewport = True

    notes = []
    if used_cloud_render:
        notes.append("Cloud JS Render Aktif")
    if not is_https:
        notes.append("Belum HTTPS")
    if not has_viewport:
        notes.append("Belum Mobile-Friendly")
    if not wa_leads:
        notes.append("Nomor WA tidak ditemukan di halaman utama maupun kontak")

    return {
        "status": "success",
        "company_name": company_name or domain,
        "url": final_url,
        "domain": urlparse(final_url).netloc or domain,
        "is_https": is_https,
        "has_viewport": has_viewport,
        "iframe_allowed": not iframe_blocked,
        "wa_leads": wa_leads,
        "notes": notes
    }