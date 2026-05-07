"""
status_udara.py - Status Terkini Setiap Sensor Cold Storage
Anggota 4: Status Terkini & Dokumentasi

Pendekatan 2: Query MongoDB untuk dokumen terbaru setiap sensor,
lalu tampilkan statusnya di konsol dalam tabel yang rapi.

Status:
  ✅ Normal  – kondisi optimal
  ⚠️ Waspada – perlu perhatian (pm25 50–150)
  🔴 Bahaya  – tindakan segera diperlukan (pm25 > 150)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import time
from datetime import datetime

from pymongo import MongoClient, errors, DESCENDING

# ─── Konfigurasi ────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME   = "kelompok6"
COL_DATA  = "kualitas_udara"
COL_ALERT = "alert"

SENSOR_IDS = [
    "TEMP-A1", "TEMP-B1",
    "HUM-A1",  "HUM-B1",
    "NH3-A1",  "NH3-B1",
    "DOOR-A1", "DOOR-B1",
    "PRESS-A1","PRESS-B1",
]

REFRESH_INTERVAL = 10  # detik sebelum refresh tampilan


def get_status_label(pm25) -> tuple:
    """
    Kembalikan (emoji, label) berdasarkan nilai pm25.
    pm25 digunakan sebagai proxy universal untuk anomali.
    """
    if pm25 is None:
        return ("❓", "Tidak Diketahui")
    elif pm25 <= 50:
        return ("✅", "Normal")
    elif pm25 <= 150:
        return ("⚠️ ", "Waspada")
    else:
        return ("🔴", "Bahaya!")


def get_sensor_value_str(doc: dict) -> str:
    """Format nilai utama sensor berdasarkan tipe."""
    tipe = doc.get("tipe_sensor", "")
    if tipe == "suhu":
        v = doc.get("suhu")
        return f"Suhu      : {v}°C" if v is not None else "-"
    elif tipe == "kelembapan":
        v = doc.get("kelembapan")
        return f"Kelembapan: {v}%" if v is not None else "-"
    elif tipe == "amonia":
        v = doc.get("amonia")
        return f"NH₃       : {v} ppm" if v is not None else "-"
    elif tipe == "pintu":
        v = doc.get("status_pintu")
        return f"Pintu     : {'TERBUKA 🚪' if v == 1 else 'Tertutup'}"
    elif tipe == "tekanan":
        v = doc.get("tekanan")
        return f"Tekanan   : {v} Pa" if v is not None else "-"
    return "-"


def fetch_latest_status(col) -> list:
    """
    Query dokumen terbaru untuk setiap sensor_id.

    Returns:
        list[dict]: satu dokumen per sensor
    """
    results = []
    for sid in SENSOR_IDS:
        doc = col.find_one(
            {"sensor_id": sid},
            sort=[("timestamp", DESCENDING)]
        )
        if doc:
            results.append(doc)
        else:
            results.append({
                "sensor_id":   sid,
                "lokasi":      "—",
                "tipe_sensor": "—",
                "pm25":        None,
                "timestamp":   "Belum ada data",
            })
    return results


def count_alerts(col_alert) -> int:
    """Hitung jumlah alert dalam koleksi."""
    return col_alert.count_documents({})


def display_status(docs: list, total_alerts: int):
    """Cetak tabel status sensor ke konsol."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\033[2J\033[H", end="")  # clear screen

    print("=" * 68)
    print(f"   COLD STORAGE MONITORING — STATUS TERKINI")
    print(f"   Diperbarui: {now}  |  Total Alert: {total_alerts}")
    print("=" * 68)
    print(f"{'No':>3} {'Sensor ID':12} {'Lokasi':14} {'Tipe':10} {'Status':20} {'Nilai'}")
    print("-" * 68)

    for i, doc in enumerate(docs, 1):
        pm25           = doc.get("pm25")
        emoji, label   = get_status_label(pm25)
        nilai          = get_sensor_value_str(doc)
        ts             = doc.get("timestamp", "")[:19] if doc.get("timestamp") else "—"

        print(
            f"{i:>3} "
            f"{doc.get('sensor_id','—'):12} "
            f"{doc.get('lokasi','—'):14} "
            f"{doc.get('tipe_sensor','—'):10} "
            f"{emoji} {label:15} "
            f"{nilai}"
        )

    print("-" * 68)

    # Ringkasan
    n_bahaya  = sum(1 for d in docs if (d.get("pm25") or 0) > 150)
    n_waspada = sum(1 for d in docs if 50 < (d.get("pm25") or 0) <= 150)
    n_normal  = sum(1 for d in docs if (d.get("pm25") or 0) <= 50 and d.get("pm25") is not None)
    print(f"\n  Ringkasan: 🔴 Bahaya={n_bahaya}  ⚠️  Waspada={n_waspada}  ✅ Normal={n_normal}")
    print(f"  Tekan Ctrl+C untuk keluar. Refresh setiap {REFRESH_INTERVAL} detik.\n")


def main():
    try:
        client    = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        db        = client[DB_NAME]
        col       = db[COL_DATA]
        col_alert = db[COL_ALERT]
        print(f"[✓] MongoDB terhubung: {DB_NAME}")
    except errors.ServerSelectionTimeoutError as e:
        print(f"[✗] MongoDB tidak terjangkau: {e}")
        return

    try:
        while True:
            docs         = fetch_latest_status(col)
            total_alerts = count_alerts(col_alert)
            display_status(docs, total_alerts)
            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        print("\n[i] Status monitor dihentikan.")
    finally:
        client.close()


if __name__ == "__main__":
    main()