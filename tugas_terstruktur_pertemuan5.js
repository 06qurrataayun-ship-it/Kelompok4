TUGAS TERSTRUKTUR

//menggunakan database

use tugas5_<225443021>

//data dummy

var NIM = "225443021";
var dbName = "tugas5_" + 225443021;
db = db.getSiblingDB(dbName);

db.inspeksi.drop();
db.target_kualitas.drop();

var mesinList = []; 
for (let i = 1; i <= 10; i++) mesinList.push("M" + i.toString().padStart(2, '0'));

var batchIds = []; 
for (let i = 1; i <= 2000; i++) batchIds.push("B" + i.toString().padStart(4, '0'));

var inspektorList = ["Andi", "Budi", "Citra", "Dian", "Eka"];
var jenisCacatOptions = ["gores", "retak", "bengkok", "warna", "dimensi", "pori"];

var docsInspeksi = [];
var startDate = new Date(2026, 3, 1, 6, 0); // April 2026

for (let i = 0; i < 1500; i++) {
    // Simulasi randomisasi waktu (90 hari)
    var randomMinutes = Math.floor(Math.random() * (60 * 24 * 90));
    var tanggal = new Date(startDate.getTime() + randomMinutes * 60000);
    
    // Tentukan shift berdasarkan jam
    var jam = tanggal.getHours();
    var shift = (jam < 14) ? 1 : (jam < 22 ? 2 : 3);
    
    var jumlah = Math.floor(Math.random() * 401) + 100; // 100-500
    var reject = Math.floor(jumlah * (Math.random() * 0.10)); // 0-10% reject
    
    // Ambil 1-3 jenis cacat secara acak
    var shuffledCacat = jenisCacatOptions.sort(() => 0.5 - Math.random());
    var jenis = shuffledCacat.slice(0, Math.floor(Math.random() * 3) + 1);

    docsInspeksi.push({
        batch_id: batchIds[Math.floor(Math.random() * batchIds.length)],
        mesin: mesinList[Math.floor(Math.random() * mesinList.length)],
        tanggal: tanggal,
        shift: shift,
        inspektor: inspektorList[Math.floor(Math.random() * inspektorList.length)],
        jumlah_diperiksa: jumlah,
        cacat_ditemukan: reject,
        jenis_cacat: jenis
    });

    if (docsInspeksi.length === 500) {
        db.inspeksi.insertMany(docsInspeksi);
        docsInspeksi = [];
    }
}
if (docsInspeksi.length > 0) db.inspeksi.insertMany(docsInspeksi);
print("Data inspeksi selesai. Total: " + db.inspeksi.countDocuments({}));


var docsTarget = [];
for (let i = 1; i <= 2000; i++) {
    var batch = "B" + i.toString().padStart(4, '0');
    var targetCacat = Math.floor(Math.random() * 15) + 1; // 1-15

    docsTarget.push({
        batch_id: batch,
        target_maks_cacat: targetCacat
    });

    if (docsTarget.length === 500) {
        db.target_kualitas.insertMany(docsTarget);
        docsTarget = [];
    }
}


//menghingtung persentase cacat per batch
db.inspeksi.aggregate([
  {
    $addFields: {
      persen_cacat: { $multiply: [ { $divide: ["$cacat_ditemukan", "$jumlah_diperiksa"] }, 100 ] }
	}
  },
  { $sort: { persen_cacat: -1 } },
  { $limit: 10 } // Ini harus di dalam array [ ] dan menggunakan $
])

//Gabungkan target kualitas menggunakan $lookup, lalu tandai batch dengan statu “OK” atau “NOT OK” jika persentase melebihi target
db.inspeksi.aggregate([
  { $lookup: {
  	from: "target_kualitas",
  	localField: "batch_id",
  	foreignField: "batch_id",
  	as: "target_info"
  }},
  { $unwind: "$target_info" },
  { $addFields: {
  	persen_cacat: { $multiply: [ { $divide: ["$cacat_ditemukan", "$jumlah_diperiksa"] }, 100 ] },
  	target_maks: "$target_info.target_maks_cacat"
  }},
  { $addFields: {
  	status: { $cond: { if: { $gt: ["$persen_cacat", "$target_maks"] }, then: "NOT OK", else: "OK" } }
  }},
  { $project: {
  	_id: 0,
  	batch_id: 1,
  	mesin: 1,
  	persen_cacat: 1,
  	target_maks: 1,
  	status: 1,
  	selisih: { $subtract: ["$persen_cacat", "$target_maks"] }
  }},
  { $sort: { selisih: -1 } },
{ $limit:10 }
])

//Menghitung jumlah batch NOT OK per mesin per minggu (dengan menggunakan $week)
db.inspeksi.aggregate([
  { $lookup: {
  	from: "target_kualitas",
  	localField: "batch_id",
  	foreignField: "batch_id",
  	as: "target_info"
  }},
  { $unwind: "$target_info" },
  { $addFields: {
  	persen_cacat: { $multiply: [ { $divide: ["$cacat_ditemukan", "$jumlah_diperiksa"] }, 100 ] }
  }},
  { $addFields: {
  	status: { $cond: { if: { $gt: ["$persen_cacat", "$target_info.target_maks_cacat"] }, then: "NOT OK", else: "OK" } }
  }},
  { $match: { status: "NOT OK" } },
  { $group: {
  	_id: {
    	mesin: "$mesin",
    	minggu: { $week: "$tanggal" },
    	tahun: { $year: "$tanggal" }
  	},
  	jumlah_NOT_OK: { $sum: 1 }
  }},
  { $sort: { "_id.tahun": 1, "_id.minggu": 1, "_id.mesin": 1 } }
])


//Tampilkan top 3 mesin dengan jumlah NOT OK terbanyak
db.inspeksi.aggregate([
  { $match: { tanggal: { $gte: ISODate("2026-06-01"), $lt: ISODate("2026-07-01") } } },
  { $lookup: {
  	from: "target_kualitas",
  	localField: "batch_id",
  	foreignField: "batch_id",
  	as: "target_info"
  }},
  { $unwind: "$target_info" },
  { $addFields: {
  	persen_cacat: { $multiply: [ { $divide: ["$cacat_ditemukan", "$jumlah_diperiksa"] }, 100 ] },
  	status: { $cond: { if: { $gt: [ { $multiply: [ { $divide: ["$cacat_ditemukan", "$jumlah_diperiksa"] }, 100 ] }, "$target_info.target_maks_cacat" ] }, then: "NOT OK", else: "OK" } }
  }},
  { $facet: {
  	"total_batch": [
    	{ $count: "count" }
  	],
  	"rata_cacat": [
    	{ $group: { _id: null, avg_cacat: { $avg: "$persen_cacat" } } }
  	],
  	"mesin_terburuk": [
    	{ $match: { status: "NOT OK" } },
    	{ $group: { _id: "$mesin", jumlah: { $sum: 1 } } },
    	{ $sort: { jumlah: -1 } },
    	{ $limit: 3 }
  	]
  }}
])


//Menggunakan $facet untuk memberikan ringkasan bulanan (total produksi, rata-rata cacat, dan mesin terburuk dalam satu query)
db.inspeksi.aggregate([
  { $match: { tanggal: { $gte: ISODate("2026-06-01"), $lt: ISODate("2026-07-01") } } },
  { $lookup: {
  	from: "target_kualitas",
  	localField: "batch_id",
  	foreignField: "batch_id",
  	as: "target_info"
  }},
  { $unwind: "$target_info" },
  { $addFields: {
  	persen_cacat: { $multiply: [ { $divide: ["$cacat_ditemukan", "$jumlah_diperiksa"] }, 100 ] },
  	status: { $cond: { if: { $gt: [ { $multiply: [ { $divide: ["$cacat_ditemukan",
"$jumlah_diperiksa"] }, 100 ] }, "$target_info.target_maks_cacat" ] }, then: "NOT OK", else: "OK" } }
  }},
  { $facet: {
      "total_batch": [
    	{ $count: "count" }
  	],
      "rata_cacat": [
    	{ $group: { _id: null, avg_cacat: { $avg: "$persen_cacat" } } }
  	],
      "mesin_terburuk": [
    	{ $match: { status: "NOT OK" } },
    	{ $group: { _id: "$mesin", jumlah: { $sum: 1 } } },
    	{ $sort: { jumlah: -1 } },
    	{ $limit: 3 }
  	]
  }}
])

//indeks
db.inspeksi.createIndex({ mesin: 1, tanggal: 1 })

//$match awal
db.inspeksi.aggregate([
  {
    $match: {
      tanggal: {
        $gte: ISODate("2026-04-01"),
        $lte: ISODate("2026-06-30")
      },
      mesin: "M01"
    }
  },
  {
    $group: {
      _id: "$mesin",
      total: { $sum: "$jumlah_diperiksa" }
    }
  }
])

//proyeksi minimal
db.inspeksi.aggregate([
  { $match: { mesin: "M01" } },
  {
    $project: {
      mesin: 1,
      tanggal: 1,
      jumlah_diperiksa: 1,
      cacat_ditemukan: 1
    }
  }
])