# ModelGate — check a CV dataset with MGS before you train on it

**Repository:** https://github.com/agriby-chaniago/MGS

`modelgate` is the reference implementation of **MGS** (Model Gate
Specification) — an open spec for evaluating computer vision dataset
quality, designed so independent implementations produce identical,
reproducible verdicts for the same dataset.

**Primary use case:** you're about to train a model. Before you do, check
the dataset — in the same notebook or script, no server, no upload, no
infrastructure.

```python
from modelgate import audit

report = audit("./my_dataset")  # a ZIP, or a plain folder-per-class directory

if report.overall_verdict != "PASS":
    raise RuntimeError(f"Dataset failed MGS: {report.overall_verdict}")

# proceed to training
```

See [`packages/modelgate-core/examples/quickstart.ipynb`](packages/modelgate-core/examples/quickstart.ipynb)
for a runnable version of this, end to end, generating its own tiny
example dataset so it works standalone.

---

## Install

```bash
cd packages/modelgate-core
pip install -e .
```

(Will become `pip install modelgate-mgs` once released — see
`ROADMAP.md` Fase 7. Not yet published to production PyPI.)

CLI, same thing without Python:

```bash
modelgate check ./my_dataset --spec mgs-1.0 --json > report.json
```

Exits non-zero on anything but a clean `PASS` — usable directly as a
CI gate, not just interactively.

---

## What it actually checks (MGS 1.0)

| Requirement | What it evaluates |
|---|---|
| `MGS-0001` Structure | At least 2 classes, each with at least one valid sample |
| `MGS-0002` Integrity | No corrupted/unreadable image files |
| `MGS-0003` Duplicate | Near-duplicate images (perceptual hash), under 3% |
| `MGS-0004` Balance | Class imbalance (Gini coefficient), under 0.4 |

Each gets one of four verdicts: `PASS`, `FAIL`, `NOT_EVALUATED`, or
`PARTIAL`. A dataset that can't actually be evaluated (empty, unreadable)
reports `NOT_EVALUATED` — never a silent `PASS`. That's MGS-0000, the
spec's fail-closed rule, and it exists because the pre-MGS version of
this project had exactly that bug: an empty dataset used to score 0.80
("grade A"). See `specs/mgs/MGS-1.0.md` for the full spec, and
`BACKLOG.md`/`ROADMAP.md` for how that bug (and others) were found and
fixed.

A secondary "health score" (0–1) is also reported, for comparing dataset
versions over time — it's informative only, never a substitute for the
verdict above.

---

## How it works internally

```
Dataset → Reader → Manifest → Checker (×4) → Report
```

A **Reader** is the only part that knows about raw file formats (ZIP,
plain directory). It normalizes everything into a **Manifest** —
`{samples[], labels[], splits[]}` — that every **Checker** reads, never
touching the filesystem directly. This split is what lets `modelgate`
guarantee **the exact same Manifest produces the exact same verdict**,
regardless of whether the dataset arrived as a ZIP or an already-
extracted folder — proven in `conformance/`, not just claimed (a ZIP and
an equivalent directory fixture hash identically; see
`conformance/fixtures/imagefolder-equivalent/`).

## Conformance — the proof, not just the claim

```bash
python3 conformance/runner.py
```

Runs a corpus of small synthetic datasets through `modelgate` and checks
the output against frozen `conformance/expected/*.json` byte-for-byte.
This is what makes MGS a specification rather than a description of one
implementation's behavior — any change to `modelgate-core` has to still
reproduce every one of these exactly, or CI fails
(`.github/workflows/conformance.yml`).

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) — the short version: all audit
logic lives in `packages/modelgate-core`, nowhere else, and any change
has to keep the conformance corpus green.

---

## Archived components

This project also has a hosted web-app version — a microservice stack,
a React UI, and a Streamlit UI, all built during this project's original
coursework phase, plus a GitHub Action for CI use. **All of that is
archived, not actively maintained** — the project's focus is the library
above. Each has its own README explaining status and what it would take
to revive it:

- [`packages/modelgate-server/README.md`](packages/modelgate-server/README.md)
- [`packages/modelgate-web/README.md`](packages/modelgate-web/README.md)
- [`packages/modelgate-streamlit/README.md`](packages/modelgate-streamlit/README.md)
- [`packages/github-action/README.md`](packages/github-action/README.md)

None of it is a dependency of `modelgate-core` — the library works
standalone.

---

## Directory structure

```
MGS/
├── packages/
│   ├── modelgate-core/       THE library. pip install this. Zero infra deps.
│   │   └── examples/          quickstart.ipynb — the primary documented use case
│   ├── modelgate-server/      archived — hosted microservice stack
│   ├── modelgate-web/         archived — React UI
│   ├── modelgate-streamlit/   archived — Streamlit UI
│   └── github-action/         archived — CI wrapper
├── specs/
│   ├── mgs/                  MGS specification (MGS-1.0.md — frozen)
│   └── LICENSE                CC-BY-4.0, for the spec only
├── conformance/                Fixtures + runner proving conformance
├── docs/
│   └── uas-archive/            Original coursework PRD, slides, video script
├── .github/workflows/
│   ├── conformance.yml         Active — gates modelgate-core + the quickstart notebook
│   └── build.yml               Manual-only — builds archived component images
├── LICENSE                     Apache-2.0, for the code
├── ARCHITECTURE.md             Design decisions (some describe the archived server)
├── BACKLOG.md                  Findings + architecture decisions (section G)
└── ROADMAP.md                  Restructuring plan and its history
```

---

## Background

This project began as a coursework submission for **Web Service** and
**Platform-Based Programming** (Informatics, semester 6) at a
university — the microservice stack in `packages/modelgate-server/` was
the original deliverable. It was then restructured into a spec
(MGS) + reference implementation (this library), and finally refocused
to be library-first: the notebook/pre-training workflow at the top of
this README, not a hosted product.

See `ROADMAP.md` for the full history of that restructuring, and
`BACKLOG.md` for the specific bugs found and architectural decisions
made along the way.
