# ModelGate — CV Dataset Quality Audit

**Repository:** https://github.com/agriby-chaniago/MGS

A Computer Vision dataset quality audit platform. Originally built as a
microservice-based web app; being restructured into **MGS** (Model Gate
Specification — an open spec for CV dataset quality) plus **ModelGate**
(its reference implementation), library/CLI-first.

> **Under active restructuring.** See [`ROADMAP.md`](ROADMAP.md) and
> [`BACKLOG.md`](BACKLOG.md) for the direction and current status, and
> [`specs/mgs/MGS-1.0.md`](specs/mgs/MGS-1.0.md) for the frozen spec.
> Fase 0–3 are done: the monorepo layout exists, `modelgate-core` (the
> Reader → Manifest → Checker → Report pipeline) is real and passes its
> own conformance corpus, and MGS 1.0 is frozen. The tier system and
> microservice details described further down this README still reflect
> the **pre-restructuring** server — that part isn't touched until Fase
> 5. This README will be split/simplified once Fase 7 (public release)
> lands.
>
> This project started as a coursework submission for **Web Service**
> and **Platform-Based Programming** (Informatics, semester 6) at a
> university. The original presentation materials (PRD, slides, video
> script) are preserved, unchanged, at
> [`docs/uas-archive/`](docs/uas-archive/).

---

## Quick start — library/CLI (the new, primary way)

This is what Fase 0–4 of the restructuring actually built. No Docker,
no server, just a Python package:

```bash
cd packages/modelgate-core
pip install -e .          # will be `pip install modelgate` once released — see ROADMAP.md Fase 7

modelgate check ./my_dataset.zip --spec mgs-1.0
modelgate check ./my_dataset.zip --json > report.json
```

Supports a ZIP archive or a plain directory (ImageFolder layout), in any
of the class-folder arrangements MGS's Reader recognizes (single root
folder, flat class folders, or `train/`/`test/`/etc. splits — see
`specs/mgs/MGS-1.0.md` §2). Exits non-zero on anything but a clean
`PASS`, so it's usable directly as a CI gate.

From Python:

```python
from modelgate import audit

report = audit("./my_dataset.zip")
print(report.overall_verdict)          # PASS / FAIL / NOT_EVALUATED
for r in report.requirements:
    print(r.id, r.verdict, r.metrics)
```

See [`packages/modelgate-core/README.md`](packages/modelgate-core/README.md)
for the stable API surface, and `conformance/` for the fixture corpus
that proves this pipeline's output is reproducible, not just claimed to
be.

Everything below this point describes the **hosted server stack**
(`packages/modelgate-server/` — FastAPI microservices, Postgres, MinIO,
RabbitMQ, React/Streamlit UIs), which is a separate, optional way to run
audits through a browser. It still has the pre-restructuring tier system
(Free/Pro/Max) described below; that's removed in Fase 5.

---

## Key Features

**Core (dataset audit):**
- Upload a dataset ZIP, automatic structure validation, SHA-256 dedup
- 5 analyzers: corruption, empty, resolution, distribution, duplicate (pHash)
- Health Score with A–F grade, PDF report
- Real-time audit progress (WebSocket)

**Added for the original coursework submission:**
- JWT auth with 3 paid tiers (Free / Pro / Max), each with different upload limits, analyzer count, daily quota, and PDF access
- API key + CLI (`mgs`) for programmatic access outside the browser
- New React + Vite + Tailwind frontend (parallel to the older Streamlit UI, both still work)
- Rate limiting at the API gateway (Nginx)
- Observability — Prometheus + Grafana (ready-made dashboard)
- Horizontal scaling for the image-analysis service
- CI/CD — GitHub Actions build & push images to GHCR

---

## Architecture (server stack)

```
Browser ──┬─→ React (3000)
          └─→ Streamlit (8501)
                    ↓
              Nginx (8080)  ← API Gateway + auth_request + rate limit
       /    |     |     |      \
   dataset audit analysis report auth
   (8001) (8002)  (8003) (8004) (8005)
       \     |      |      |     /
        PostgreSQL  MinIO  RabbitMQ
                              │
                     analysis_service (consumer, scalable)

CLI (mgs) ──→ Nginx (8080), via API Key

Prometheus (9090) ──scrape──→ all services + RabbitMQ
Grafana (3001) ──query──→ Prometheus
```

| Service | Port | Function |
|---|---|---|
| React frontend | 3000 | Newer UI (Tailwind, WebSocket live progress) |
| Streamlit | 8501 | Older UI (still functional) |
| Nginx | 8080 | API Gateway — auth, rate limit, routing |
| dataset_service | 8001 | Dataset upload & management |
| audit_service | 8002 | Audit orchestration, WebSocket broadcast |
| analysis_service | 8003 | Image analysis (5 analyzers), RabbitMQ consumer |
| report_service | 8004 | Reports, Health Score, PDF |
| auth_service | 8005 | JWT, API key, tiers — **added for coursework, removed in Fase 5** |
| PostgreSQL | 5432 | Main database (1 DB, separate schema per service) |
| MinIO | 9000/9001 | Object storage (images) |
| RabbitMQ | 5672/15672/15692 | Message queue + metrics plugin |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3001 | Observability dashboard |
| pgAdmin | 5050 | Database admin UI |

Architecture principle: **bounded context** — each service only writes to
its own database schema; cross-service reads use a *read-only mirror*
model. Nginx only handles **authentication** (who you are); **authorization**
(what you're allowed to do) stays each service's own responsibility. Full
detail in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Plans / Tiers (server stack — removed in Fase 5, see BACKLOG.md G8)

| Tier | Max Upload | Analyzers | Daily Audit Quota | PDF Download |
|---|---|---|---|---|
| **Free** | 150MB | 3 of 5 | 3 | ✗ |
| **Pro** | 1024MB | 5 | 20 | ✓ |
| **Max** | 2048MB | 5 | Unlimited | ✓ |

All new accounts default to **Free**. Upgrading is self-service via a
button in the app sidebar (no real payment — demo/coursework scope only)
or via the `POST /api/v1/auth/upgrade` API.

---

## Screenshots

| | |
|---|---|
| **Login** | **Register** |
| ![Login](docs/screenshots/01-login.png) | ![Register](docs/screenshots/02-register.png) |
| **Upload dataset (Free tier)** | **Start audit** |
| ![Upload](docs/screenshots/03-wizard-upload-free.png) | ![Audit start](docs/screenshots/04-audit-start.png) |
| **Real-time audit progress (WebSocket)** | **Report — Free tier** |
| ![Audit progress](docs/screenshots/05-audit-progress.png) | ![Report free](docs/screenshots/06-report-free.png) |

Note in the Free-tier report: the **Uniqueness** and **Distribution**
components are clearly marked **"Not audited"** (dashed, not a number)
because the `duplicate` and `distribution` analyzers don't run on the
Free plan — not silently treated as a perfect score of 1.00. This fixed a
Health Score transparency bug found during testing.

| | |
|---|---|
| **Upgrade to Max** | **Generate an API key for the CLI** |
| ![Upgraded](docs/screenshots/07-upgraded-max.png) | ![API key panel](docs/screenshots/08-apikey-panel.png) |
| **Report — Max tier (all analyzers + PDF)** | **Delete dataset confirmation** |
| ![Report max](docs/screenshots/09-report-max-pdf.png) | ![Delete confirm](docs/screenshots/10-delete-confirm.png) |
| **Grafana — observability dashboard** | **Prometheus — target status** |
| ![Grafana](docs/screenshots/11-grafana.png) | ![Prometheus](docs/screenshots/12-prometheus.png) |

---

## Requirements (server stack)

- Docker & Docker Compose
- 4GB RAM minimum (large datasets need more)
- Python 3.11+ and Node.js 20+ if developing outside Docker
- Ports 3000, 3001, 5050, 8080, 8501, 9000, 9001, 9090, 15672 free

---

## Running the server stack

### 1. Clone & configure

> Since the Fase 1 monorepo restructuring, the whole server stack lives
> in `packages/modelgate-server/` — run the commands below from there,
> not from the repo root.

```bash
git clone <repo-url>
cd MGS/packages/modelgate-server
cp .env.example .env
```

`.env` holds default dev credentials, including `JWT_SECRET`. **Don't
commit `.env`** (already gitignored).

### 2. Start every service

```bash
docker compose up -d --build
docker compose restart nginx   # REQUIRED after every --build, see note below
```

Wait for every container to report healthy (~1-2 minutes, especially
Postgres and RabbitMQ). Check status:

```bash
docker compose ps
```

> **Important — a common gotcha:** Nginx uses the stock image
> (`nginx:alpine`), not a custom build. If any other service gets
> rebuilt with `--build`, that container gets a new IP, but Nginx
> doesn't automatically know — **always run `docker compose restart
> nginx` after rebuilding any service**, or requests will fail with 502.

### 3. Access the app

| URL | Purpose |
|---|---|
| http://localhost:3000 | React frontend (newer) |
| http://localhost:8501 | Streamlit frontend (older, still works) |
| http://localhost:8080 | API Gateway (Nginx) |
| http://localhost:8080/docs/ | API documentation (RapiDoc) |
| http://localhost:3001 | Grafana (`admin` / `admin`) |
| http://localhost:9090 | Prometheus |
| http://localhost:9001 | MinIO Console (`minioadmin` / `minioadmin123`) |
| http://localhost:15672 | RabbitMQ Management (`guest` / `guest`) |
| http://localhost:5050 | pgAdmin |

---

## Usage flow (server stack)

### Via browser (React or Streamlit)

```
1. Register / Log in
   └── New accounts default to the Free plan

2. (Optional) Upgrade plan
   └── "Upgrade to Pro/Max" button in the sidebar — self-service, no payment

3. Upload a dataset ZIP
   └── Format: ZIP containing one subfolder per class
       Example: dataset.zip/cats/, dataset.zip/dogs/
       Size limit depends on plan (see Plans table)

4. Run an audit
   └── Which analyzers run is decided automatically by plan:
       - Corruption   : detects broken image files
       - Empty        : detects empty/near-empty class folders
       - Resolution   : analyzes resolution distribution
       - Distribution : class balance (Gini coefficient)
       - Duplicate    : near-duplicate detection (pHash)
   └── Progress shown live via WebSocket

5. View the report
   └── Health Score (0-1) with an A/B/C/D/F grade
       Components: Integrity (30%), Uniqueness (25%),
                   Distribution (25%), Quality (20%)
       PDF download (Pro/Max only)
```

### Via CLI (`mgs`) — programmatic access to the server

For Pro/Max plans, no browser required at all.

> **Note:** this is the *old* CLI, which talks to `packages/modelgate-server`
> over HTTP (API key, JWT). It's distinct from the new
> `modelgate check ./data` CLI built on `modelgate-core` (see the Quick
> Start section above) — that one needs no server at all. Paths below
> already reflect its new location at `packages/modelgate-server/cli/`.

```bash
# 1. Generate an API key from the browser — "API Key" panel in the sidebar (Pro/Max only)

# 2. Install the CLI's dependencies (once)
pip install -r packages/modelgate-server/cli/requirements.txt

# 3. Save the API key (validated immediately)
python3 packages/modelgate-server/cli/mgs.py configure --key mg_live_xxxxxxxx --base-url http://localhost:8080

# 4. Run a full audit end-to-end in one command
python3 packages/modelgate-server/cli/mgs.py run dataset.zip --pdf
```

Other available commands: `mgs upload`, `mgs audit <dataset_id>`, `mgs
status <audit_id>`, `mgs report <audit_id> --pdf`. Run `mgs --help` for
the full guide.

Tip: add an alias so you don't have to type the full path every time:
```bash
echo 'alias mgs="python3 '"$(pwd)"'/packages/modelgate-server/cli/mgs.py"' >> ~/.zshrc   # or ~/.bashrc
```

---

## API Documentation (server stack)

Interactive docs are available via **RapiDoc** — open
`http://localhost:8080/docs/` while the stack is running, or open
`docs/index.html` directly in a browser (no Docker needed).

### Refresh specs (optional)

After changing any endpoint, regenerate the specs from the running services:

```bash
bash docs/generate_specs.sh
```

Then commit `docs/openapi/*.json`.

---

## API Endpoints (server stack)

### Auth Service — *added for coursework, removed in Fase 5*
```
POST   /api/v1/auth/register        Register a new account (defaults to Free)
POST   /api/v1/auth/login           Log in, get a JWT
GET    /api/v1/auth/me              Info about the logged-in account
POST   /api/v1/auth/upgrade         Upgrade plan (self-service, demo-only)
POST   /api/v1/auth/api-keys        Generate an API key (Pro/Max only)
```

### Dataset Service
```
POST   /api/v1/datasets/upload      Upload a dataset ZIP (limit depends on plan)
GET    /api/v1/datasets             List your own datasets
GET    /api/v1/datasets/{id}        Dataset detail + classes
DELETE /api/v1/datasets/{id}        Soft-delete a dataset
```

### Audit Service
```
POST   /api/v1/audits               Create a new audit (analyzers decided server-side by plan)
GET    /api/v1/audits/{id}          Audit status
POST   /api/v1/audits/{id}/retry    Retry a failed audit
WS     /ws/audits/{id}              Live per-analyzer progress — added for coursework
```

### Report Service
```
GET    /api/v1/reports/{audit_id}          Per-analyzer results + findings
GET    /api/v1/reports/{audit_id}/summary  Health score & components
GET    /api/v1/reports/{audit_id}/pdf      PDF download (Pro/Max only)
```

Every endpoint above (except `/api/v1/auth/register` and
`/api/v1/auth/login`) requires `Authorization: Bearer <jwt>` or
`X-API-Key: <key>`.

---

## Observability (server stack)

- **Prometheus** (`localhost:9090/targets`) — scrapes metrics from all 5
  backend services + the RabbitMQ metrics plugin, automatically via
  `prometheus-fastapi-instrumentator`, no extra code per endpoint.
- **Grafana** (`localhost:3001`, login `admin`/`admin`) — the
  **"ModelGate Overview"** dashboard is auto-provisioned on startup
  (request rate & latency per service, RabbitMQ queue depth, consumer
  count, up/down status for every service). The Prometheus datasource
  is also connected automatically, no manual setup needed.

---

## Horizontal Scaling (server stack)

`analysis_service` connects to RabbitMQ as a consumer — running more
than one instance automatically distributes load with no extra
load-balancing code (run from `packages/modelgate-server/`):

```bash
docker compose up -d --scale analysis_service=3
sleep 5   # give replicas time to connect to RabbitMQ
docker compose exec rabbitmq rabbitmqctl list_consumers   # should show 3 consumers on the audit.jobs queue

# scale back down to 1 replica when done
docker compose up -d --scale analysis_service=1
```

---

## CI/CD

- `.github/workflows/build.yml` — builds and pushes a Docker image for
  each service to **GitHub Container Registry (GHCR)** on every push to
  `main`.
- `.github/workflows/conformance.yml` — runs `conformance/runner.py`
  against `modelgate-core` on every push/PR. This is the gate that makes
  MGS a specification rather than a claim (see `ROADMAP.md` Fase 3):
  any change to the Reader/Checker/Report pipeline has to still
  reproduce every frozen `conformance/expected/*.json` exactly, or CI fails.

---

## Development (server stack)

> Every `docker compose` command in this section is run from
> `packages/modelgate-server/`.

### Rebuild a single service

```bash
docker compose up -d --build <service_name>
docker compose restart nginx   # REQUIRED after any rebuild
```

### View logs

```bash
docker compose logs -f <service_name>
# Example:
docker compose logs -f analysis_service
docker compose logs -f audit_service
```

### Stop everything

```bash
docker compose down          # Stop, keep data
docker compose down -v       # Stop + delete all data (full reset)
```

### Directory structure

Restructured into a monorepo in Fase 1 (see [`ROADMAP.md`](ROADMAP.md)) —
`modelgate-core` is the center of it (G3 in [`BACKLOG.md`](BACKLOG.md)),
everything else is a consumer of it:

```
MGS/
├── packages/
│   ├── modelgate-core/          MGS reference implementation — pure Python,
│   │                            zero infra dependencies. Reader → Manifest →
│   │                            Checker → Report. Real and conformance-tested
│   │                            as of Fase 3 (ROADMAP.md) — not just a
│   │                            packaging skeleton anymore.
│   ├── modelgate-server/        Microservice stack (hosted deployment)
│   │   ├── dataset_service/     FastAPI — upload & dataset management
│   │   ├── audit_service/       FastAPI — audit orchestration + WebSocket + RabbitMQ publisher
│   │   ├── analysis_service/    FastAPI — 5 analyzers (will call modelgate-core in Fase 5) + RabbitMQ consumer (scalable)
│   │   ├── report_service/      FastAPI — health score + PDF generation
│   │   ├── auth_service/        FastAPI — JWT, API key, tiers (removed in Fase 5, see G8)
│   │   ├── cli/                 mgs.py — old CLI, talks to the server over HTTP
│   │   ├── shared/              Shared code (response envelope, etc.) — server-only, not core
│   │   ├── nginx/                nginx.conf (API gateway: auth_request, rate limit, CORS)
│   │   ├── rabbitmq/             Custom Dockerfile (Prometheus plugin)
│   │   ├── observability/        Prometheus + Grafana provisioning config
│   │   ├── docker-compose.yml    Run from here, not from repo root
│   │   └── .env.example          Config template (copy to .env)
│   ├── modelgate-web/            React + Vite + Tailwind — main UI
│   ├── modelgate-streamlit/      Older UI — archived, not actively maintained
│   └── github-action/            GitHub Action — built in Fase 6
├── specs/
│   ├── mgs/                     MGS specification (MGS-1.0.md — frozen)
│   └── LICENSE                  CC-BY-4.0, for the spec only
├── conformance/                  Conformance corpus + CI gate (Fase 3)
├── docs/
│   ├── uas-archive/              Original coursework PRD, slides, video script — archived
│   ├── index.html                 API docs (RapiDoc)
│   ├── rapidoc-min.js             Bundled RapiDoc (offline)
│   ├── generate_specs.sh          Refresh OpenAPI specs from running services
│   └── openapi/                  OpenAPI 3.0 JSON per service
├── .github/workflows/            CI/CD — image builds + the conformance gate
├── LICENSE                       Apache-2.0, for the code
├── ARCHITECTURE.md               Architecture detail & design decisions
├── BACKLOG.md                    Findings + architecture decisions (section G)
└── ROADMAP.md                    Fase 0-7 restructuring plan
```

---

## Course Mapping

This section documents which features of the original coursework
submission map to which course concepts — kept for historical record.

### Web Service
- **REST API + API Gateway** — Nginx as a single entry point for every service
- **Two auth schemes** — JWT (browser users) and API key (programmatic access via CLI/scripts)
- **Real-time communication** — WebSocket for audit progress, replacing polling
- **Rate limiting** — IP-based request limits at the API gateway

### Platform-Based Programming
- **Containerization** — the whole stack runs on Docker & Docker Compose
- **Async message queue** — RabbitMQ for heavy image-analysis work
- **Observability** — Prometheus (metrics) + Grafana (visualization)
- **Horizontal scaling** — multiple consumer instances, load distributed automatically by RabbitMQ
- **CI/CD** — automated image build & publish via GitHub Actions

Kubernetes was deliberately left out of the coursework's scope — a
trade-off between setup complexity and the time available to properly
implement and test other features.
