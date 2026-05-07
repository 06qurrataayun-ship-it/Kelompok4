from pymongo import MongoClient
from datetime import datetime, timedelta
import random

client = MongoClient('mongodb://localhost:27017')
col = client['studi_kasus']['suhu_mesin']

mesin_list = ['CNC-01', 'CNC-02', 'LATHE-01', 'MILL-01']
docs = []
for i in range(40):
    docs.append({
        'mesin': random.choice(mesin_list),
        'suhu': round(random.uniform(70, 100), 1),
        'timestamp': datetime.utcnow() - timedelta(minutes=random.randint(0, 55))
    })

col.insert_many(docs)
print(f'{len(docs)} dokumen berhasil dimasukkan.')
