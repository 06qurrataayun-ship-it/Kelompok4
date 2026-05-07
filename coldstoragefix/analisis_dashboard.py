"""
analisis_dashboard.py - Analisis Data & Visualisasi Dashboard
Anggota 3: Analisis dan Dashboard

Mengambil data 24 jam terakhir dari MongoDB, membuat grafik perbandingan
antar lokasi, dan mengekspor ke CSV.

Output:
  - dashboard_udara.png  : grafik tren sensor per lokasi
  - data_24jam.csv       : data mentah 24 jam terakhir
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import csv
from datetime import datetime, timezone, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pymongo import MongoClient, errors

# ─── Konfigurasi ────────────────────────────────────────────────────────────
MONGO_URI  = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME    = "kelompok6"
COL_DATA   = "kualitas_udara"

OUTPUT_PNG = "dashboard_udara.png"
OUTPUT_CSV = "data_24jam.csv"


def get_mongo_collection():
    """Koneksi ke MongoDB dan kembalikan koleksi."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()
    return client[DB_NAME][COL_DATA], client


def fetch_last_24h(col) -> list:
    """
    Mengambil semua dokumen dalam 24 jam terakhir.

    Returns:
        list[dict]: daftar dokumen sensor
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cursor = col.find(
        {"timestamp": {"$gte": cutoff}},
        {"_id": 0}
    ).sort("timestamp", 1)
    return list(cursor)


def aggregate_hourly(col, tipe_sensor: str, field: str) -> dict:
    """
    Agregasi rata-rata nilai per jam per lokasi untuk tipe sensor tertentu.

    Args:
        col         : koleksi MongoDB
        tipe_sensor : tipe sensor (misal 'suhu', 'kelembapan')
        field       : nama field yang dirata-rata (misal 'suhu', 'kelembapan')

    Returns:
        dict: {lokasi: [(jam, rata_rata), ...]}
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    pipeline = [
        {"$match": {
            "timestamp":   {"$gte": cutoff},
            "tipe_sensor": tipe_sensor,
            field:         {"$ne": None}
        }},
        {"$addFields": {
            "ts_date": {"$dateFromString": {"dateString": "$timestamp"}}
        }},
        {"$group": {
            "_id": {
                "lokasi": "$lokasi",
                "hour":   {"$hour": "$ts_date"}
            },
            "avg_value": {"$avg": f"${field}"}
        }},
        {"$sort": {"_id.hour": 1}}
    ]
    results = list(col.aggregate(pipeline))

    lokasi_data: dict = {}
    for doc in results:
        lokasi = doc["_id"]["hour"]  # nanti kita pakai hour sebagai x
        loc    = doc["_id"]["lokasi"]
        if loc not in lokasi_data:
            lokasi_data[loc] = []
        lokasi_data[loc].append((doc["_id"]["hour"], round(doc["avg_value"], 2)))

    return lokasi_data


def export_csv(data: list, filepath: str):
    """Ekspor data ke file CSV."""
    if not data:
        print("[!] Tidak ada data untuk diekspor.")
        return

    fieldnames = [
        "sensor_id", "lokasi", "tipe_sensor", "timestamp",
        "suhu", "kelembapan", "amonia", "status_pintu", "tekanan", "pm25"
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

    print(f"[✓] Data diekspor ke '{filepath}' ({len(data)} baris)")


def plot_dashboard(col):
    """
    Membuat grafik dashboard multi-panel untuk setiap tipe sensor.
    Grafik disimpan sebagai dashboard_udara.png.
    """
    configs = [
        {"tipe": "suhu",      "field": "suhu",       "ylabel": "Suhu (°C)",    "color": ["#1f77b4", "#ff7f0e"]},
        {"tipe": "kelembapan","field": "kelembapan",  "ylabel": "Kelembapan (%)", "color": ["#2ca02c", "#d62728"]},
        {"tipe": "amonia",    "field": "amonia",      "ylabel": "NH₃ (ppm)",    "color": ["#9467bd", "#8c564b"]},
        {"tipe": "tekanan",   "field": "tekanan",     "ylabel": "Tekanan (Pa)", "color": ["#e377c2", "#7f7f7f"]},
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f"Dashboard Monitoring Cold Storage – 24 Jam Terakhir\n"
        f"({datetime.now().strftime('%Y-%m-%d %H:%M')})",
        fontsize=14, fontweight="bold", y=1.01
    )
    axes_flat = axes.flatten()

    for i, cfg in enumerate(configs):
        ax  = axes_flat[i]
        data = aggregate_hourly(col, cfg["tipe"], cfg["field"])

        if not data:
            ax.text(0.5, 0.5, "Belum ada data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=11, color="gray")
            ax.set_title(f"Sensor {cfg['tipe'].title()}")
            continue

        for j, (lokasi, points) in enumerate(sorted(data.items())):
            hours  = [p[0] for p in points]
            values = [p[1] for p in points]
            color  = cfg["color"][j % len(cfg["color"])]
            ax.plot(hours, values, marker="o", label=lokasi, color=color, linewidth=2)

        ax.set_title(f"Sensor {cfg['tipe'].title()}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Jam (UTC)")
        ax.set_ylabel(cfg["ylabel"])
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(0, 24, 2))

    # Panel ke-5: status pintu (bar chart)
    door_data = aggregate_hourly(col, "pintu", "pm25")
    ax5 = axes_flat[3] if len(configs) < 4 else None
    # (sudah 4 panel, cukup)

    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[✓] Grafik disimpan ke '{OUTPUT_PNG}'")


def main():
    print(f"\n{'='*60}")
    print("   COLD STORAGE – ANALISIS & DASHBOARD")
    print(f"{'='*60}\n")

    try:
        col, client = get_mongo_collection()
    except errors.ServerSelectionTimeoutError as e:
        print(f"[✗] MongoDB tidak dapat dijangkau: {e}")
        return

    # 1. Ambil data 24 jam terakhir
    print("[1] Mengambil data 24 jam terakhir...")
    data = fetch_last_24h(col)
    print(f"    → {len(data)} dokumen ditemukan")

    # 2. Ekspor ke CSV
    print("[2] Mengekspor ke CSV...")
    export_csv(data, OUTPUT_CSV)

    # 3. Plot dashboard
    print("[3] Membuat grafik dashboard...")
    plot_dashboard(col)

    print(f"\n[✓] Selesai! Output: {OUTPUT_PNG}, {OUTPUT_CSV}")
    client.close()


if __name__ == "__main__":
    main()