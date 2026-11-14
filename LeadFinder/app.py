import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from flask import Flask, render_template, request, jsonify, Response
from scraper import scrape_website, HEADERS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))


@app.route('/')
def index():
    """Halaman Landing Page."""
    return render_template('index.html')


@app.route('/app')
def dashboard():
    """Halaman Dashboard Split-Screen Mode Manual."""
    return render_template('app.html')


@app.route('/scrape', methods=['POST'])
def scrape():
    """Menerima URL manual (1 link atau banyak baris) dan memanggil scrape_website."""
    data = request.get_json(silent=True) or {}
    raw_input = data.get('url', '') or request.form.get('url', '')

    urls = [
        line.strip()
        for line in raw_input.replace(',', '\n').splitlines()
        if line.strip()
    ]

    if not urls:
        return jsonify({"error": "Masukkan minimal satu URL website target."}), 400

    unique_urls = list(dict.fromkeys(urls))[:20]

    results = [None] * len(unique_urls)
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {
            executor.submit(scrape_website, target_url): idx
            for idx, target_url in enumerate(unique_urls)
        }
        for future in as_completed(future_map):
            idx = future_map[future]
            results[idx] = future.result()

    return jsonify({"results": results})


@app.route('/proxy')
def proxy_preview():
    """Menampilkan website target di panel browser kanan meski situs memasang X-Frame-Options."""
    target_url = request.args.get('url', '').strip()
    if not target_url:
        return "URL kosong", 400
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url

    try:
        resp = requests.get(target_url, headers=HEADERS, timeout=12, allow_redirects=True)
        content_type = resp.headers.get('Content-Type', 'text/html; charset=utf-8')

        if 'text/html' in content_type.lower():
            html_body = resp.text
            base_tag = f'<base href="{resp.url}" target="_blank">'
            if '<head>' in html_body.lower():
                idx = html_body.lower().find('<head>') + 6
                html_body = html_body[:idx] + base_tag + html_body[idx:]
            else:
                html_body = base_tag + html_body
            return Response(html_body, status=resp.status_code, content_type='text/html; charset=utf-8')

        return Response(resp.content, status=resp.status_code, content_type=content_type)
    except Exception as exc:
        return f"""
        <div style="font-family:sans-serif; padding:40px; text-align:center; color:#334155;">
            <h3>Pratinjau dibatasi oleh server website target</h3>
            <p style="font-size:13px; color:#64748b;">{type(exc).__name__} — {target_url}</p>
            <a href="{target_url}" target="_blank" style="display:inline-block; margin-top:10px; padding:10px 18px; background:#2563eb; color:#fff; border-radius:8px; text-decoration:none; font-size:13px; font-weight:600;">
                Buka Langsung di Tab Baru ↗
            </a>
        </div>
        """, 200


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)