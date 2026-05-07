"""
pub_udara.py - MQTT Publisher Simulasi Sensor Cold Storage
Anggota 1: MQTT Publisher

Mensimulasikan 5 jenis sensor untuk sistem monitoring Cold Storage (ruang penyimpanan daging).
Setiap 10 detik, data dikirim ke topik MQTT 'pabrik/udara'.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

# ─── Konfigurasi MQTT ───────────────────────────────────────────────────────
BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
TOPIC       = "pabrik/udara"
INTERVAL    = 10  # detik antar pengiriman

# ─── Definisi Sensor (5 jenis x 2 lokasi = 10 sensor) ──────────────────────
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


def generate_sensor_data(sensor: dict) -> dict:
    """
    Membuat data sensor simulasi berdasarkan tipe sensor.
    Probabilitas 5% untuk kondisi anomali/berbahaya.
    """
    tipe = sensor["tipe"]
    is_anomaly = random.random() < 0.05  # 5% peluang anomali

    if tipe == "suhu":
        # Normal: -18°C s/d -22°C | Anomali: di atas -10°C (pintu terbuka/kerusakan)
        suhu = round(random.uniform(-8.0, -5.0), 2) if is_anomaly else round(random.uniform(-22.0, -18.0), 2)
        payload = {
            "suhu": suhu,
            "pm25": None, "kelembapan": None, "amonia": None,
            "status_pintu": None, "tekanan": None
        }

    elif tipe == "kelembapan":
        # Normal: 85%–95% | Anomali: di bawah 70% (risiko freezer burn)
        kelembapan = round(random.uniform(50.0, 65.0), 2) if is_anomaly else round(random.uniform(85.0, 95.0), 2)
        payload = {
            "kelembapan": kelembapan,
            "pm25": None, "suhu": None, "amonia": None,
            "status_pintu": None, "tekanan": None
        }

    elif tipe == "amonia":
        # Normal: 0–10 ppm | Anomali: >25 ppm (berbahaya – kebocoran refrigran)
        amonia = round(random.uniform(28.0, 50.0), 2) if is_anomaly else round(random.uniform(0.5, 9.5), 2)
        # pm25 digunakan sebagai proxy anomali (> 150 untuk trigger alert)
        pm25_equiv = amonia * 6.0 if is_anomaly else amonia * 1.5
        payload = {
            "amonia": amonia,
            "pm25": round(pm25_equiv, 2),
            "suhu": None, "kelembapan": None,
            "status_pintu": None, "tekanan": None
        }

    elif tipe == "pintu":
        # Normal: 0 (tertutup) | Anomali: 1 (terbuka)
        status_pintu = 1 if is_anomaly else 0
        # pm25 tinggi jika pintu terbuka (proxy anomali)
        pm25_equiv = round(random.uniform(160.0, 200.0), 2) if is_anomaly else round(random.uniform(5.0, 20.0), 2)
        payload = {
            "status_pintu": status_pintu,
            "pm25": pm25_equiv,
            "suhu": None, "kelembapan": None,
            "amonia": None, "tekanan": None
        }

    elif tipe == "tekanan":
        # Normal: 50–80 Pa | Anomali: < 20 Pa (penumpukan es/frost)
        tekanan = round(random.uniform(5.0, 18.0), 2) if is_anomaly else round(random.uniform(50.0, 80.0), 2)
        pm25_equiv = round(random.uniform(155.0, 190.0), 2) if is_anomaly else round(random.uniform(10.0, 30.0), 2)
        payload = {
            "tekanan": tekanan,
            "pm25": pm25_equiv,
            "suhu": None, "kelembapan": None,
            "amonia": None, "status_pintu": None
        }
    else:
        payload = {}

    # Gabungkan data umum
    data = {
        "sensor_id":    sensor["sensor_id"],
        "lokasi":       sensor["lokasi"],
        "tipe_sensor":  tipe,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        **payload
    }
    return data


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[✓] Terhubung ke broker MQTT {BROKER_HOST}:{BROKER_PORT}")
    else:
        print(f"[✗] Gagal terhubung, kode: {rc}")


def on_publish(client, userdata, mid):
    print(f"    → Pesan #{mid} terkirim")


def main():
    client = mqtt.Client(client_id="publisher-cold-storage")
    client.on_connect = on_connect
    client.on_publish  = on_publish

    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.loop_start()
    except ConnectionRefusedError:
        print("[✗] Tidak dapat terhubung ke broker. Pastikan Mosquitto berjalan.")
        return

    print(f"\n{'='*60}")
    print("   COLD STORAGE SENSOR PUBLISHER")
    print(f"{'='*60}")
    print(f"Topik  : {TOPIC}")
    print(f"Interval: setiap {INTERVAL} detik")
    print(f"Sensor  : {len(SENSORS)} unit\n")

    cycle = 1
    try:
        while True:
            print(f"\n[Siklus #{cycle}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            for sensor in SENSORS:
                data    = generate_sensor_data(sensor)
                payload = json.dumps(data, ensure_ascii=False)
                result  = client.publish(TOPIC, payload, qos=1)
                status  = "ANOMALI ⚠️" if (data.get("pm25") or 0) > 150 else "normal"
                print(f"  [{sensor['sensor_id']:10s}] {sensor['lokasi']:12s} | {sensor['tipe']:10s} | {status}")
            cycle += 1
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\n[i] Publisher dihentikan oleh pengguna.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()