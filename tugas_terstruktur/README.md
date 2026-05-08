# DOKUMENTASI PROGRAM - SISTEM DATA PRODUKSI - Tugas Terstruktur Pertemuan 6

Tugas ini dibangun untuk memenuhi kriteria Tugas Terstruktur (Tugas Mandiri) pembangunan aplikasi input data produksi dan laporan berbasis MongoDB.

# 1. Persiapan Lingkungan
- Pastikan MongoDB Community Server sudah terinstal dan berjalan (Running).
- Gunakan Python 3.x.
- Instalasi library yang dibutuhkan:
  pip install pymongo pandas python-dotenv tabulate

# 2. Konfigurasi Database (.env)
Aplikasi menggunakan environment variable untuk koneksi database. Pastikan file `.env` tersedia di root folder dengan isi:
MONGO_URI=mongodb://localhost:27017/

# 3. Cara Menjalankan Program
1. Buka Terminal/PowerShell di folder project.
2. Aktifkan Virtual Environment:
   .\venv\Scripts\activate
3. Jalankan aplikasi:
   python app_produksi.py

# 4. Fitur Aplikasi
- Menu 1: Input data produksi (tersimpan ke koleksi 'produksi').
- Menu 2: Tampilkan data per mesin dalam format tabel rapi.
- Menu 3: Agregasi reject rate untuk mencari batch dengan reject > 5%.
- Menu 4: Ekspor laporan total produksi & reject per mesin ke file CSV.
- Logging: Semua aktivitas operasional (insert, query, error) otomatis tercatat di file `app.log`.

# 5. Struktur Folder
- app_produksi.py  : Skrip utama aplikasi (Modular).
- .env             : Konfigurasi connection string.
- app.log          : File catatan aktivitas (Logging).
- README.md        : Panduan penggunaan program.
