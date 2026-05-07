import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Koneksi ke MongoDB
client = MongoClient(os.getenv("MONGO_URI"))

# Nama database yang sekarang dan yang baru
db_lama = "tugas6_NIM_KAMU" # Ganti dengan nama yang sekarang
db_baru = "tugas6_225443021" # Ganti dengan nama yang benar

def ganti_nama_db():
    try:
        # 1. Ambil semua nama koleksi dari db lama
        koleksi_lama = client[db_lama].list_collection_names()
        
        if not koleksi_lama:
            print(f"Database '{db_lama}' tidak ditemukan atau kosong.")
            return

        print(f"Memulai migrasi dari {db_lama} ke {db_baru}...")

        # 2. Salin setiap koleksi ke database baru
        for nama_col in koleksi_lama:
            # Gunakan agregasi $out untuk menyalin koleksi
            client[db_lama][nama_col].aggregate([{"$out": {"db": db_baru, "coll": nama_col}}])
            print(f"Koleksi '{nama_col}' berhasil disalin.")

        # 3. Hapus database lama setelah yakin tersalin (opsional tapi disarankan)
        # client.drop_database(db_lama)
        # print(f"Database lama '{db_lama}' telah dihapus.")
        
        print(f"\nSukses! Sekarang database kamu bernama: {db_baru}")
        print("Jangan lupa ganti nama database di file app_produksi.py kamu ya!")

    except Exception as e:
        print(f"Terjadi kesalahan: {e}")

if __name__ == "__main__":
    ganti_nama_db()