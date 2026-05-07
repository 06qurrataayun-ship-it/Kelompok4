"""
sub_udara.py - MQTT Subscriber & Penyimpanan ke MongoDB
Anggota 2: MQTT Subscriber

Menerima pesan dari topik 'pabrik/udara', menyimpan ke MongoDB,
dan mendeteksi anomali secara real-time.

Database : kelompok6
Koleksi  : kualitas_udara  → semua data sensor
           alert           → dokumen peringatan anomali
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import os
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pymongo import MongoClient, errors

# ─── Konfigurasi ────────────────────────────────────────────────────────────
MQTT_HOST   = "broker.hivemq.com"
MQTT_PORT   = 1883
MQTT_TOPIC  = "pabrik/udara"

MONGO_URI   = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME     = "kelompok6"
COL_DATA    = "kualitas_udara"
COL_ALERT   = "alert"

PM25_DANGER_THRESHOLD = 150  # µg/m³ (atau ekuivalen)

# ─── Inisialisasi MongoDB ────────────────────────────────────────────────────
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # test koneksi
    db         = mongo_client[DB_NAME]
    col_data   = db[COL_DATA]
    col_alert  = db[COL_ALERT]
    print(f"[✓] MongoDB terhubung: {MONGO_URI} → {DB_NAME}")
except errors.ServerSelectionTimeoutError as e:
    print(f"[✗] MongoDB tidak dapat dijangkau: {e}")
    raise SystemExit(1)


def handle_anomaly(data: dict):
    """Menyimpan dokumen alert dan mencetak notifikasi mencolok."""
    pm25 = data.get("pm25") or 0

    # Tentukan pesan berdasarkan tipe sensor
    tipe = data.get("tipe_sensor", "")
    if tipe == "amonia":
        pesan = f"Amonia berbahaya! NH₃={data.get('amonia')} ppm (proxy PM2.5={pm25})"
    elif tipe == "pintu":
        pesan = f"Pintu TERBUKA terlalu lama! Status={data.get('status_pintu')}"
    elif tipe == "tekanan":
        pesan = f"Tekanan diferensial rendah! Kemungkinan penumpukan es. Tekanan={data.get('tekanan')} Pa"
    else:
        pesan = f"PM2.5 berbahaya! Nilai={pm25} µg/m³"

    alert_doc = {
        "sensor_id": data.get("sensor_id"),
        "lokasi":    data.get("lokasi"),
        "tipe_sensor": data.get("tipe_sensor"),
        "pm25":      pm25,
        "timestamp": data.get("timestamp"),
        "pesan":     pesan,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        col_alert.insert_one(alert_doc)
    except errors.PyMongoError as e:
        print(f"[✗] Gagal menyimpan alert: {e}")
        return

    # Notifikasi mencolok di konsol
    border = "🔴" * 30
    print(f"\n{border}")
    print(f"  ⚠️  PERINGATAN ANOMALI TERDETEKSI ⚠️")
    print(f"  Sensor  : {alert_doc['sensor_id']} ({alert_doc['lokasi']})")
    print(f"  Tipe    : {alert_doc['tipe_sensor'].upper()}")
    print(f"  Pesan   : {alert_doc['pesan']}")
    print(f"  Waktu   : {alert_doc['timestamp']}")
    print(f"{border}\n")


def on_message(client, userdata, msg):
    """Callback saat pesan MQTT diterima."""
    try:
        payload = msg.payload.decode("utf-8")
        data    = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"[✗] Gagal parse pesan: {e}")
        return

    # Simpan ke koleksi utama
    try:
        col_data.insert_one(data)
        pm25 = data.get("pm25") or 0
        status = "⚠️ ANOMALI" if pm25 > PM25_DANGER_THRESHOLD else "✅ Normal"
        print(f"[{data.get('sensor_id'):10s}] {data.get('tipe_sensor'):10s} | PM25≈{pm25:6.1f} | {status}")
    except errors.PyMongoError as e:
        print(f"[✗] Gagal menyimpan data: {e}")
        return

    # Deteksi anomali
    pm25 = data.get("pm25") or 0
    if pm25 > PM25_DANGER_THRESHOLD:
        handle_anomaly(data)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC, qos=1)
        print(f"[✓] Terhubung ke MQTT & subscribe topik '{MQTT_TOPIC}'")
    else:
        print(f"[✗] Gagal terhubung MQTT, kode: {rc}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"[!] Terputus dari broker (kode {rc}), mencoba reconnect...")


def main():
    client = mqtt.Client(client_id="subscriber-cold-storage")
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect

    print(f"\n{'='*60}")
    print("   COLD STORAGE SENSOR SUBSCRIBER")
    print(f"{'='*60}")
    print(f"Broker : {MQTT_HOST}:{MQTT_PORT}")
    print(f"Topik  : {MQTT_TOPIC}")
    print(f"MongoDB: {DB_NAME} | {COL_DATA} | {COL_ALERT}\n")

    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_forever()  # blokir & auto-reconnect
    except KeyboardInterrupt:
        print("\n[i] Subscriber dihentikan.")
    except ConnectionRefusedError:
        print("[✗] Tidak dapat terhubung ke broker MQTT.")
    finally:
        client.disconnect()
        mongo_client.close()


if __name__ == "__main__":
    main()