# ModelGate — Backlog Perbaikan & Keputusan

> Dokumen kerja. Dibuat saat sesi analisa kritis + diskusi repositioning.
> **Status: arah arsitektur sudah final (bagian G). Urutan eksekusi belum — F1 masih menggerbangi.**
> Setiap item punya ID supaya bisa dirujuk saat diskusi.
>
> Mulai baca dari **bagian G** — di situ kompasnya. Bagian A–F adalah konsekuensinya.
>
> Legend status: `OPEN` belum dikerjakan · `DECIDED` keputusan sudah diambil, belum dikerjakan · `DONE` selesai · `WONTFIX` sengaja tidak dikerjakan (dengan alasan)

---

## G. Keputusan arsitektur — final

Kompas untuk semua keputusan berikutnya:

> *"Apakah perubahan ini membuat MGS lebih kuat sebagai spesifikasi, atau hanya membuat server lebih rumit?"*

Pergeseran pola pikir yang mendasari seluruhnya: **ModelGate bukan lagi produk utama — ModelGate adalah implementasi dari MGS.**

| ID | Keputusan | Status |
|---|---|---|
| G1 | MGS adalah spesifikasi terbuka | `DECIDED` |
| G2 | ModelGate adalah reference implementation dari MGS | `DECIDED` |
| G3 | `modelgate-core` jadi pusat seluruh logika audit | `DECIDED` |
| G4 | `modelgate-server` memakai `modelgate-core`, tidak boleh punya implementasi checker sendiri | `DECIDED` |
| G5 | Setiap implementasi MGS **MUST** mengevaluasi Manifest yang identik. Kesetaraan verdict didefinisikan pada **Manifest**, bukan pada dataset mentah | `DECIDED` (direvisi) |
| G6 | MGS dikembangkan independen dari ModelGate sehingga implementasi lain dimungkinkan | `DECIDED` |
| G7 | Storage adalah turunan Manifest — tidak boleh menghilangkan informasi yang dibawa Manifest | `DECIDED` |
| G8 | Tidak ada tier/paket. Conformance tidak pernah dibatasi oleh lisensi, akun, atau pembayaran | `DECIDED` |

### G5 — rumusan normatif

```
Every MGS implementation MUST evaluate an identical Manifest.
Verdict equivalence is defined on Manifest, not on the raw dataset.
```

Rumusan ini lebih kuat dari versi pertama ("semua antarmuka menghasilkan hasil sama") karena memindahkan titik kesetaraan ke tempat yang benar. Checker yang sempurna pun tidak bisa menyelamatkan Manifest yang sudah kehilangan informasi.

Konsekuensinya: **beban pembuktian pindah dari checker ke Reader + Storage.**

### G7 — storage tidak boleh lossy

Rantai yang harus dijaga:

```
ZIP → Reader → Manifest → Storage → Manifest'
                    ↑                    ↓
                    └──── harus identik ──┘
```

Kalau `Manifest' ≠ Manifest`, MGS rusak — bukan sebagian, tapi seluruhnya, karena G5 adalah fondasi klaim reproducibility.

**✅ SELESAI (Fase 5).** `minio_service.py` ditulis ulang: objek disimpan pakai `Sample.uri` kanonik dari modelgate-core's Reader (sudah mengandung split/label/filename), bukan skema lama yang membuang split. Dibuktikan langsung lewat HTTP asli: upload `adhoc-split.zip` → MinIO menyimpan `train/cat/0.jpg`, `test/cat/1.jpg`, dst — bukan cuma diklaim benar oleh kode, diverifikasi isi storage-nya. Lebih jauh, `conformance/runner.py --tool server_client.py` membuktikan **12/12 fixture menghasilkan `dataset_hash` identik** dengan `modelgate-core` langsung — bukti G5 sungguhan, bukan cuma G7 sendirian.

Akar yang sama dengan A1 (juga sudah mati, lihat Fase 2).

### G5/G7 — mekanisme pembuktian

Aturan tanpa gate akan bocor pelan-pelan. Mekanismenya adalah D4:

```
conformance/fixtures/catdog/
        ├─→ core    → report.json ┐
        ├─→ CLI     → report.json ├─→ diff → beda 1 byte = CI gagal
        ├─→ server  → report.json │
        └─→ action  → report.json ┘
```

---

### G8 — tier dihapus

Menjawab F3. Seluruh mesin tier (`free`/`pro`/`max`) dibuang: batas upload, pemilihan analyzer, kuota harian, gating PDF.

**Alasan:** conformance yang bisa dibeli bukan conformance (C2). Peneliti tidak akan mensitasi tool yang menyembunyikan sebagian pemeriksaan di balik paywall. Di bawah G3, logika audit hidup di `modelgate-core` yang open source — tier di sana tidak punya arti sama sekali.

**Item yang otomatis larut:** A4, B1, B3, C2 (prinsipnya tetap hidup, mekanismenya hilang).

**Yang masih perlu diputuskan — lihat F9:** `auth_service` masih menyimpan JWT, API key, ownership, dan rate limiting. Tanpa tier, apakah auth tetap ada sebagai fitur multi-user opsional di server, atau ikut dibuang?

---

## A. Correctness — bug terverifikasi

Semua item di bagian ini sudah diverifikasi empiris (simulasi kode asli), bukan dugaan.

### A1 — `upload_directory` buang seluruh dataset untuk layout flat-class · P0 · ✅ MATI (Fase 2/5)

**File:** `dataset_service/services/minio_service.py:27-44`

`upload_directory()` mengasumsikan ZIP selalu punya **satu root folder**: ambil `entries[0]` sebagai root, lalu cari subfolder di dalamnya sebagai kelas.

`validate_zip_structure()` / `scan_extracted_dataset()` (`dataset_service/services/validator.py:48-160`) menerima **3 layout**. Upload hanya menangani 1.

Hasil simulasi memakai kode asli:

| Layout ZIP | Objek ter-upload ke MinIO |
|---|---|
| `PetImages/Cat/`, `PetImages/Dog/` (single root) | benar ✓ |
| `Cat/`, `Dog/` (flat-class) | **0 objek** |
| `train/Cat/`, `test/Cat/` (split) | **hanya 1 split, sisanya hilang** |

**Dampak:** DB mencatat N gambar, MinIO kosong, audit jalan di direktori kosong, tidak ada error. Silent data loss.

**Catatan penting:** `PetImages-Free-Subset.zip` — zip demo project sendiri, dipakai `test_pro_flow.sh` — adalah layout flat-class. Jalur demo tier Free kena bug ini.

**Akar masalah:** logika deteksi struktur ada di dua tempat dan tidak sinkron. Lihat D3 (Reader/Manifest) untuk perbaikan struktural.

---

### A2 — Dataset kosong mendapat grade A · P0 · ✅ MATI (Fase 2)

**File:** `report_service/services/health_score.py:20-24`

Semua komponen default ke nilai "netral" saat metriknya tidak ada. Tidak ada guard `total_images == 0`.

Diverifikasi jalan lewat kode asli:

```
input : dataset 0 gambar
output: {'score': 0.8, 'grade': 'A',
         'components': {'I': 1.0, 'U': 1.0, 'D': 1.0, 'Q': 0.0}}
```

Dataset nol gambar dinyatakan "siap dipakai training".

Terkait langsung dengan C1 (fail-closed) — ini bukan sekadar bugfix, ini pelanggaran prinsip spec.

---

### A3 — Skala grade di kode ≠ dokumentasi · P1 · OPEN

**Kode** (`report_service/services/health_score.py:26`): `A≥0.80, B≥0.60, C≥0.40, D<0.40`. **Grade F tidak ada.**

**Docs:**
- `ABOUT.md:112-118` → `A≥0.80, B 0.65–0.79, C 0.50–0.64, D 0.35–0.49, F<0.35`
- `README.md:16, 186` → "grade A–F"
- `PRD.md:240` → `A≥0.80, B≥0.60, C≥0.40, D<0.40` (**sesuai kode**)

Skor 0.45 → docs bilang D, kode kasih C. Skor 0.20 → docs bilang F, kode kasih D.

Dua dokumen resmi saling bertentangan soal output utama produk. Perlu satu sumber kebenaran — kemungkinan besar diganti total oleh C4 (conformance level).

---

### A4 — Health score tier Free tidak sebanding · ~~P1~~ · LARUT (G8)

**File:** `report_service/services/health_score.py`, `audit_service/routers/audits.py:26`

Free skip analyzer `duplicate` + `distribution` (bobot gabungan 50%), tapi keduanya tetap dihitung sebagai 1.0. Hasil test: dataset free tier dengan Q=0.85 → skor **0.97**.

Commit terakhir menambahkan `requested_analyzers` ke payload report supaya UI bisa menandai "Tidak diaudit" — tapi **angka skornya sendiri masih inflasi**. Perbaikan baru di lapisan tampilan, belum di lapisan perhitungan.

Terkait C2 (tier tidak boleh gate conformance).

---

### A5 — Distribution analyzer menghitung file, bukan gambar · P3 · ✅ MATI (Fase 5 — analyzer lama dihapus, diganti _checkers/balance.py)

**File:** `analysis_service/analyzers/distribution.py:22`

`sum(1 for _ in os.scandir(entry.path))` menghitung semua entry di folder kelas — termasuk file non-gambar dan subfolder. Menggeser Gini coefficient.

---

### A6 — `run_with_retry` tidak pernah pakai delay terakhir · P3 · ✅ MATI (Fase 5 — consumer.py lama dihapus)

**File:** `analysis_service/consumer.py:24-40`

`RETRY_DELAYS = [5, 15, 30]` — sleep hanya terjadi di attempt 0 dan 1, jadi nilai `30` tidak pernah terpakai. Attempt ketiga langsung tanpa jeda.

---

### A7 — `_verify_jwt` bisa lempar 500 · P3 · OPEN

**File:** `auth_service/routers/internal.py:35`

`payload["sub"], payload["plan"]` diakses langsung. Token lama/malformed tanpa claim `plan` → `KeyError` → HTTP 500, bukan 401.

---

## B. Security

### B1 — Fail-open: header plan hilang = tier `max` · ~~P1~~ · LARUT (G8)

**File:** `dataset_service/routers/upload.py:49`, `audit_service/routers/audits.py:60`, `report_service/routers/reports.py:63`

Ketiganya `Header(default="max")`. Komentar menyebut ini sengaja "selama pre-auth rollout window" — window itu sudah selesai, auth aktif penuh.

Sekarang jadi bahaya laten: satu kesalahan di `nginx.conf`, atau satu container di jaringan Docker yang sama, langsung dapat tier tertinggi tanpa autentikasi.

**Perbaikan:** default `"free"`. Fail closed.

---

### B2 — IDOR: audit bisa dibuat di dataset milik user lain · P1 · ✅ SELESAI (Fase 5)

**File:** `audit_service/routers/audits.py:62-70`

`create_audit()` query `DatasetReadOnly` **tanpa filter `user_id`**, dan tidak memanggil `_check_ownership`. (Fungsi itu ada dan dipakai di `retry_audit` dan `get_audit`, tapi tidak di `create_audit`.)

User A kirim `dataset_id` milik user B → lolos. Blok dedup mengembalikan audit completed milik B lengkap dengan `audit_id`, `dataset_id`, `requested_analyzers`.

Membaca report-nya tertahan ownership check di `report_service`, jadi kebocorannya terbatas di metadata — tapi tetap: metadata bocor lintas-tenant + bisa memicu compute atas data orang lain.

**Catatan:** memory project menyatakan "ownership checks added to every single-resource endpoint" — pernyataan itu tidak akurat, `create_audit` terlewat.

---

### B3 — Kuota harian bisa dilewati lewat dedup · ~~P2~~ · LARUT (G8)

**File:** `audit_service/routers/audits.py:70-86`

Urutan sekarang: cek dedup **dulu**, baru `_check_daily_quota`. Request yang kena cache tidak menghabiskan kuota.

Bisa dianggap fitur (cache tidak makan compute), tapi dikombinasikan dengan B2 jadi jalur penyalahgunaan. Perlu keputusan sadar, bukan kebetulan.

---

### B4 — File `.env` tidak pernah terbaca · P1 · ✅ SELESAI (Fase 5)

**File:** `docker-compose.yml:63, 79, 99, 117, 130`

Kelima service pakai `env_file: .env.example`. README menyuruh `cp .env.example .env` — file `.env` itu **tidak berpengaruh sama sekali** terhadap environment container.

Artinya `JWT_SECRET=dev-only-insecure-secret-change-me` yang ter-commit di repo adalah secret yang benar-benar dipakai runtime, dan tidak ada cara mengubahnya lewat prosedur yang didokumentasikan.

**Perbaikan:** `env_file: .env` + perbaiki instruksi README.

---

### B5 — Port 8005 auth_service ter-publish, melewati rate limit · P1 · ✅ SELESAI (Fase 5)

**File:** `docker-compose.yml` (service `auth_service`)

Empat service lain sudah benar pakai `expose:` saja, dengan rationale panjang tertulis di compose. `auth_service` masih `ports: "8005:8005"`.

Nginx membatasi `/api/v1/auth` ke 5 req/menit. `http://localhost:8005/api/v1/auth/login` tidak dibatasi sama sekali → brute-force password terbuka, dan bcrypt yang lambat justru jadi vektor DoS.

---

### B6 — JWT di query string WebSocket · P2 · OPEN

**File:** `frontend/src/pages/AuditPage.tsx:37`, `cli/mgs.py:248`

`?token=<jwt>` masuk ke access log Nginx dalam plaintext, dan ke browser history.

Batasan protokol WebSocket (browser tidak bisa set custom header saat handshake) memang nyata dan sudah didokumentasikan di kode. Yang belum ada: mitigasinya — token WS berumur pendek, sekali pakai.

---

## C. Keputusan tingkat spesifikasi (MGS)

Muncul dari diskusi repositioning: **MGS = spesifikasi terbuka, ModelGate = reference implementation.**

### C1 — MGS-0000: Fail Closed · DISKUSI

Prinsip dasar yang harus jadi requirement pertama:

> Ketiadaan bukti bukan bukti kepatuhan. Requirement yang tidak dapat dievaluasi harus dilaporkan `NOT_EVALUATED`, tidak pernah `PASS`.

`health_score.py:20-24` sekarang melakukan persis yang dilarang (metrik hilang → default 1.0). Ini yang menyebabkan A2 dan A4.

Kalau produknya "Dataset Trust", mode gagal berupa *silently certifying nothing as compliant* itu fatal — bukan sekadar bug.

---

### C2 — Tier tidak boleh menentukan conformance · DECIDED → diganti G8

Kalau MGS adalah spesifikasi, tier komersial **tidak boleh** menentukan requirement mana yang dievaluasi. Kalau boleh, "MGS 0.97" tidak punya makna tunggal — dan spec dengan hasil tak sebanding antar-implementasi bukan spec.

Aturan yang diusulkan:
- Tier **boleh** gate kenyamanan: PDF, kuota, kecepatan, retensi, dashboard, dukungan.
- Tier **tidak boleh** gate conformance. Free → jalankan semua requirement, atau keluarkan `PARTIAL (5 of 7 evaluated)` dan **tolak** memberikan level.

---

### C3 — Verdict semantics · DISKUSI

Ganti angka tunggal dengan verdict per-requirement: `PASS` / `FAIL` / `NOT_EVALUATED` / `PARTIAL`.

Alasan: pengguna tidak peduli `0.82`. Yang ditanya: *"Can I trust this dataset?"* Jawaban yang berguna: `PASS — SAFE TO TRAIN` atau `FAIL — HIGH DUPLICATION`.

Angka jadi ringkasan, bukan produk.

---

### C4 — Penamaan level conformance · DISKUSI

Hindari **"MGS Certified"** — kata *certified* mengimplikasikan badan otoritas penerbit sertifikat. Proyek solo tidak punya itu; reviewer akan langsung menandainya.

Alternatif yang bisa dipertahankan:

```
MGS-1.0 Conformant — Level A (7/7 requirements passed)
```

Menggantikan skala grade A–F (lihat A3).

---

### C5 — Ambiguitas nama MGS · DISKUSI

Sekarang `MGS` = nama repo = nama produk = nama spec. Kalimat "ModelGate implements MGS" jadi tak bermakna karena merujuk benda yang sama.

Perlu dipisah:
- `MGS` = spesifikasi (repo terpisah, mis. `mgs-spec`)
- `ModelGate` = reference implementation

---

### C6 — Threshold butuh justifikasi · OPEN

Konstanta ajaib tanpa alasan tertulis:
- `HAMMING_THRESHOLD = 10` — `analysis_service/analyzers/duplicate.py:8`
- `EMPTY_STD_THRESHOLD = 5.0` — `analysis_service/analyzers/empty.py:6` (ada label "empirical", tanpa data)
- bobot health score `0.30 / 0.25 / 0.25 / 0.20` — tidak ada asal-usul
- ambang resolusi ±1σ — tidak ada alasan

Di spesifikasi, setiap threshold butuh: angka + alasan + referensi. Tanpa itu, spec tidak bisa dipertahankan di review.

**Naik jadi prasyarat blocking untuk C8:** implementor Rust/Go tidak boleh perlu membaca `duplicate.py` untuk tahu ambangnya. Selama threshold hanya hidup sebagai konstanta Python, MGS bukan spec — ia dokumentasi dari satu implementasi.

---

### C7 — Versioned Specification · DECIDED

MGS bernomor versi: `MGS 1.0`, `MGS 1.1`, `MGS 2.0`. Setiap report **wajib** mencantumkan `spec_version`, supaya paper bisa menyebut versi spesifikasi yang dipakai.

**Yang belum diputuskan — dua sumbu versi yang bergerak independen:**

| | Contoh | Berubah karena |
|---|---|---|
| Versi spec | `MGS 1.0` | requirement berubah/bertambah |
| Versi tool | `modelgate 1.4.2` | bugfix, performa, format baru |

`modelgate 2.x` bisa saja tetap mengimplementasikan `MGS 1.0`. Butuh **matriks dukungan** yang menyatakan versi spec mana yang didukung tiap versi tool, dan flag `--spec` supaya pengguna bisa mengunci versi spec secara eksplisit. Terkait D5.1.

---

### C8 — Reference Implementation · DECIDED

ModelGate adalah reference implementation, **bukan satu-satunya**. Implementasi Rust/Go/Java dimungkinkan dan tetap conformant terhadap MGS.

**Prasyarat yang harus dipenuhi supaya klaim ini benar, bukan sekadar niat:**

1. **C6 selesai** — semua threshold terdefinisi di prosa spec, bukan di konstanta Python.
2. **Bahasa normatif** — pakai MUST/SHOULD/MAY ala RFC 2119. "Sebaiknya" tidak bisa diuji.
3. **Semantik numerik terdefinisi** — mode pembulatan, presisi float, urutan tie-break. `round(x, 4)` Python memakai banker's rounding; implementasi Rust yang memakai half-up akan menghasilkan angka berbeda pada kasus batas, dan G5 langsung batal.
4. **Korpus conformance dapat dijalankan lintas bahasa** (D4) — fixture + expected output dalam format netral (JSON), bukan pytest.

---

## D. Arsitektur & repositioning

### D1 — Positioning · DECIDED

Dari: *"Platform audit dataset."*
Ke: *"ModelGate — an open-source dataset governance framework for trustworthy computer vision datasets."*

MGS bukan skor, melainkan spesifikasi terbuka yang didefinisikan, didokumentasikan, dan diimplementasikan ModelGate sebagai reference implementation.

Target akhir bukan GitHub stars, tapi: **dikutip di Methods section paper orang lain.**

---

### D2 — Pisahkan `modelgate-core` dari `modelgate-server` · DECIDED

Pushback terbesar terhadap arsitektur sekarang: untuk target "dikutip di Methods section", stack microservice adalah **liability distribusi**. Tidak ada peneliti yang menyalakan 12 container untuk memvalidasi dataset sebelum training.

Jalur adopsi yang realistis:

```bash
pip install modelgate
modelgate check ./data --spec mgs-1.0
```

plus satu langkah di CI.

Usulan pemisahan:

| Paket | Isi | Distribusi |
|---|---|---|
| `modelgate-core` | pure Python, zero infra. Reader + Checker + Report | PyPI, CLI, GitHub Action, import di notebook |
| `modelgate-server` | stack microservice sekarang — deployment ter-host dari core yang sama | Docker Compose |

**Kelayakan:** analyzer sekarang sudah nyaris murni — tidak menyentuh DB atau MinIO, antarmukanya cuma `analyze(path, config)`. Ekstraksi realistis, bukan rewrite. Seluruh kerja UAS tetap utuh.

Microservice **tidak dibuang** — berubah peran jadi consumer dari library.

---

### D2.1 — Single Source of Truth · DECIDED

Seluruh logika audit hanya boleh hidup di `modelgate-core`. Server tidak boleh punya implementasi checker sendiri.

```
❌  modelgate-core/DuplicateChecker  +  modelgate-server/DuplicateChecker
✅  modelgate-core/DuplicateChecker  ←  dipanggil oleh modelgate-server
```

Tujuan: hasil CLI, Python API, dan Web selalu identik. Lihat G5.

---

### D2.2 — Product Hierarchy · DECIDED

```
MGS (Specification)
        ↓
  modelgate-core
        ↓
  ┌─────┴─────┬──────────────┬────────────┐
modelgate-cli  modelgate-server  GitHub Action  Python API
```

`modelgate-core` jadi pusat seluruh ekosistem.

---

### D3 — Refactor Reader → Manifest → Checker · DECIDED

Blocker multi-format: kelima analyzer hardcode `os.walk(dataset_path)` (`corruption.py:12`, `empty.py:16`, `resolution.py:14`, `duplicate.py:16`, `distribution.py:22`). Analyzer terikat ke filesystem.

Usulan tiga lapis:

```
Reader   (ZIP | COCO | YOLO | ImageFolder | HuggingFace | S3 | DICOM | Roboflow | Kaggle)
   ↓
Manifest (normalized: samples[], labels[], splits[], uri, bytes, meta)
   ↓
Checker  (MGS-0001..000N — hanya membaca Manifest)
```

Manfaat ganda:
1. "Tambah format" berubah dari menyentuh 5 analyzer jadi menulis 1 Reader.
2. **Memperbaiki A1 secara struktural** — deteksi struktur jadi satu tempat, bukan dua implementasi tak sinkron.

---

### D3.1 — Reader Independence · DECIDED

Checker tidak boleh tahu asal dataset. Checker hanya menerima `Manifest` — bukan folder, ZIP, COCO, atau YOLO.

Menambah format = menulis satu Reader baru, nol perubahan di checker.

**Konsekuensi yang harus dijaga:** Manifest wajib membawa *semua* informasi yang dibutuhkan checker manapun (split, label, path asli, ukuran, metadata). Kalau ada checker yang butuh sesuatu di luar Manifest, itu tanda desain Manifest bocor — perbaiki Manifest, jangan beri checker akses filesystem.

---

### D4 — Korpus conformance · DECIDED

Yang membedakan RFC beneran dari dokumen ide: **test suite**. HTML punya web-platform-tests, WCAG punya ACT Rules.

Usulan struktur:

```
conformance/
  MGS-0003-duplicate/
    pass-no-dup/           expect: PASS
    fail-30pct-dup/        expect: FAIL
    edge-empty/            expect: NOT_EVALUATED   ← A2: sekarang PASS
    edge-single-class/     expect: FAIL
    edge-flat-zip-layout/  expect: PASS            ← A1: sekarang silent 0 file
```

**Poin kunci:** korpus conformance untuk spec **adalah** test suite yang repo ini belum punya (lihat E1). Satu pekerjaan, dua manfaat.

---

### D5 — Syarat supaya layak dikutip · DISKUSI

Kalau ada paper menulis *"verified using ModelGate (MGS v1.4)"*, reviewer paper itu harus bisa mengulang hasilnya:

- **Determinisme** — tiap threshold terkunci & terjustifikasi (lihat C6), tie-break terdefinisi, versi analyzer tercatat.
- **Output self-describing** — sematkan `spec_version`, `tool_version`, `dataset_sha256`, dan config tiap checker ke dalam laporan. Primitifnya sudah ada: SHA-256 file hash di `dataset_service/routers/upload.py:66`.
- **Artefak citable** — Zenodo DOI per rilis (gratis, otomatis dari GitHub release). Tanpa DOI, orang tidak bisa mensitasi dengan benar.

---

### D5.1 — Stable API · OPEN

Begitu orang menulis `from modelgate import audit`, signature itu tidak boleh berubah tiap rilis. Paper 2027 memakai `audit(...)`, fungsi itu hilang di 2028 → paper tidak bisa direproduksi.

Butuh keputusan eksplisit:
- Permukaan API mana yang dijamin stabil (kemungkinan kecil saja: `audit()`, `Manifest`, `Report`) vs mana yang internal dan bebas berubah
- Kebijakan deprecation — berapa lama versi lama didukung sebelum dibuang
- Konvensi penandaan internal (prefix `_`, modul `modelgate._internal`)

Terkait C7 — ada **dua nomor versi** yang bergerak independen (versi spec vs versi tool). Butuh matriks dukungan, lihat C7.

---

### D6 — Ecosystem, dikirim sebagai monorepo · DECIDED

Target akhir tetap ekosistem lima komponen, tapi **jalannya lewat monorepo** — menjawab F2:

```
modelgate/
├── packages/
│   ├── modelgate-core/
│   ├── modelgate-cli/
│   ├── modelgate-server/
│   └── github-action/
├── specs/
│   └── mgs/
├── conformance/
└── docs/
```

Terpisah secara logika, satu repo secara GitHub. Pemecahan nanti lewat `git subtree` / `git filter-repo` kalau proyek berkembang.

**Batas alami untuk memecah:** saat ada orang di luar maintainer yang mengomentari atau mengusulkan perubahan pada `specs/mgs/`. Sebelum itu, lima CI + lima issue tracker + lima siklus rilis adalah biaya harian tanpa manfaat.

**Satu hal yang harus diputuskan bersamaan:** monorepo berarti `pip install modelgate` mem-publish dari subdirektori. Perlu ditetapkan sejak awal — nama distribusi PyPI, dan apakah `modelgate-cli` paket terpisah atau extra dari core (`pip install modelgate[cli]`). Mengubah nama paket setelah rilis pertama itu mahal.

---

### D7 — Distribution First · DECIDED

Urutan prioritas distribusi dibalik:

1. `pip install modelgate`
2. `modelgate check`
3. Python API
4. GitHub Action
5. Server

**Konsekuensi langsung ke backlog ini:** banyak item di bagian B (security) dan sebagian A hanya ada di jalur server. Di bawah D7, prioritasnya turun relatif terhadap apa pun yang menghalangi jalur `pip install`. Lihat ulang urutan saat menyusun plan.

---

## E. Kualitas & utang infrastruktur

### E1 — Nol test otomatis · P2 · OPEN

Tidak ada pytest, tidak ada vitest, tidak ada conftest. Satu-satunya artefak test: `test_pro_flow.sh` (skrip smoke curl end-to-end).

Repo punya 5006 baris OpenAPI spec dan **0 baris assertion**.

**Ini akar masalahnya:** A1, A2, A3, B2 — empat dari lima temuan P0/P1 — mati oleh satu file `test_minio_service.py` dan satu `test_health_score.py`.

CI (`.github/workflows/build.yml`) hanya build image. Tidak ada gate test maupun lint.

---

### E2 — `--reload` di image produksi · P2 · OPEN

**File:** semua `*/Dockerfile`

`CMD ["uvicorn", "main:app", ..., "--reload"]`. Mode development ikut ter-push ke GHCR sebagai artefak rilis.

---

### E3 — Alembic terpasang, migrasi nol · P2 · OPEN

`alembic==1.13.1` ada di kelima `requirements.txt`. Tidak ada `alembic.ini`, tidak ada direktori `versions/`.

Schema dibuat lewat `Base.metadata.create_all()` + `ALTER TABLE IF EXISTS` manual. Dependency mati; perubahan schema ke depan berisiko butuh `docker compose down -v`.

---

### E4 — Duplicate analyzer O(n²) · P3 · OPEN

**File:** `analysis_service/analyzers/duplicate.py:38-56`

12.500 gambar → ~78 juta perbandingan. Vektorisasi numpy mempercepat konstanta, tidak mengubah kompleksitas.

Risiko lebih besar: list `findings` bisa meledak jadi jutaan dict, dan seluruhnya masuk ke satu kolom JSONB.

---

### E5 — Env var MinIO tidak konsisten · P3 · ✅ SELESAI (Fase 5)

`analysis_service/services/minio_downloader.py:7-8` membaca `MINIO_HOST` + `MINIO_PORT`. `.env.example` hanya mendefinisikan `MINIO_ENDPOINT`.

Jalan sekarang **hanya karena kebetulan** nilai default fallback-nya sama. Ganti port MinIO di `.env.example` → analysis_service diam-diam tetap menunjuk ke `minio:9000`.

Tambahan: default `MINIO_SECRET_KEY` di file itu `"minioadmin"`, sedangkan nilai sebenarnya `"minioadmin123"`.

---

### E6 — Duplikasi blok nginx · P3 · ✅ SELESAI (Fase 5)

**File:** `nginx/nginx.conf`

`location /api/v1/datasets` dan `location /api/v1/datasets/` menduplikasi ~25 baris identik. Prefix pertama sudah mencakup keduanya.

---

## H. Kesiapan open source

Muncul dari keputusan go-public. Diverifikasi terhadap repo per 2026-07-27.

### H1 — Tidak ada LICENSE · BLOCKING · OPEN

Repo tidak punya `LICENSE` sama sekali. Tanpa lisensi, secara hukum **default-nya adalah hak cipta penuh** — orang lain tidak boleh memakai, memodifikasi, atau mendistribusikan, meskipun reponya publik. Ini membatalkan seluruh premis open source.

Butuh **dua** lisensi berbeda, karena spec dan implementasi adalah barang berbeda:

| Bagian | Lisensi lazim | Alasan |
|---|---|---|
| `packages/*` (kode) | Apache-2.0 | punya *patent grant* eksplisit — penting saat institusi/perusahaan mengadopsi. MIT tidak punya. |
| `specs/mgs/` (spesifikasi) | CC-BY-4.0 | spec dimaksudkan untuk disalin & diimplementasikan ulang (C8), bukan dieksekusi |

Pola ini dipakai banyak proyek spec+impl. Apache-2.0 lebih tepat dari MIT di sini justru karena target adopsinya akademik/institusional.

---

### H2 — Email asli ter-commit di repo publik · OPEN

**File:** `docker-compose.yml:142`

```yaml
PGADMIN_DEFAULT_EMAIL: agrieby.chaniago@student.uhb.ac.id
```

Email kampus asli, akan terbaca publik dan ter-scrape bot spam begitu repo dibuka. Ganti ke `admin@example.com`.

Catatan: mengganti di HEAD tidak menghapusnya dari riwayat commit. Untuk repo yang belum dikenal, biarkan saja di riwayat — biayanya tidak sebanding dengan `filter-repo`. Yang penting HEAD bersih.

---

### H3 — Bahasa dokumentasi · OPEN

Seluruh dokumentasi berbahasa Indonesia. Untuk target D5 (dikutip di Methods section) dan C8 (implementor bahasa lain), ini penghalang nyata.

Pemisahan yang masuk akal, bukan menerjemahkan semuanya:

| Wajib Inggris | Boleh tetap Indonesia |
|---|---|
| `specs/mgs/` — spec harus bisa diimplementasi orang lain | `VIDEO_SCRIPT.md`, `SLIDES.md` (materi UAS) |
| `README.md` root | `PRD.md` (dokumen internal) |
| Docstring API publik | komentar kode internal |
| Pesan error `modelgate-core` | — |

Pesan error yang berbahasa Indonesia (`"Dataset tidak ditemukan"`, `"File terlalu besar"`) akan muncul di terminal pengguna internasional — itu bagian dari permukaan API publik, bukan dokumentasi.

---

### H4 — `.git` lokal membawa 293MB blob mati · P3 · OPEN

`.git` = 282MB, tapi hanya **427 objek yang terjangkau** dari ref manapun; pack berisi 9987 blob (293MB) sisa `git add` dataset PetImages yang tidak pernah masuk commit.

**Kabar baiknya:** objek tak terjangkau tidak pernah ikut ter-push. Clone dari GitHub tetap kecil, dan riwayat publik bersih — sudah diverifikasi, tidak ada commit yang menyentuh path `PetImages*`.

Cukup dibereskan lokal:

```bash
git gc --prune=now
```

Tidak butuh `filter-repo`.

---

### H5 — Berkas standar repo publik · OPEN

Belum ada: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, template issue/PR, `CHANGELOG.md`.

Prioritas rendah sampai ada kontributor, **kecuali `CHANGELOG.md`** — itu terikat D5.1 (stable API) dan C7 (versi spec). Tanpa changelog, pengguna tidak bisa tahu rilis mana yang mengubah verdict. Untuk tool yang dipakai di paper, perubahan verdict antar-versi adalah informasi kritis.

---

## F. Pertanyaan terbuka — perlu diputuskan sebelum plan

| # | Pertanyaan | Menghalangi |
|---|---|---|
| ~~F1~~ | ~~UAS sudah dinilai?~~ | **TERJAWAB: sudah, nilai A. Perubahan merusak diizinkan. A1 TIDAK ditambal di arsitektur lama — lihat [ROADMAP.md](ROADMAP.md)** |
| ~~F2~~ | ~~Repo tetap satu, atau pisah?~~ | **TERJAWAB: monorepo — lihat D6** |
| ~~F3~~ | ~~Model tier dipertahankan?~~ | **TERJAWAB: dihapus — lihat G8** |
| F4 | Health Score dipertahankan sebagai ringkasan di samping verdict, atau dihapus total? | A3, C3, C4 |
| F5 | Format apa yang jadi target rilis pertama setelah ZIP? (ImageFolder / COCO / YOLO / HF) | D3 |
| F6 | Berapa requirement di MGS-1.0 — kunci di 7, atau mulai dari 3–4 yang benar-benar bisa dipertahankan? | C6, D4 |
| F7 | Target waktu: sprint pendek merapikan repo, atau program 1 tahun? | prioritisasi keseluruhan |
| F8 | GitHub org (`github.com/modelgate/*`) atau tetap di bawah akun pribadi? | D6, branding |
| F9 | Tanpa tier, apakah `auth_service` tetap ada sebagai multi-user opsional di server, atau ikut dibuang? | G8, ruang lingkup server |
| F10 | Nama distribusi PyPI + apakah CLI paket terpisah atau extra (`modelgate[cli]`)? | D6, D7 — mahal diubah setelah rilis |

**Catatan F8 — ada tenggatnya.** Pemindahan repo GitHub meninggalkan redirect otomatis, jadi murah secara teknis kapan pun. Yang tidak bisa dibatalkan: **URL yang sudah tercetak di paper dan DOI Zenodo yang sudah terbit.** Jadi F8 harus diputuskan **sebelum rilis ber-DOI pertama** (D5), bukan sebelum baris kode pertama.

**Status per akhir diskusi:** F1, F2, F3 terjawab. F4–F10 punya **jawaban default** di [ROADMAP.md](ROADMAP.md) bagian "Keputusan default" — dipakai kalau tidak dibantah.

Urutan eksekusi ada di [ROADMAP.md](ROADMAP.md). Dokumen ini tetap jadi daftar temuan; ROADMAP yang menentukan kapan tiap item dikerjakan.
