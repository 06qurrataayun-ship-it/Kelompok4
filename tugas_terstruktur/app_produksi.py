import os
import logging
import pandas as pd
from tabulate import tabulate
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# LOAD KONFIGURASI DARI .env
load_dotenv()

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# KONEKSI KE MONGODB 
try:
    # Mengambil connection string dari environment variable
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["tugas6_225443021"] 
    col = db["produksi"]
    logging.info("Aplikasi dimulai - Koneksi sukses.")
except Exception as e:
    logging.error(f"Gagal koneksi database: {e}")
    print("Database tidak terdeteksi, pastikan MongoDB sudah jalan!")

# bagian menu

def input_data():
    """Menu 1: Input data produksi baru"""
    try:
        print("\n--- Input Data Produksi ---")
        batch = input("Batch: ")
        mesin = input("Nama Mesin: ")
        jumlah = int(input("Jumlah Produksi: "))
        reject = int(input("Jumlah Reject: "))
        tgl_input = input("Tanggal (YYYY-MM-DD): ")
        tanggal = datetime.strptime(tgl_input, "%Y-%m-%d")

        payload = {
            "batch": batch,
            "mesin": mesin,
            "jumlah": jumlah,
            "reject": reject,
            "tanggal": tanggal
        }
        col.insert_one(payload)
        print(">> Data berhasil disimpan!")
        logging.info(f"INSERT: Batch {batch} ditambahkan.")
    except Exception as e:
        print(f">> Gagal input: {e}")
        logging.error(f"ERR_INPUT: {e}")

def tampil_mesin():
    """Menu 2: Tampilkan data per mesin dalam tabel"""
    nama_mesin = input("\nMasukkan nama mesin: ")
    query = {"mesin": nama_mesin}
    data = list(col.find(query))
    
    if data:
        table_data = []
        for d in data:
                table_data.append([
                    d.get('batch'), 
                    d.get('mesin'), 
                    d.get('jumlah'), 
                    d.get('reject'), 
                    d.get('tanggal').strftime('%Y-%m-%d') 
                ])
        
        headers = ["BATCH", "MESIN", "JUMLAH", "REJECT", "TANGGAL"]
        
        # Tampilkan pakai tabulate
        print("\n" + tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
        logging.info(f"QUERY: Menampilkan tabel mesin {nama_mesin}")
    else:
        print("Data tidak ditemukan.")

def hitung_reject():
    """Menu 3: Agregasi reject rate > 5%"""
    pipeline = [
        {
            "$project": {
                "batch": 1,
                "reject_rate": {
                    "$multiply": [{"$divide": ["$reject", "$jumlah"]}, 100]
                }
            }
        },
        {"$match": {"reject_rate": {"$gt": 5}}}
    ]
    hasil = list(col.aggregate(pipeline))
    
    print("\n--- Batch dengan Reject Rate > 5% ---")
    if hasil:
        for item in hasil:
            print(f"Batch: {item['batch']} | Rate: {item['reject_rate']:.2f}%")
        logging.info("AGGREGATE: Hitung reject rate sukses.")
    else:
        print("Aman! Tidak ada reject rate di atas 5%.")

def ekspor_csv():
    """Menu 4: Ekspor laporan bulanan"""
    print("\nFormat MM-YYYY (Contoh: 05-2026)")
    periode = input("Masukkan Bulan & Tahun: ")
    try:
        bln, thn = map(int, periode.split('-'))
        
        pipeline = [
            {
                "$match": {
                    "tanggal": {
                        "$gte": datetime(thn, bln, 1),
                        "$lt": datetime(thn, bln + 1, 1) if bln < 12 else datetime
                        (thn + 1, 1, 1)
                    }
                }
            },
            {
                "$group": {
                    "_id": "$mesin",
                    "total_jumlah": {"$sum": "$jumlah"},
                    "total_reject": {"$sum": "$reject"}
                }
            }
        ]
        
        hasil = list(col.aggregate(pipeline))
        if hasil:
            df = pd.DataFrame(hasil).rename(columns={"_id": "mesin"})
            nama_file = f"laporan_{periode}.csv"
            df.to_csv(nama_file, index=False)
            print(f">> Berhasil diekspor ke {nama_file}")
            logging.info(f"EXPORT: Laporan {nama_file} dibuat.")
        else:
            print("Tidak ada data untuk periode tersebut.")
    except Exception as e:
        print("Kesalahan format.")
        logging.error(f"ERR_EXPORT: {e}")

# --- MENU UTAMA ---
def main():
    while True:
        print("\n=== APLIKASI DATA PRODUKSI ===")
        print("1. Input Data Baru")
        print("2. Tampilkan per Mesin")
        print("3. Cek Reject Rate (>5%)")
        print("4. Ekspor ke CSV")
        print("5. Keluar")
        
        pilih = input("Pilih (1-5): ")
        
        if pilih == '1': input_data()
        elif pilih == '2': tampil_mesin()
        elif pilih == '3': hitung_reject()
        elif pilih == '4': ekspor_csv()
        elif pilih == '5': 
            print("Terimakasih!")
            break
        else:
            print("Pilihan salah!")

if __name__ == "__main__":
    main()