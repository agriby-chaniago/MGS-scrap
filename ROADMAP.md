# ModelGate — Roadmap Restrukturisasi

> Disusun setelah F1 terjawab: **UAS sudah dinilai (A)**. Tidak ada lagi kendala demo — perubahan yang merusak diizinkan.
>
> Dasar keputusan ada di [`BACKLOG.md`](BACKLOG.md) bagian G. Dokumen ini hanya **urutan eksekusi**, bukan keputusan baru.
>
> Setiap fase punya **exit criteria** yang bisa diperiksa. Fase tidak dianggap selesai karena "sudah dikerjakan", tapi karena kriteria itu terpenuhi.

---

## Prinsip urutan

**1. Jangan tambal yang akan dibuang.**
A1 (`upload_directory`) **tidak diperbaiki di arsitektur lama.** Jalur itu dihapus di Fase 2. Memperbaikinya sekarang berarti membayar dua kali untuk desain yang akan mati.

**2. Spec dan implementasi ditulis berselang-seling, bukan berurutan.**
Spec ditulis lebih dulu supaya Manifest tidak dibentuk oleh kebetulan implementasi. Tapi spec yang ditulis tanpa umpan balik implementasi menghasilkan spec yang tidak bisa diimplementasi. Jadi: draf spec → implementasi → spec diperbaiki oleh temuan implementasi → **baru** dibekukan. Pembekuan terjadi di Fase 3, bukan Fase 1.

**3. Sempit dan tuntas, bukan luas dan setengah jadi.**
Risiko terbesar proyek ini bukan salah arsitektur — arsitekturnya sudah benar. Risikonya **mandek di tengah restrukturisasi**: monorepo sudah dipecah, core setengah jadi, server rusak, tidak ada yang bisa dipakai. Karena itu Fase 2–4 dirancang menghasilkan **tool yang benar-benar bisa dipasang dan dipakai** meski MGS baru punya 4 requirement.

**4. Server terakhir.**
Konsekuensi D7. Server tetap rusak selama Fase 1–4, dan itu tidak apa-apa.

---

## Fase 0 — Amankan & buka jalan

**Ukuran:** beberapa jam · **Bisa dikerjakan hari ini**

Semua di sini murah, tidak bergantung apa pun, dan sebagiannya **tidak bisa dilakukan lagi setelah kode lama hilang**.

| # | Aksi | Backlog |
|---|---|---|
| 0.1 | `git tag -a v0.1-uas` + push — abadikan kondisi UAS sebelum demolisi | — |
| 0.2 | `LICENSE` Apache-2.0 untuk kode | H1 |
| 0.3 | `specs/LICENSE` CC-BY-4.0 (disiapkan, diisi di Fase 1) | H1 |
| 0.4 | Ganti email asli di `docker-compose.yml:142` → `admin@example.com` | H2 |
| 0.5 | `git gc --prune=now` — buang 293MB blob mati lokal | H4 |

**Exit criteria**
- Tag `v0.1-uas` ada di GitHub dan bisa di-clone
- `LICENSE` ada di root; `git grep @student` tidak menghasilkan apa-apa
- `du -sh .git` di bawah 10MB

**Kenapa 0.1 duluan:** G8 menghapus tier, D3 menghapus jalur upload lama, D2 memindahkan seluruh analyzer. Kerja UAS — JWT, auth_request gateway, RabbitMQ, WebSocket, observability — akan hilang dari HEAD. Tag itu satu-satunya cara menunjuknya lagi nanti.

---

## Fase 1 — MGS 1.0 (draf) + kerangka monorepo

**Ukuran:** 1–2 minggu

### 1a. Draf spesifikasi

`specs/mgs/` — bahasa Inggris, bahasa normatif RFC 2119 (MUST/SHOULD/MAY).

Isi minimum:

- **MGS-0000 — Fail Closed.** Requirement yang tidak dapat dievaluasi dilaporkan `NOT_EVALUATED`, tidak pernah `PASS`. (C1)
- **Verdict semantics** — `PASS` / `FAIL` / `NOT_EVALUATED` / `PARTIAL`. (C3)
- **Semantik numerik** — mode pembulatan, presisi, urutan tie-break. Tanpa ini C8 tidak mungkin. (C6, C8)
- **Skema Manifest** — sumber kebenaran G5. Ini artefak terpenting di seluruh fase.
- **Skema report** — wajib memuat `spec_version`, `tool_version`, `dataset_hash`, config tiap checker. (C7, D5)
- **4 requirement awal** (usulan, lihat "Keputusan default" di bawah)

### 1b. Restrukturisasi monorepo

```
modelgate/
├── packages/{modelgate-core,modelgate-server,github-action}/
├── specs/mgs/
├── conformance/
└── docs/
```

Kode lama **dipindahkan apa adanya** dulu — belum di-refactor. Tujuan langkah ini hanya memindahkan berkas supaya diff di fase berikutnya terbaca.

**Exit criteria**
- `specs/mgs/MGS-1.0.md` ada, memakai MUST/SHOULD/MAY, tiap threshold punya alasan tertulis
- Skema Manifest terdefinisi cukup lengkap sehingga **keempat requirement bisa dievaluasi tanpa menyentuh filesystem**
- Struktur direktori monorepo sudah jadi, `docker compose up` masih jalan seperti sebelumnya

---

## Fase 2 — `modelgate-core`

**Ukuran:** 2–4 minggu · **Fase terberat**

Di sinilah G3, D2.1, D3, D3.1 benar-benar terjadi.

```
Reader ──→ Manifest ──→ Checker ──→ Report
```

- `readers/` — `ZipReader`, `ImageFolderReader`. Satu-satunya tempat yang tahu bentuk dataset.
- `manifest.py` — struktur netral: `samples[]`, `labels[]`, `splits[]`, `uri`, `bytes`, `meta`.
- `checkers/` — port dari 5 analyzer lama, **hanya membaca Manifest**. Tidak ada `os.walk`.
- `report.py` — verdict + skema dari Fase 1.
- Zero dependency infra: tanpa DB, MinIO, RabbitMQ, FastAPI.

**A1 dan A2 mati di sini** — bukan ditambal, tapi karena jalur yang mengandungnya tidak ada lagi. Deteksi struktur jadi satu tempat (Reader), dan MGS-0000 melarang `PASS` untuk yang tidak terevaluasi.

**Exit criteria**
- `python -c "from modelgate import audit; audit('./data')"` menghasilkan report valid
- Nol import `os.walk` di dalam `checkers/`
- Ketiga layout ZIP (single-root, flat-class, split) menghasilkan Manifest yang benar — kasus yang hari ini diam-diam gagal
- Nol dependency infra di `modelgate-core/pyproject.toml`

---

## Fase 3 — Korpus conformance + pembekuan spec · ✅ SELESAI

**Ukuran:** 1–2 minggu (aktual: dikerjakan langsung menyambung Fase 2 dalam sesi yang sama)

Yang mengubah MGS dari dokumen jadi spesifikasi. (D4)

Realisasi (sedikit berbeda dari sketsa awal — bukan dipecah per-`MGS-000X-*/`
folder, tapi flat di `conformance/fixtures/*.zip` + `conformance/expected/*.json`,
karena tiap fixture sudah diberi nama yang menyatakan intent-nya):

```
conformance/
  fixtures/
    generate.py                        ← generator deterministik (noise sintetis,
    adhoc-{single-root,flat-class,split}.zip   bukan flat-color — lihat catatan di generate.py
    structure-{pass,fail-single-class}.zip     soal kenapa flat-color gagal untuk uji pHash)
    edge-empty.zip
    integrity-{pass,fail-corrupted}.zip
    duplicate-{pass,fail-near-identical}.zip
    balance-{pass,fail-imbalanced}.zip
  expected/*.json                      ← 12 file, JSON netral (bukan pytest), di-freeze via --update
  runner.py                            ← kontrak CLI subprocess (spec §7.3), bukan impor Python
```

**Kasus yang hari ini gagal senyap — sudah diverifikasi terbalik:**
- `edge-empty.zip` → `NOT_EVALUATED`/`FAIL` di semua requirement (dulu: `PASS`, skor 0.80, grade A — bug A2)
- `adhoc-flat-class.zip` → `PASS` (dulu: 0 objek ter-upload, tanpa error — bug A1)
- `adhoc-split.zip` → split preserved di URI (`train/cat/0.jpg` dll)
- **Bukti G5 langsung:** `adhoc-single-root.zip` dan `adhoc-flat-class.zip` — dua packaging berbeda, isi logis identik — menghasilkan `dataset_hash` yang **sama persis**.

Runner diverifikasi bisa gagal sungguhan (bukan selalu hijau): expected file sengaja dirusak, `MISMATCH` + exit 1 terdeteksi tepat, lalu dipulihkan.

CI: `.github/workflows/conformance.yml` — job terpisah dari `build.yml`, menjalankan `conformance/runner.py` di tiap push/PR.

**MGS 1.0 dibekukan** — `specs/mgs/MGS-1.0-draft.md` → `specs/mgs/MGS-1.0.md`, status "Draft" → "Final" (§9 spec mencatat kapan & kenapa). Perubahan §5 (Requirements) sekarang jadi MGS 1.1+, bukan edit dokumen ini.

**Exit criteria — semua terpenuhi:**
- ✅ `conformance/runner.py` hijau untuk `modelgate-core` (12/12 fixture)
- ✅ CI (`conformance.yml`) gagal kalau ada beda dari `expected/` — diverifikasi dengan mismatch sengaja
- ✅ `specs/mgs/MGS-1.0.md` — status Draft dicabut

---

## Fase 4 — CLI + rilis PyPI

**Ukuran:** 1 minggu · **Prioritas 1 & 2 dari D7**

```bash
pip install modelgate
modelgate check ./data --spec mgs-1.0
modelgate check ./data --json > report.json
```

Plus: permukaan API publik dikunci (D5.1), `CHANGELOG.md` dimulai (H5), README root bahasa Inggris (H3), pesan error core bahasa Inggris.

**Exit criteria**
- Terpasang dari PyPI di venv bersih, jalan pada dataset asli
- `modelgate check` keluar dengan **exit code non-nol saat FAIL** — syarat mutlak agar berguna di CI
- API publik terdokumentasi dan ditandai stabil; sisanya `_internal`

**Di titik ini proyek sudah berguna bagi orang lain.** Semua sesudahnya adalah perluasan.

---

## Fase 5 — Server jadi konsumen core · ✅ SELESAI

**Ukuran:** 1–2 minggu (aktual: satu sesi kerja lanjutan, diverifikasi via Docker sungguhan — bukan hanya baca kode)

- Hapus seluruh mesin tier (G8): batas upload, pemilihan analyzer, kuota harian, gating PDF, kolom `plan` di `User`, endpoint `/upgrade` — semuanya di `dataset_service`, `audit_service`, `report_service`, `auth_service`
- `analysis_service/analyzers/` dihapus total — `consumer.py` sekarang memanggil `modelgate.audit()` satu kali per job (G4, D2.1)
- Storage (`dataset_service/services/minio_service.py`) ditulis ulang: objek disimpan pakai `Sample.uri` kanonik (sudah termasuk split/label/filename dari Reader), bukan skema `{dataset_id}/{class_name}/{filename}` lama yang membuang info split (G7)
- Docker build context untuk `dataset_service` + `analysis_service` diperluas ke repo root supaya bisa `pip install` `modelgate-core` sebagai sibling package
- `modelgate.read_dataset` naik jadi bagian permukaan API publik (D5.1) — dataset_service butuh validasi struktur tanpa menjalankan full audit
- IDOR di `create_audit()` diperbaiki (B2) — sekaligus ketemu bug turunan: `DatasetReadOnly` (read-only mirror di audit_service) tidak punya kolom `user_id` sama sekali, jadi ownership check baru crash `AttributeError` sampai kolomnya ditambahkan
- Auth opsional, mati default (F9) — toggle `AUTH_REQUIRED` di `/internal/verify`, bukan di `nginx.conf` (nginx tidak punya conditional bersih untuk skip `auth_request`). Ketemu bug saat testing: pseudo-user default sempat berupa string `"local"`, padahal kolom `user_id` di DB bertipe UUID — diganti UUID nil (`00000000-...`)
- `.env` vs `.env.example` (B4), port 8005 (B5), duplikasi blok nginx (E6), env var MinIO yang tidak konsisten (E5) — semua diperbaiki
- **Alembic diaktifkan penuh untuk 4 service** (auth/dataset/audit/analysis — `report_service` dilewati sengaja, ia tidak punya tabel sendiri sama sekali). Baseline di-generate dari skema kosong (bukan dari DB yang sudah ada — koreksi atas kesalahpahaman di draf awal roadmap ini soal cara kerja `--autogenerate`), diverifikasi **dua jalur**: `upgrade head` dari DB kosong, dan `stamp head` pada DB yang disimulasikan seperti hasil `create_all()` lama. Migrasi dijalankan via `docker-entrypoint.sh` di tiap container sebelum `uvicorn` start.

**Exit criteria — semua terpenuhi, diverifikasi lewat stack Docker hidup:**
- ✅ `conformance/runner.py` hijau **untuk server** (`conformance/server_client.py`, kontrak HTTP) — **12/12 fixture identik** dengan `modelgate-core`, termasuk `dataset_hash` yang sama persis. Ini bukti G5, bukan klaim.
- ✅ `git grep -i "free\|pro\|max"` di kode aktif hanya menemukan komentar historis ("tier lama sudah dihapus"), nol logika aktif
- ✅ Nol implementasi checker di luar `modelgate-core`
- ✅ Bukti tambahan di luar exit criteria tertulis: upload `adhoc-split.zip` lewat HTTP asli → MinIO benar-benar menyimpan `train/cat/0.jpg`, `test/cat/1.jpg` dst (G7 hidup, bukan teori)

---

## Fase 6 — Ekosistem inti · ✅ CAKUPAN TERTUTUP SELESAI

**Ukuran:** aktual, satu sesi kerja lanjutan setelah Fase 5

**Koreksi dari draf pertama:** header lama fase ini ("Ekosistem & rilis publik", "berkelanjutan") sempat menggantung tanpa garis finish. Dipersempit jadi cakupan tertutup di bawah — reader tambahan (COCO/YOLO/HF) sengaja **ditunda ke pasca-Fase-7**, bukan bagian gerbang ini (alasan sama seperti sebelumnya: MGS-1.0 dirancang untuk dataset klasifikasi gaya folder, COCO adalah format deteksi objek yang butuh perluasan requirement, bukan cuma Reader baru).

**Selesai:**
- `packages/github-action/action.yml` — composite action, menjalankan `modelgate check --spec --json`, expose `overall-verdict` + `report-json` sebagai output
- `conformance/action_client.py` — mereplay langkah-langkah `action.yml` secara lokal (bukan cuma alias CLI), termasuk format `$GITHUB_OUTPUT` multiline milik GitHub sendiri, diverifikasi lewat eksekusi nyata bukan cuma dibaca. **Diverifikasi 13/13 fixture identik dengan `modelgate-core`.** (Catatan jujur: menjalankan di GitHub Actions runner asli belum terverifikasi dari sandbox ini — tidak ada `act` maupun sesi `gh auth` — baru terbukti setelah push memicu CI sungguhan.)
- CI: `.github/workflows/conformance.yml` sekarang juga menjalankan korpus lewat `action_client.py` sebagai langkah terpisah — bukan cuma CLI langsung
- **Reader ImageFolder dibuktikan formal**, bukan cuma "sudah ada sejak Fase 2": fixture direktori baru `conformance/fixtures/imagefolder-equivalent/` (isi identik dengan `adhoc-flat-class.zip`) menghasilkan `dataset_hash` **sama persis** — G5 terbukti lintas Reader, bukan cuma lintas antarmuka. `runner.py` diperluas mengenali fixture direktori, tidak cuma `.zip`
- `server_client.py` diperluas: zip direktori on-the-fly sebelum upload (endpoint HTTP server memang hanya menerima ZIP — keputusan desain API yang sah, bukan celah) — hasil tetap identik byte-per-byte
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/{bug_report,spec_change}.md`, `.github/PULL_REQUEST_TEMPLATE.md`
- `specs/mgs/SUPPORT-MATRIX.md` — matriks dukungan versi tool↔spec (C7), didokumentasikan sebagai living document yang wajib diupdate tiap rilis, bukan sekali tulis lalu basi

**Bukti akhir — empat antarmuka, satu korpus, hasil identik:**

| Antarmuka | Mekanisme | Hasil |
|---|---|---|
| `modelgate-core` | impor Python langsung | 13/13 OK (baseline) |
| CLI | subprocess `modelgate check` | 13/13 OK |
| Server | HTTP (`server_client.py`) | 13/13 OK, termasuk `dataset_hash` sama persis |
| GitHub Action | replay langkah `action.yml` | 13/13 OK |

**Exit criteria (gerbang Fase 7) — terpenuhi:**
- ✅ GitHub Action lolos korpus conformance yang sama seperti core/CLI/server
- ✅ Reader ImageFolder jalan lewat kontrak yang sama seperti ZIP, dibuktikan bukan diasumsikan
- ✅ `CONTRIBUTING.md` dkk ada
- ✅ Matriks versi terdokumentasi

**Zenodo DOI TIDAK diterbitkan di sini** — tetap ditahan sampai Fase 7d, sesuai keputusan awal.

---

## Keputusan default yang saya ambil

Belum kamu putuskan; saya pilih supaya plan bisa jalan. **Semua bisa dibantah** — tapi kalau tidak dibantah, ini yang dipakai.

| # | Pertanyaan | Default | Alasan |
|---|---|---|---|
| F4 | Nasib Health Score | Dipertahankan sebagai **informative, not normative** | Methods section butuh angka pembanding antar-versi dataset. Verdict jadi headline, angka turun jadi metrik sekunder yang tidak boleh dipakai mengklaim conformance |
| F5 | Format pertama setelah ZIP | **ImageFolder** (direktori polos) | `modelgate check ./data` menyiratkannya. Yang paling banyak dipunya orang secara lokal. COCO/YOLO menyusul |
| F6 | Jumlah requirement MGS-1.0 | **4, bukan 7** — structure, integrity, duplicate, balance | Empat ini bisa dipertahankan di depan reviewer. Resolution (aturan ±1σ) paling lemah justifikasinya → turun jadi informative. Lebih baik 4 kokoh daripada 7 goyah |
| F8 | GitHub org | ✅ **FINAL: "ModelGate Standard"**, slug `modelgate-standard` (terverifikasi tersedia via `api.github.com/orgs/modelgate-standard` → 404) | Nama org resmi yang dipakai di Fase 7a. `modelgate` polos (tanpa hyphen) sudah dipakai org lain — tidak jadi masalah karena bukan yang dipilih |
| F9 | `auth_service` | Dipertahankan, **opsional, mati secara default** | Self-hosted single-user tidak butuh login; multi-user tetap butuh ownership. Membuangnya berarti membuang fitur nyata demi masalah yang sudah hilang |
| F10 | Paket PyPI | ✅ **FINAL: `modelgate-mgs`** (terverifikasi tersedia di PyPI produksi, lihat catatan Fase 4 di bawah) | CLI tetap bernama command `modelgate` (entry point independen dari nama paket PyPI — pola yang sama dipakai `beautifulsoup4` yang command-nya `bs4`) |

**⚠️ Temuan Fase 4 — nama `modelgate` sudah dipakai di PyPI produksi** (ada rilis `0.1.0` aktif, terverifikasi lewat `pypi.org/simple/modelgate/`). Ini **tidak menghalangi Fase 4** — TestPyPI adalah namespace terpisah dari PyPI produksi, dan `modelgate` **tersedia** di sana (terverifikasi, HTTP 404 di `test.pypi.org/simple/modelgate/`). `pyproject.toml` tetap memakai `name = "modelgate"` untuk sisa Fase 4-6 (development), dan **berganti ke `modelgate-mgs` di Fase 7a** saat nama dikunci final untuk rilis PyPI produksi.

**✅ Diputuskan: `modelgate-mgs`** (F10). Di Fase 7a, `pyproject.toml`'s `project.name` diganti dari `modelgate` (dev-only) ke `modelgate-mgs`; `project.scripts` entry point tetap `modelgate` sebagai nama command CLI — independen dari nama paket PyPI (pola yang sama dipakai `beautifulsoup4`, command-nya `bs4`).

---

## Risiko terbesar

**Bukan salah arsitektur — arsitekturnya sudah benar. Risikonya berhenti di tengah.**

Titik paling rawan: akhir Fase 2. Monorepo sudah dipecah, core setengah jadi, server rusak, dan tidak ada satu pun yang bisa dipakai. Kalau kesibukan datang di situ, proyeknya mati dalam keadaan lebih buruk daripada sebelum dimulai.

Mitigasi, berurutan kekuatannya:

1. **Fase 4 adalah titik aman.** Kejar sampai `pip install modelgate` jalan sebelum menyentuh server. Setelah itu proyek punya nilai berdiri sendiri meski tidak dilanjutkan.
2. **Server dibiarkan rusak dengan sengaja** selama Fase 1–4. Jangan pelihara dua jalur sekaligus — itu yang membuat orang kehabisan tenaga.
3. **Empat requirement, bukan tujuh.** Cakupan bisa ditambah kapan saja setelah fondasinya berdiri; fondasi tidak bisa ditambal setelah cakupannya melebar.
