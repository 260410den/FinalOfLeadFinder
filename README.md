# Lead Finder — Pencari Kontak WhatsApp & Pratinjau Website Otomatis

**Lead Finder** adalah aplikasi bantu riset bisnis untuk mengambil nama perusahaan dan nomor WhatsApp dari daftar link website secara otomatis, sekaligus menampilkan tampilan asli websitenya secara *real-time* dalam satu layar.

## 🔗 Akses Aplikasi

Anda dapat menggunakan aplikasi ini secara langsung melalui versi online, atau mengunduhnya untuk dijalankan secara mandiri di komputer Anda:

| Pilihan Akses | Keterangan | Link / Tempat Akses |
| :--- | :--- | :--- |
| **🌐 Versi Online (Langsung Pakai)** | Langsung buka dari browser HP maupun laptop tanpa perlu instalasi apa pun. | `[masih dalam proses deploy]` |
| **💻 Versi Mandiri (Download)** | Unduh folder proyek dari halaman GitHub ini (*Klik tombol hijau **Code** → **Download ZIP***) untuk dijalankan di komputer. | Repositori GitHub Ini |

## ⚖️ Perbandingan Versi Online vs. Versi Mandiri

Pilih cara penggunaan yang paling sesuai dengan kebutuhan riset Anda:

| Aspek | Versi Online (Via Link Vercel) | Versi Mandiri (Di Komputer) |
| :--- | :--- | :--- |
| **Kepraktisan** | **Sangat praktis**, tinggal klik link dan langsung pakai dari HP atau laptop. | Perlu mengunduh folder proyek dan menjalankannya di komputer. |
| **Kecepatan Pemindaian** | Cepat untuk mengecek **1–10 link** sekaligus. | **Jauh lebih cepat** karena berjalan langsung menggunakan internet komputer Anda. |
| **Kapasitas Sekali Proses** | Dibatasi waktu proses maksimal **60 detik** per pemindaian. | **Tanpa batas waktu**, aman untuk memindai puluhan link sekaligus. |
| **Stabilitas Akses Web** | Menggunakan server cloud (terkadang beberapa website membatasi akses server). | Menggunakan jaringan internet pribadi sehingga lebih jarang terblokir website target. |

> **Tips Penggunaan:** Gunakan **Versi Online** saat sedang bepergian atau butuh mengecek beberapa website dengan cepat. Gunakan **Versi Mandiri (Komputer)** saat melakukan riset dalam jumlah banyak agar kecepatannya maksimal.

## ✨ Fitur & Manfaat Utama

### 1. Pencarian Kontak WhatsApp Secara Menyeluruh
* **Menemukan Nomor Tersembunyi:** Otomatis menarik nomor WhatsApp yang ada di halaman utama, halaman *Kontak / Hubungi Kami*, tombol chat mengambang, tautan singkat (*shortlink*), hingga nomor yang terpasang di balik gambar atau banner.
* **Penyaringan Nomor Valid:** Otomatis memisahkan nomor seluler dari nomor telepon kantor (`021`, `031`) atau angka acak, serta memberikan tanda **`✓ Terverifikasi WA`** untuk nomor yang dipastikan terhubung ke WhatsApp.

### 2. Tampilan Layar Terbagi (*Split-Screen Real-Time*)
* **Panel Kiri (Daftar Kontak):** Menampilkan nama perusahaan, status keamanan/tampilan website, dan daftar nomor WhatsApp yang ditemukan.
* **Panel Kanan (Pratinjau Website Langsung):** Membuka tampilan asli website target secara langsung di sebelah kanan. Anda bisa mengganti mode tampilan **Desktop** maupun **Mobile** untuk melihat kerapian website tersebut.

### 3. Mempercepat Komunikasi & Rekap Data
* **Langsung Chat WhatsApp:** Klik nomor yang muncul untuk langsung membuka ruang chat WhatsApp tanpa perlu menyimpan nomor ke kontak HP terlebih dahulu.
* **Salin Nomor & Contoh Pesan:** Tersedia tombol **Salin** untuk menyalin nomor dan tombol **Pitch** untuk menyalin draf pesan perkenalan sesuai nama perusahaan target.
* **Unduh ke Excel / CSV:** Simpan seluruh hasil pencarian beserta catatan pengecekan website ke dalam satu file `.csv` yang rapi.

## 📖 Cara Menggunakan Aplikasi

1. Buka halaman utama aplikasi, lalu klik **Buka Dashboard Manual** (atau masuk ke halaman `/app`).
2. Tempel (*paste*) satu atau beberapa alamat website perusahaan ke kotak input *(pisahkan dengan baris baru jika ingin memindai banyak link sekaligus)*.
3. Klik tombol **Pindai URL** dan tunggu beberapa saat hingga daftar hasilnya muncul di panel kiri.
4. Klik kartu perusahaan mana saja di **panel kiri** untuk melihat tampilan websitenya secara langsung di **panel kanan**.
5. Klik nomor WhatsApp untuk mulai menghubungi prospek, atau gunakan tombol **Salin** dan **Pitch**.
6. Klik **Export CSV ↓** jika Anda ingin mengunduh seluruh hasil pemindaian ke komputer.

## 💻 Cara Menjalankan Versi Mandiri di Komputer

Bagi Anda yang mengunduh proyek ini untuk dijalankan sendiri di komputer:

1. Pastikan aplikasi **Python** sudah terpasang di komputer Anda.
2. Ekstrak file ZIP proyek yang sudah diunduh dari GitHub.
3. Buka terminal / Command Prompt di dalam folder proyek tersebut, lalu pasang paket pendukungnya (cukup dilakukan sekali saja):

```bash
pip install -r requirements.txt
```

4. **Jalankan aplikasi:**
   * **Pengguna Windows:** Klik dua kali file **`JALANKAN.bat`**, atau ketik `python app.py` di terminal.
   * **Pengguna macOS / Linux:** Ketik `python3 app.py` di terminal.
5. Buka browser Anda dan akses alamat **`http://127.0.0.1:5001`**.
