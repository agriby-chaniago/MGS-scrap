# modelgate-core

Reference implementation of [MGS (Model Gate Specification)](../../specs/mgs/MGS-1.0-draft.md) — pure-Python, zero infrastructure dependencies.

**Status:** Fase 1 packaging skeleton. The actual Reader → Manifest →
Checker → Report pipeline is built in Fase 2 — see
[`ROADMAP.md`](../../ROADMAP.md) at the repo root.

```bash
pip install -e .
```

No FastAPI, no database, no message queue — this package is meant to be
usable from a plain Python script, a notebook, or a CI job with nothing
but `pip install modelgate`. The hosted server
(`packages/modelgate-server`) is a consumer of this package, not the
other way around.
