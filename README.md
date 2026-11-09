# Batikku – Toko Handmade Batik (Prototipe)

Website katalog dengan checkout via WhatsApp (CTWA). Bisa dijalankan **tanpa backend** (statis)
atau **dengan backend Flask** (admin panel untuk upload, edit, hapus produk).

## Struktur folder

```
batikku/
├── index.html              ← halaman toko
├── assets/
│   ├── css/style.css       ← tampilan
│   └── js/app.js           ← logika (slider, keranjang, checkout WA)
├── data/
│   └── products.js         ← DATA TOKO: produk, banner, nomor WA
├── foto/                   ← foto produk & banner
└── backend/                ← OPSIONAL (admin panel Flask)
    ├── app.py
    ├── pesanan.db          ← dibuat otomatis (data pembeli, jangan dipublikasikan)
    ├── requirements.txt
    ├── .env.example
    ├── templates/          ← halaman admin
    └── static/             ← css & js admin
```

Frontend dan backend memakai **file yang sama** (`data/products.js` dan `foto/`),
jadi keduanya selalu sinkron.

## Cara 1 – Tanpa backend
Buka `index.html` dengan klik dua kali. Untuk server lokal sederhana:

```
python -m http.server 8000      # lalu buka http://localhost:8000
```

Edit manual: buka `data/products.js`. Isinya JSON, jadi tanda petik ganda `"` dan koma
harus tetap benar. Taruh foto di `foto/` lalu tulis `"foto": "foto/tote-1.jpg"`.

## Cara 2 – Dengan backend + admin panel

```
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # Mac/Linux: cp .env.example .env  → isi password & SECRET_KEY
python app.py
```

- Toko: http://localhost:5000
- Admin: http://localhost:5000/admin (username/password dari `.env`; bawaan `admin` / `admin123`)

Fitur admin: tambah, edit, hapus, sembunyikan produk; upload foto (otomatis diperkecil
ke WEBP); kelola banner beranda dan nomor WhatsApp. Backup otomatis (20 terakhir) ada di
`backend/backup/`.

## Daftar pesanan di admin panel

Menu **Pesanan** (admin) mencatat pesanan: ID, waktu, pembeli, alamat, metode bayar, item, total,
ongkir, status (Menunggu bayar → Sudah dibayar → Diproses → Dikirim → Selesai / Batal), no. resi,
dan catatan. Ada pencarian, filter status, ekspor CSV, dan **Pesanan Manual** untuk mencatat
pesanan yang masuk lewat chat.

Pesanan tercatat otomatis saat pembeli menekan "Pesan via WhatsApp", **hanya jika toko
dibuka lewat Flask** (`python app.py`). Pada toko statis tanpa backend online, pesanan tidak
tercatat, jadi gunakan **Pesanan Manual**. Harga selalu dihitung ulang server dari katalog.
Data disimpan di `backend/pesanan.db` (SQLite). File ini berisi data pembeli, jadi jangan
diunggah ke hosting publik.

## Kalau mau dipublikasikan

**A. Statis (paling murah, disarankan untuk tes trafik).** Kelola produk lewat admin di
komputermu, lalu upload semua **kecuali folder `backend/`** (yaitu `index.html`, `assets/`,
`data/`, `foto/`) ke Netlify, Cloudflare Pages, atau GitHub Pages. Setiap ada perubahan, upload ulang.
Admin panel tidak ikut online, jadi aman.

**B. Dengan backend online.** Perlu hosting Python (misalnya PythonAnywhere, VPS, atau Railway).
Wajib: ganti `ADMIN_PASSWORD`, isi `SECRET_KEY`, pakai HTTPS, dan jalankan dengan
`gunicorn app:app`. Cek harga dan ketentuan hosting terbaru sebelum memilih.

## Format data produk (`data/products.js`)

| Field | Keterangan |
|---|---|
| `id` | unik, huruf kecil/angka/tanda `-` |
| `nama`, `kategori`, `deskripsi` | teks (kategori baru otomatis jadi tab di halaman Shop) |
| `harga` | angka tanpa titik, contoh `89000` |
| `foto` | `"foto/nama-file.webp"` atau `""` (pakai pola batik) |
| `tag` | `"best"`, `"hot"`, `"trendy"`, atau `""` |
| `ikon` | `bag`, `wallet`, `pouch`, `key` (dipakai jika belum ada foto) |
| `terjual` | angka |
| `aktif` | `true` tampil, `false` disembunyikan |
| `spesifikasi` | daftar teks `"Nama: Isi"` |

## Catatan keamanan admin
Login satu akun, proteksi CSRF, batas percobaan login, validasi dan konversi gambar.
Ini cukup untuk toko kecil, tapi tetap pakai password kuat dan HTTPS jika diakses publik.
