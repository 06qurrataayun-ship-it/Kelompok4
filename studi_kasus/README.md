## Studi Kasus

# Dashboard Monitoring Suhu Mesin

Skrip monitor.py membaca data suhu mesin dari koleksi suhu_mesin (database studi_kasus) selama 1 jam terakhir, menghitung rata-rata suhu per mesin menggunakan aggregation pipeline, mendeteksi mesin yang melewati ambang 90 C, serta mencatat alarm ke file alarm.log.

# Informasi File

Nama file : monitor.py

Database  : studi_kasus

Koleksi   : suhu_mesin

Log       : alarm.log

Cara pakai : python monitor.py
