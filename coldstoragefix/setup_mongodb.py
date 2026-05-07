"""
setup_mongodb.py - Inisialisasi Database & Isi Sample Data
Menghubungkan ke MongoDB, membuat database + koleksi,
membuat index, dan mengisi data contoh realistis.

Jalankan SEKALI sebelum menjalankan sistem:
    python setup_mongodb.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import random
from datetime import datetime, timezone, timedelta

from pymongo import MongoClient, ASCENDING, DESCENDING, errors

# ─── Konfigurasi ────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME   = "kelompok6"

SENSORS = [
    {"sensor_id": "TEMP-A1",  "lokasi": "Cold Room A", "tipe": "suhu"},
    {"sensor_id": "TEMP-B1",  "lokasi": "Cold Room B", "tipe": "suhu"},
    {"sensor_id": "HUM-A1",   "lokasi": "Cold Room A", "tipe": "kelembapan"},
    {"sensor_id": "HUM-B1",   "lokasi": "Cold Room B", "tipe": "kelembapan"},
    {"sensor_id": "NH3-A1",   "lokasi": "Cold Room A", "tipe": "amonia"},
    {"sensor_id": "NH3-B1",   "lokasi": "Cold Room B", "tipe": "amonia"},
    {"sensor_id": "DOOR-A1",  "lokasi": "Cold Room A", "tipe": "pintu"},
    {"sensor_id": "DOOR-B1",  "lokasi": "Cold Room B", "tipe": "pintu"},
    {"sensor_id": "PRESS-A1", "lokasi": "Cold Room A", "tipe": "tekanan"},
    {"sensor_id": "PRESS-B1", "lokasi": "Cold Room B", "tipe": "tekanan"},
]


def generate_sample(sensor: dict, ts: datetime, anomaly: bool = False) -> dict:
    """Hasilkan satu dokumen sensor realistis."""
    tipe = sensor["tipe"]
    base = {
        "sensor_id":   sensor["sensor_id"],
        "lokasi":      sensor["lokasi"],
        "tipe_sensor": tipe,
        "timestamp":   ts.isoformat(),
        "suhu":        None,
        "kelembapan":  None,
        "amonia":      None,
        "status_pintu": None,
        "tekanan":     None,
        "pm25":        None,
    }

    if tipe == "suhu":
        base["suhu"] = round(random.uniform(-8.0, -5.0) if anomaly else random.uniform(-22.0, -18.0), 2)
        base["pm25"] = round(random.uniform(160, 200) if anomaly else random.uniform(5, 40), 2)

    elif tipe == "kelembapan":
        base["kelembapan"] = round(random.uniform(55, 65) if anomaly else random.uniform(85, 95), 2)
        base["pm25"]       = round(random.uniform(160, 200) if anomaly else random.uniform(5, 40), 2)

    elif tipe == "amonia":
        nh3 = round(random.uniform(30, 50) if anomaly else random.uniform(0.5, 9.5), 2)
        base["amonia"] = nh3
        base["pm25"]   = round(nh3 * 6 if anomaly else nh3 * 1.5, 2)

    elif tipe == "pintu":
        base["status_pintu"] = 1 if anomaly else 0
        base["pm25"] = round(random.uniform(165, 200) if anomaly else random.uniform(5, 20), 2)

    elif tipe == "tekanan":
        base["tekanan"] = round(random.uniform(5, 18) if anomaly else random.uniform(50, 80), 2)
        base["pm25"]    = round(random.uniform(158, 195) if anomaly else random.uniform(10, 30), 2)

    return base


def seed_data(col_data, col_alert):
    """Masukkan data historis 24 jam ke MongoDB."""
    now    = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    docs        = []
    alert_docs  = []
    ts          = cutoff

    print("[2] Mengisi data historis (setiap 10 menit selama 24 jam)...")
    while ts <= now:
        for sensor in SENSORS:
            anomaly = random.random() < 0.05
            doc     = generate_sample(sensor, ts, anomaly)
            docs.append(doc)

            # Buat alert jika anomali
            if anomaly and (doc.get("pm25") or 0) > 150:
                tipe = sensor["tipe"]
                if tipe == "amonia":
                    pesan = f"Amonia berbahaya! NH₃={doc['amonia']} ppm"
                elif tipe == "pintu":
                    pesan = "Pintu TERBUKA terlalu lama!"
                elif tipe == "tekanan":
                    pesan = f"Tekanan rendah: {doc['tekanan']} Pa (penumpukan es)"
                else:
                    pesan = f"PM2.5 berbahaya! Nilai={doc['pm25']}"

                alert_docs.append({
                    "sensor_id":   sensor["sensor_id"],
                    "lokasi":      sensor["lokasi"],
                    "tipe_sensor": tipe,
                    "pm25":        doc["pm25"],
                    "timestamp":   ts.isoformat(),
                    "pesan":       pesan,
                    "created_at":  ts.isoformat(),
                })

        ts += timedelta(minutes=10)

    col_data.insert_many(docs)
    print(f"    → {len(docs)} dokumen ke 'kualitas_udara'")

    if alert_docs:
        col_alert.insert_many(alert_docs)
        print(f"    → {len(alert_docs)} alert ke 'alert'")
    else:
        print("    → 0 alert (tidak ada anomali)")


def main():
    print(f"\n{'='*60}")
    print("   SETUP DATABASE MONGODB – Cold Storage IoT")
    print(f"{'='*60}\n")

    # 1. Koneksi
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        print(f"[OK] Terhubung ke MongoDB: {MONGO_URI}")
    except errors.ServerSelectionTimeoutError as e:
        print(f"[No] Gagal konek MongoDB: {e}")
        return

    db        = client[DB_NAME]
    col_data  = db["kualitas_udara"]
    col_alert = db["alert"]

    print(f"[1] Database: {DB_NAME}")

    # 2. Drop & recreate collections (fresh start)
    col_data.drop()
    col_alert.drop()
    print("    → Koleksi lama dihapus (reset)")

    # 3. Buat index
    col_data.create_index([("sensor_id", ASCENDING), ("timestamp", DESCENDING)])
    col_data.create_index([("timestamp", DESCENDING)])
    col_data.create_index([("tipe_sensor", ASCENDING)])
    col_alert.create_index([("sensor_id", ASCENDING), ("timestamp", DESCENDING)])
    print("    → Index dibuat")

    # 4. Seed data
    seed_data(col_data, col_alert)

    # 5. Verifikasi
    print(f"\n[3] Verifikasi:")
    print(f"    kualitas_udara : {col_data.count_documents({}):,} dokumen")
    print(f"    alert          : {col_alert.count_documents({}):,} dokumen")
    print(f"\n[✓] Setup selesai! Database '{DB_NAME}' siap digunakan.")

    # Tampilkan contoh dokumen
    print("\n[4] Contoh dokumen 'kualitas_udara':")
    sample = col_data.find_one({}, {"_id": 0})
    if sample:
        for k, v in sample.items():
            if v is not None:
                print(f"    {k:15}: {v}")

    print("\n[5] Contoh dokumen 'alert':")
    sample_alert = col_alert.find_one({}, {"_id": 0})
    if sample_alert:
        for k, v in sample_alert.items():
            if v is not None:
                print(f"    {k:15}: {v}")

    client.close()


if __name__ == "__main__":
    main()