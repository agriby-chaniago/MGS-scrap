# ModelGate — Dataset Governance Framework untuk Computer Vision

## What — Apa itu ModelGate?

ModelGate adalah **reference implementation** dari **MGS** (Model Gate Standard) — spesifikasi terbuka yang mendefinisikan apa artinya
sebuah dataset gambar Computer Vision (CV) "layak dievaluasi", dan apa
yang harus dihasilkan oleh implementasi evaluasi itu agar dua
implementasi independen — di bahasa apa pun — bisa sampai pada verdict
yang sama untuk dataset yang sama. Spesifikasi lengkapnya ada di
`specs/mgs/`.

ModelGate bukan tool untuk melatih model — ModelGate adalah **penjaga
gerbang** sebelum dataset masuk ke pipeline training, dan implementasi
rujukan dari spesifikasi yang lebih besar dari dirinya sendiri: siapa
pun boleh membangun implementasi MGS lain, dan itu tetap dianggap sah
selama sesuai spesifikasi — lihat `specs/mgs/MGS-1.0.md` §7.

---

## Who — Untuk Siapa?

| Pengguna | Kebutuhan |
|---|---|
| **Peneliti & Mahasiswa** | Memastikan dataset yang dikumpulkan layak sebelum eksperimen dimulai, dan bisa mencantumkan versi spesifikasi yang dipakai di bagian Methods |
| **ML Engineer** | Audit dataset sebelum masuk pipeline training produksi — lewat CLI/CI, bukan hanya lewat UI |
| **Data Curator** | Mendeteksi masalah kualitas (duplikat, file rusak, distribusi tidak merata) secara otomatis dan reproducible |
| **Pembuat tooling lain** | Mengimplementasikan MGS di bahasa/platform lain, memakai spesifikasi sebagai kontrak, bukan kode ModelGate sebagai sumber kebenaran |

---

## Why — Mengapa MGS/ModelGate Dibutuhkan?

Dataset berkualitas buruk adalah penyebab utama model CV yang gagal — bukan arsitektur modelnya.

**Masalah umum dataset yang sering tidak terdeteksi secara manual:**

- File gambar rusak yang tetap terbaca sebagai valid oleh sistem file
- Gambar duplikat yang menyebabkan model overfit pada data tertentu
- Ketidakseimbangan kelas yang signifikan (Gini coefficient tinggi)
- Folder kelas yang kosong atau hampir kosong

Tanpa audit, masalah ini baru ditemukan saat akurasi model stagnan atau saat evaluasi gagal — setelah berjam-jam waktu training terbuang.

**Masalah yang lebih dalam yang MGS coba jawab:** "diaudit" tanpa
spesifikasi yang jelas gampang jadi klaim yang tidak bisa diverifikasi
ulang — dua orang menjalankan "audit" yang beda-beda hasilnya untuk
dataset yang sama, dengan threshold yang tidak terdokumentasi, dari alat
yang tidak bisa dijalankan ulang oleh orang lain. MGS mendefinisikan
threshold, semantik pembulatan, dan format Manifest secara eksplisit
justru supaya klaim "dataset ini lolos MGS-1.0" bisa direproduksi oleh
siapa pun, bukan hanya dipercaya begitu saja.

---

## When — Kapan Menggunakannya?

Digunakan **sebelum** proses training dimulai, sebagai checkpoint wajib dalam ML pipeline:

```
Pengumpulan Data → [MGS CHECK] → Preprocessing → Training → Evaluasi
```

Gunakan setiap kali:
- Dataset baru selesai dikumpulkan atau di-scraping
- Menggabungkan beberapa sumber dataset menjadi satu
- Menerima dataset dari pihak ketiga yang belum diverifikasi
- Menambahkan data baru ke dataset yang sudah ada
- Menyiapkan dataset untuk publikasi/paper, dan ingin mencantumkan bukti kualitas yang bisa diverifikasi ulang

---

## Where — Di Mana Berada dalam Ekosistem?

Berada di lapisan **Data Quality** — sebelum preprocessing dan training, setelah pengumpulan data mentah.

```
[Sumber Data]         raw images, scraping, labeling tools
      ↓
[MGS CHECK]           modelgate-core: audit otomatis, verdict per-requirement
      ↓
[Preprocessing]       augmentasi, normalisasi, split train/val/test
      ↓
[Training]            PyTorch, TensorFlow, Keras, dll
      ↓
[Evaluasi & Deploy]   inference, monitoring
```

Tidak terikat pada framework ML apapun. Fokus proyek sekarang murni
library/CLI — `packages/modelgate-core`, dipakai langsung di notebook
atau CI. Stack server/web/Streamlit (hasil fase UAS awal) diarsipkan,
bukan dikembangkan lagi — lihat `README.md` bagian "Archived
components". Jalur adopsi yang realistis untuk alat verifikasi adalah
`pip install` dan satu langkah di CI, bukan menyalakan satu stack
microservice penuh.

---

## How — Bagaimana Cara Kerjanya?

### 1. Reader membaca Dataset apa adanya

Dataset yang didukung format-nya (ZIP, direktori ImageFolder — format
lain menyusul, lihat `ROADMAP.md` Fase 6) dibaca oleh sebuah **Reader**
dan dinormalisasi menjadi **Manifest** — representasi netral yang tidak
lagi tahu apakah asalnya ZIP atau folder. Seluruh Checker di bawah ini
hanya membaca Manifest, tidak pernah menyentuh dataset mentah secara
langsung. Detail skema Manifest ada di `specs/mgs/MGS-1.0.md` §2.

### 2. Checker mengevaluasi tiap Requirement MGS-1.0

| Requirement | Checker | Yang Dievaluasi |
|---|---|---|
| MGS-0001 Structure | Structure | Minimal 2 kelas, tiap kelas punya ≥1 sample valid |
| MGS-0002 Integrity | Corruption | File gambar yang rusak atau tidak dapat dibaca |
| MGS-0003 Duplicate | Duplicate | Gambar hampir identik (perceptual hash, threshold terdokumentasi di spec) |
| MGS-0004 Balance | Distribution | Ketimpangan jumlah gambar antar kelas (Gini coefficient) |

Resolusi gambar tetap dilaporkan tapi sebagai metrik **informative**, bukan Requirement dengan verdict PASS/FAIL — lihat spec §5.5 untuk alasannya.

### 3. Verdict, bukan sekadar angka

Tiap Requirement menghasilkan salah satu dari empat verdict:

```
PASS            — dievaluasi, kondisinya terpenuhi
FAIL            — dievaluasi, kondisinya tidak terpenuhi
NOT_EVALUATED   — tidak bisa dievaluasi (data hilang/kosong) — TIDAK PERNAH
                  otomatis dianggap PASS (lihat MGS-0000, spec §3)
PARTIAL         — dievaluasi untuk sebagian Manifest saja
```

Angka ringkas (bekas "Health Score") tetap dihitung dan ditampilkan
sebagai metrik pembanding antar-versi dataset, tapi statusnya
**informative, not normative** — tidak boleh dipakai untuk mengklaim
kepatuhan terhadap MGS. Yang menentukan kepatuhan adalah verdict
per-Requirement di atas.

### 4. Laporan

Setiap laporan (`Report`, lihat spec §4) mencantumkan `spec_version`,
`tool_version`, dan `dataset_hash` — supaya siapa pun yang membaca
laporan tahu persis versi spesifikasi apa yang dipakai, alat versi
berapa yang menghasilkannya, dan dataset persis yang mana (lihat
`ROADMAP.md` Fase 4, "layak dikutip").

---

## Value — Nilai yang Diberikan

**Hemat waktu training.**
Dataset bermasalah yang lolos ke pipeline training membuang jam hingga berhari-hari compute time. Masalah terdeteksi dalam menit.

**Hasil model yang lebih baik.**
Dataset bersih menghasilkan model yang lebih general dan tidak overfit.

**Proses yang dapat direproduksi — ini yang membedakan MGS dari sekadar "tool audit".**
Laporan yang sama, dari dataset yang sama, dievaluasi terhadap versi spec yang sama, harus menghasilkan verdict yang sama — di implementasi apa pun. Itu bukan aspirasi, itu definisi konformansi (`specs/mgs/MGS-1.0.md` §7).

**Tidak terkunci ke satu tool.**
MGS adalah spesifikasi terbuka (lisensi CC BY 4.0, `specs/LICENSE`). ModelGate adalah satu implementasi rujukannya, bukan satu-satunya yang sah.
