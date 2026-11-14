document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('scrapeForm');
    if (!form) return;

    const phoneList = document.getElementById('phoneList');
    const resultCount = document.getElementById('resultCount');
    const phoneSubtext = document.getElementById('phoneSubtext');
    const iframePreview = document.getElementById('websitePreview');
    const mockupUrl = document.getElementById('mockupUrl');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        let url = document.getElementById('urlInput').value.trim();
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'https://' + url;
        }

        resultCount.textContent = "Memindai...";
        phoneSubtext.textContent = "Sedang mengambil data...";
        phoneList.innerHTML = '';

        try {
            const response = await fetch('/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();
            const phones = data.phones || data;

            if (phones && phones.length > 0) {
                resultCount.textContent = `${phones.length} hasil`;
                phoneSubtext.textContent = `Nomor terdeteksi dari ${url}`;
                phones.forEach(phone => {
                    const li = document.createElement('li');
                    li.innerHTML = `<i class="fa-brands fa-whatsapp" style="color:#25d366; margin-right:8px;"></i> ${phone}`;
                    phoneList.appendChild(li);
                });
            } else {
                resultCount.textContent = "0 hasil";
                phoneSubtext.textContent = "Tidak ada nomor ditemukan.";
                phoneList.innerHTML = `<li><span style="color:#94a3b8;">Tidak ada data</span></li>`;
            }

            iframePreview.src = url;
            mockupUrl.textContent = url;

        } catch (err) {
            console.error(err);
            resultCount.textContent = "Error";
            phoneSubtext.textContent = "Gagal memuat URL.";
        }
    });
});