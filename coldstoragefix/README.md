# 🧊 Cold Storage IoT Monitoring System - Project Pertemuan 6

Sistem pemantauan kualitas lingkungan untuk **Cold Storage (ruang penyimpanan daging)** berbasis arsitektur IoT dengan MQTT dan MongoDB.

---

## 👥 Pembagian Peran

| Anggota | Peran | File |
|---------|-------|------|
| Anggota 1 | MQTT Publisher Simulasi | `pub_udara.py` |
| Anggota 2 | MQTT Subscriber & Penyimpanan | `sub_udara.py` |
| Anggota 3 | Analisis & Dashboard | `analisis_dashboard.py` |
| Anggota 4 | Status Terkini & Dokumentasi | `status_udara.py` |

---

## 🌡️ Sensor yang Digunakan

| Sensor | ID | Variabel | Kondisi Bahaya |
|--------|-----|----------|----------------|
| Suhu (PT100/DS18B20) | TEMP-A1, TEMP-B1 | `suhu` °C | > -10°C |
| Kelembapan (DHT22) | HUM-A1, HUM-B1 | `kelembapan` % | < 70% |
| Gas Amonia (MQ-137) | NH3-A1, NH3-B1 | `amonia` ppm | > 25 ppm |
| Status Pintu (Magnetic Switch) | DOOR-A1, DOOR-B1 | `status_pintu` 0/1 | = 1 (terbuka) |
| Tekanan Diferensial | PRESS-A1, PRESS-B1 | `tekanan` Pa | < 20 Pa |

---

## ⚙️ Prasyarat

- Python 3.9+
- MongoDB (lokal atau Atlas)
- Mosquitto MQTT Broker

### Install Mosquitto (Windows)
```
https://mosquitto.org/download/
```

### Install Mosquitto (Linux/Mac)
```bash
sudo apt install mosquitto mosquitto-clients   # Ubuntu/Debian
brew install mosquitto                          # Mac
```

### Start Mosquitto
```bash
mosquitto -v   # verbose mode
```

---

## 🚀 Cara Menjalankan Sistem

### Langkah 1 – Clone & Install Dependencies
```bash
git clone <repo>
cd cold_storage_iot
pip install -r requirements.txt
```

### Langkah 2 – Konfigurasi Environment
```bash
cp .env.example .env
# Edit .env sesuai konfigurasi MongoDB dan MQTT Anda
```

### Langkah 3 – Inisialisasi Database MongoDB
```bash
python setup_mongodb.py
```
> Membuat database `kelompok6`, koleksi `kualitas_udara` dan `alert`, serta mengisi data historis 24 jam.

### Langkah 4 – Jalankan Subscriber (Terminal 1)
```bash
python sub_udara.py
```

### Langkah 5 – Jalankan Publisher (Terminal 2)
```bash
python pub_udara.py
```

### Langkah 6 (Opsional) – Status Monitor (Terminal 3)
```bash
python status_udara.py
```

### Langkah 7 (Opsional) – Buat Dashboard & Export CSV
```bash
python analisis_dashboard.py
```
Output: `dashboard_udara.png` dan `data_24jam.csv`

---

## 📁 Struktur File

```
cold_storage_iot/
├── pub_udara.py           # Anggota 1: Publisher MQTT
├── sub_udara.py           # Anggota 2: Subscriber + MongoDB
├── analisis_dashboard.py  # Anggota 3: Analisis & Grafik
├── status_udara.py        # Anggota 4: Status Monitor
├── setup_mongodb.py       # Setup & seed database
├── requirements.txt       # Dependensi Python
├── .env.example           # Template environment variables
└── README.md              # Dokumentasi ini
```

---

## 🗄️ Struktur Database MongoDB

**Database:** `kelompok6`

### Koleksi `kualitas_udara`
```json
{
  "sensor_id":    "NH3-A1",
  "lokasi":       "Cold Room A",
  "tipe_sensor":  "amonia",
  "timestamp":    "2025-01-15T08:30:00+00:00",
  "suhu":         null,
  "kelembapan":   null,
  "amonia":       8.5,
  "status_pintu": null,
  "tekanan":      null,
  "pm25":         12.75
}
```

### Koleksi `alert`
```json
{
  "sensor_id":   "NH3-A1",
  "lokasi":      "Cold Room A",
  "tipe_sensor": "amonia",
  "pm25":        210.0,
  "timestamp":   "2025-01-15T08:30:00+00:00",
  "pesan":       "Amonia berbahaya! NH₃=35.0 ppm",
  "created_at":  "2025-01-15T08:30:00+00:00"
}
```

---

## 🔗 Website Dashboard

Buka `index.html` di browser untuk melihat dashboard web interaktif.

---

## 📌 Catatan

- Nilai `pm25` pada sistem ini berfungsi sebagai **proxy universal anomali** untuk memudahkan deteksi lintas tipe sensor.
- Setiap sensor memiliki probabilitas **5%** untuk menghasilkan kondisi anomali dalam simulasi.
- Threshold bahaya: `pm25 > 150` (ekuivalen dengan kondisi berbahaya pada masing-masing sensor).
