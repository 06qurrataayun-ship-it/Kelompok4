STUDI KASUS

//data dummy

db.produksi_harian.drop()
var docs = [];
var mesinList = []; for (let i=1;i<=10;i++) mesinList.push("M"+i.toString().padStart(2,'0'));
var start = new Date(2026,3,1); // April
for (let i=0; i<200; i++) {
    var tgl = new Date(start.getTime() + Math.floor(Math.random()*90)*86400000);
    var shift = Math.floor(Math.random()*3)+1;
    var target = Math.floor(Math.random()*301)+200;
    var actual_ok = Math.floor(target * (0.6 + Math.random()*0.4));
    var actual_reject = Math.floor(actual_ok * Math.random()*0.15);
    var durasi_tersedia = 480;
    var durasi_operasi = Math.floor(durasi_tersedia * (0.7 + Math.random()*0.3));
    docs.push({
        mesin: mesinList[Math.floor(Math.random()*10)],
        tanggal: tgl,
        shift: shift,
        target: target,
        actual_ok: actual_ok,
        actual_reject: actual_reject,
        durasi_operasi_menit: durasi_operasi,
        durasi_tersedia_menit: durasi_tersedia
    });
    if (docs.length === 200) { db.produksi_harian.insertMany(docs); docs = []; }
}


// pipeline agregasi untuk menghitung OEE per mesin, per bulan. (Gunakan $group dengan _id { mesin, bulan: { $month: "$tanggal" } }).

db.produksi_harian.aggregate([
  // Tahap 1: Tidak perlu $match karena ingin semua data
  // Tahap 2: Group by mesin dan bulan
  { $group: {
      _id: {
        mesin: "$mesin",
        bulan: { $month: "$tanggal" },
        tahun: { $year: "$tanggal" }
      },
      total_target: { $sum: "$target" },
      total_ok: { $sum: "$actual_ok" },
      total_reject: { $sum: "$actual_reject" },
      total_op: { $sum: "$durasi_operasi_menit" },
      total_avail: { $sum: "$durasi_tersedia_menit" }
  }},
  // Tahap 3: Hitung OEE
  { $project: {
      _id: 0,
      mesin: "$_id.mesin",
      bulan: "$_id.bulan",
      tahun: "$_id.tahun",
      total_ok: 1,
      total_target: 1,
      total_reject: 1,
      availability: { $divide: ["$total_op", "$total_avail"] },
      performance: { $divide: ["$total_ok", "$total_target"] },
      quality: { $divide: ["$total_ok", { $add: ["$total_ok", "$total_reject"] } ] },
      OEE: {
        $multiply: [
          { $divide: ["$total_ok", "$total_target"] },
          { $divide: ["$total_op", "$total_avail"] },
          { $divide: ["$total_ok", { $add: ["$total_ok", "$total_reject"] } ] }
        ]
      }
  }},
  // Tahap 4: Urutkan berdasarkan OEE terendah
  { $sort: { OEE: 1 } }
])


//hanya mesin yang OEE < 0.8

db.produksi_harian.aggregate([
  // Tahap 1: Tidak perlu $match karena ingin semua data
  // Tahap 2: Group by mesin dan bulan
  { $group: {
      _id: {
        mesin: "$mesin",
        bulan: { $month: "$tanggal" },
        tahun: { $year: "$tanggal" }
      },
      total_target: { $sum: "$target" },
      total_ok: { $sum: "$actual_ok" },
      total_reject: { $sum: "$actual_reject" },
      total_op: { $sum: "$durasi_operasi_menit" },
      total_avail: { $sum: "$durasi_tersedia_menit" }
  }},
  // Tahap 3: Hitung OEE
  { $project: {
      _id: 0,
      mesin: "$_id.mesin",
      bulan: "$_id.bulan",
      tahun: "$_id.tahun",
      total_ok: 1,
      total_target: 1,
      total_reject: 1,
      availability: { $divide: ["$total_op", "$total_avail"] },
      performance: { $divide: ["$total_ok", "$total_target"] },
      quality: { $divide: ["$total_ok", { $add: ["$total_ok", "$total_reject"] } ] },
      OEE: {
        $multiply: [
          { $divide: ["$total_ok", "$total_target"] },
          { $divide: ["$total_op", "$total_avail"] },
          { $divide: ["$total_ok", { $add: ["$total_ok", "$total_reject"] } ] }
        ]
      }
  }},  { $match: { OEE: { $lt: 0.80 } } },
  // Tahap 4: Urutkan berdasarkan OEE terendah
  { $sort: { OEE: 1 } }
])


//Distribusi jumlah produksi per shift dalam bentuk bucket.


db.produksi_harian.aggregate([
  { $facet: {
      "shift1": [
        { $match: { shift: 1 } },
        { $bucket: { groupBy: "$actual_ok", boundaries: [0,200,300,400,600], default: "600+", output: { count: {$sum:1} } } }
      ],
      "shift2": [
        { $match: { shift: 2 } },
        { $bucket: { groupBy: "$actual_ok", boundaries: [0,200,300,400,600], default: "600+", output: { count: {$sum:1} } } }
      ],
      "shift3": [
        { $match: { shift: 3 } },
        { $bucket: { groupBy: "$actual_ok", boundaries: [0,200,300,400,600], default: "600+", output: { count: {$sum:1} } } }
      ]
  }}
])
