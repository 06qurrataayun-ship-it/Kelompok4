"""
api_server.py - REST API Backend untuk Web Monitoring Cold Storage
Menyediakan endpoint untuk dashboard, status sensor, alert, dan export CSV.

Jalankan: python api_server.py
Buka browser: http://localhost:5000
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import csv
import io
import os
from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
from pymongo import MongoClient, errors, DESCENDING

# ─── Konfigurasi ────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME   = "kelompok6"
COL_DATA  = "kualitas_udara"
COL_ALERT = "alert"

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

SENSOR_IDS = [
    "TEMP-A1", "TEMP-B1",
    "HUM-A1",  "HUM-B1",
    "NH3-A1",  "NH3-B1",
    "DOOR-A1", "DOOR-B1",
    "PRESS-A1","PRESS-B1",
]

# ─── Koneksi MongoDB ─────────────────────────────────────────────────────────
def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return client[DB_NAME], client


# ─── Endpoint: Status terkini semua sensor ──────────────────────────────────
@app.route("/api/status")
def api_status():
    try:
        db, client = get_db()
        col = db[COL_DATA]
        col_alert = db[COL_ALERT]

        results = []
        for sid in SENSOR_IDS:
            doc = col.find_one({"sensor_id": sid}, sort=[("timestamp", DESCENDING)])
            if doc:
                doc.pop("_id", None)
                results.append(doc)
            else:
                results.append({
                    "sensor_id": sid,
                    "lokasi": "—",
                    "tipe_sensor": "—",
                    "pm25": None,
                    "timestamp": None,
                })

        total_alerts = col_alert.count_documents({})
        client.close()

        return jsonify({
            "sensors": results,
            "total_alerts": total_alerts,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    except errors.ServerSelectionTimeoutError as e:
        return jsonify({"error": f"MongoDB tidak terjangkau: {str(e)}"}), 503


# ─── Endpoint: Data grafik 24 jam (agregasi per jam) ─────────────────────────
@app.route("/api/chart")
def api_chart():
    try:
        db, client = get_db()
        col = db[COL_DATA]
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        sensor_types = [
            {"tipe": "suhu",       "field": "suhu"},
            {"tipe": "kelembapan", "field": "kelembapan"},
            {"tipe": "amonia",     "field": "amonia"},
            {"tipe": "tekanan",    "field": "tekanan"},
        ]

        chart_data = {}
        for cfg in sensor_types:
            pipeline = [
                {"$match": {
                    "timestamp":   {"$gte": cutoff},
                    "tipe_sensor": cfg["tipe"],
                    cfg["field"]:  {"$ne": None}
                }},
                {"$addFields": {
                    "ts_date": {"$dateFromString": {"dateString": "$timestamp"}}
                }},
                {"$group": {
                    "_id": {
                        "lokasi": "$lokasi",
                        "hour":   {"$hour": "$ts_date"}
                    },
                    "avg_value": {"$avg": f"${cfg['field']}"}
                }},
                {"$sort": {"_id.hour": 1}}
            ]
            results = list(col.aggregate(pipeline))

            lokasi_data = {}
            for doc in results:
                loc = doc["_id"]["lokasi"]
                hour = doc["_id"]["hour"]
                if loc not in lokasi_data:
                    lokasi_data[loc] = []
                lokasi_data[loc].append({
                    "hour": hour,
                    "value": round(doc["avg_value"], 2)
                })

            chart_data[cfg["tipe"]] = lokasi_data

        client.close()
        return jsonify(chart_data)
    except errors.ServerSelectionTimeoutError as e:
        return jsonify({"error": str(e)}), 503


# ─── Endpoint: Alert terbaru ─────────────────────────────────────────────────
@app.route("/api/alerts")
def api_alerts():
    try:
        limit = int(request.args.get("limit", 20))
        db, client = get_db()
        col_alert = db[COL_ALERT]

        docs = list(col_alert.find(
            {}, {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit))

        client.close()
        return jsonify({"alerts": docs, "total": len(docs)})
    except errors.ServerSelectionTimeoutError as e:
        return jsonify({"error": str(e)}), 503


# ─── Endpoint: Ringkasan statistik ───────────────────────────────────────────
@app.route("/api/summary")
def api_summary():
    try:
        db, client = get_db()
        col = db[COL_DATA]
        col_alert = db[COL_ALERT]
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        total_docs = col.count_documents({"timestamp": {"$gte": cutoff}})
        total_alerts = col_alert.count_documents({"timestamp": {"$gte": cutoff}})
        total_danger = col.count_documents({
            "timestamp": {"$gte": cutoff},
            "pm25": {"$gt": 150}
        })

        # Rata-rata suhu 24 jam terakhir
        pipeline_suhu = [
            {"$match": {"tipe_sensor": "suhu", "timestamp": {"$gte": cutoff}, "suhu": {"$ne": None}}},
            {"$group": {"_id": None, "avg": {"$avg": "$suhu"}}}
        ]
        r_suhu = list(col.aggregate(pipeline_suhu))
        avg_suhu = round(r_suhu[0]["avg"], 2) if r_suhu else None

        # Rata-rata kelembapan
        pipeline_hum = [
            {"$match": {"tipe_sensor": "kelembapan", "timestamp": {"$gte": cutoff}, "kelembapan": {"$ne": None}}},
            {"$group": {"_id": None, "avg": {"$avg": "$kelembapan"}}}
        ]
        r_hum = list(col.aggregate(pipeline_hum))
        avg_hum = round(r_hum[0]["avg"], 2) if r_hum else None

        client.close()
        return jsonify({
            "total_data_24h": total_docs,
            "total_alerts_24h": total_alerts,
            "total_danger": total_danger,
            "avg_suhu": avg_suhu,
            "avg_kelembapan": avg_hum,
        })
    except errors.ServerSelectionTimeoutError as e:
        return jsonify({"error": str(e)}), 503


# ─── Endpoint: Export CSV 24 jam terakhir ────────────────────────────────────
@app.route("/api/export/csv")
def api_export_csv():
    try:
        db, client = get_db()
        col = db[COL_DATA]
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        docs = list(col.find(
            {"timestamp": {"$gte": cutoff}},
            {"_id": 0}
        ).sort("timestamp", 1))

        client.close()

        fieldnames = [
            "sensor_id", "lokasi", "tipe_sensor", "timestamp",
            "suhu", "kelembapan", "amonia", "status_pintu", "tekanan", "pm25"
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(docs)
        output.seek(0)

        filename = f"data_udara_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename
        )
    except errors.ServerSelectionTimeoutError as e:
        return jsonify({"error": str(e)}), 503


# ─── Serve index.html ─────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_file("index.html")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("   COLD STORAGE WEB MONITORING API")
    print("="*60)
    print(f"MongoDB  : {MONGO_URI} → {DB_NAME}")
    print(f"Server   : http://localhost:5000")
    print(f"Dashboard: http://localhost:5000/dashboard.html")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)