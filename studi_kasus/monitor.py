"""
monitor.py - Dashboard Monitoring Suhu Mesin
Studi Kasus Praktikum 6
"""

import os
import logging
from datetime import datetime, timedelta
 
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
 
load_dotenv()
 
# ── Konfigurasi logging ke file alarm.log ──────────────────────────────────
logging.basicConfig(
    filename='alarm.log',
    level=logging.WARNING,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
 
SUHU_ALARM = 90  # derajat Celsius
 
 
def koneksi_db():
    """Buat koneksi ke MongoDB. Return (client, collection) atau raise error."""
    client = MongoClient(os.getenv('MONGO_URI'), serverSelectionTimeoutMS=3000)
    client.admin.command('ping')          # test koneksi
    db = client['studi_kasus']
    return client, db['suhu_mesin']
 
 
def ambil_data_1jam(collection):
    """Ambil semua dokumen dalam 1 jam terakhir."""
    batas_waktu = datetime.utcnow() - timedelta(hours=1)
    return list(collection.find({'timestamp': {'$gt': batas_waktu}}))
 
 
def rata_rata_per_mesin(collection):
    """Hitung rata-rata suhu per mesin (1 jam terakhir) menggunakan aggregation."""
    batas_waktu = datetime.utcnow() - timedelta(hours=1)
    pipeline = [
        {'$match': {'timestamp': {'$gt': batas_waktu}}},
        {'$group': {
            '_id': '$mesin',
            'rata_rata_suhu': {'$avg': '$suhu'},
            'jumlah_data': {'$sum': 1}
        }},
        {'$sort': {'_id': 1}}
    ]
    return list(collection.aggregate(pipeline))
 
 
def suhu_terkini_per_mesin(collection):
    """Ambil dokumen suhu terbaru untuk setiap mesin."""
    batas_waktu = datetime.utcnow() - timedelta(hours=1)
    pipeline = [
        {'$match': {'timestamp': {'$gt': batas_waktu}}},
        {'$sort': {'timestamp': -1}},
        {'$group': {
            '_id': '$mesin',
            'suhu_terkini': {'$first': '$suhu'},
            'timestamp': {'$first': '$timestamp'}
        }},
        {'$sort': {'_id': 1}}
    ]
    return list(collection.aggregate(pipeline))
 
 
def deteksi_alarm(collection):
    """Deteksi mesin dengan suhu > 90 derajat dalam 1 jam terakhir."""
    batas_waktu = datetime.utcnow() - timedelta(hours=1)
    pipeline = [
        {'$match': {
            'timestamp': {'$gt': batas_waktu},
            'suhu': {'$gt': SUHU_ALARM}
        }},
        {'$group': {
            '_id': '$mesin',
            'suhu_max': {'$max': '$suhu'},
            'waktu_kejadian': {'$first': '$timestamp'}
        }},
        {'$sort': {'suhu_max': -1}}
    ]
    return list(collection.aggregate(pipeline))
 
 
def tampilkan_tabel(judul, df, lebar=60):
    """Tampilkan DataFrame sebagai tabel konsol sederhana."""
    print()
    print('=' * lebar)
    print(f'  {judul}')
    print('=' * lebar)
    if df.empty:
        print('  (Tidak ada data)')
    else:
        print(df.to_string(index=False))
    print('=' * lebar)
 
 
def catat_alarm(mesin, suhu_max, waktu):
    """Catat alarm ke file alarm.log."""
    logging.warning(f'ALARM | Mesin: {mesin} | Suhu Max: {suhu_max:.1f}°C | Waktu: {waktu}')
 
 
def jalankan_dashboard():
    """Fungsi utama dashboard."""
    print('\n' + '█' * 60)
    print('  DASHBOARD MONITORING SUHU MESIN')
    print(f'  Waktu laporan: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('█' * 60)
 
    try:
        client, collection = koneksi_db()
    except (ConnectionFailure, ServerSelectionTimeoutError):
        print('\n[OFFLINE] Sistem tidak dapat terhubung ke database MongoDB.')
        print('          Periksa koneksi jaringan dan pastikan MongoDB berjalan.')
        return
    except Exception as e:
        print(f'\n[ERROR] Koneksi gagal: {e}')
        return
 
    # ── 1. Suhu terkini per mesin ──────────────────────────────────────────
    terkini = suhu_terkini_per_mesin(collection)
    if terkini:
        df_terkini = pd.DataFrame(terkini).rename(columns={
            '_id': 'Mesin', 'suhu_terkini': 'Suhu Terkini (°C)', 'timestamp': 'Timestamp'
        })
        df_terkini['Timestamp'] = pd.to_datetime(df_terkini['Timestamp']).dt.strftime('%H:%M:%S')
        tampilkan_tabel('SUHU TERKINI PER MESIN (1 JAM TERAKHIR)', df_terkini)
    else:
        print('\n[INFO] Tidak ada data suhu dalam 1 jam terakhir.')
 
    # ── 2. Mesin alarm (suhu > 90°C) ──────────────────────────────────────
    alarm_list = deteksi_alarm(collection)
    if alarm_list:
        df_alarm = pd.DataFrame(alarm_list).rename(columns={
            '_id': 'Mesin', 'suhu_max': 'Suhu Max (°C)', 'waktu_kejadian': 'Waktu'
        })
        df_alarm['Waktu'] = pd.to_datetime(df_alarm['Waktu']).dt.strftime('%H:%M:%S')
        tampilkan_tabel(f'⚠  ALARM: MESIN DENGAN SUHU > {SUHU_ALARM}°C', df_alarm)
 
        # Catat ke alarm.log
        for row in alarm_list:
            catat_alarm(row['_id'], row['suhu_max'], row['waktu_kejadian'])
        print(f'  ▶ {len(alarm_list)} alarm dicatat ke alarm.log')
    else:
        print('\n  ✔  Tidak ada mesin yang melewati batas suhu alarm.')
 
    # ── 3. Rata-rata suhu per mesin ────────────────────────────────────────
    rata = rata_rata_per_mesin(collection)
    if rata:
        df_rata = pd.DataFrame(rata).rename(columns={
            '_id': 'Mesin', 'rata_rata_suhu': 'Rata-rata Suhu (°C)', 'jumlah_data': 'Jumlah Data'
        })
        df_rata['Rata-rata Suhu (°C)'] = df_rata['Rata-rata Suhu (°C)'].round(2)
        tampilkan_tabel('RATA-RATA SUHU PER MESIN (1 JAM TERAKHIR)', df_rata)
 
    client.close()
    print('\n[INFO] Dashboard selesai diperbarui.\n')
 
 
if __name__ == '__main__':
    jalankan_dashboard()
