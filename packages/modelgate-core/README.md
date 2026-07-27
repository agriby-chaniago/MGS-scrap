# modelgate-core

Reference implementation of [MGS (Model Gate Specification)](../../specs/mgs/MGS-1.0.md) — pure-Python, zero infrastructure dependencies.

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

## Usage

```python
from modelgate import audit

report = audit("./my_dataset.zip")
print(report.overall_verdict)  # PASS / FAIL / NOT_EVALUATED
for r in report.requirements:
    print(r.id, r.verdict, r.metrics)
```

```bash
modelgate check ./my_dataset.zip --spec mgs-1.0 --json > report.json
```

## Stable API surface (D5.1)

Only what's listed in `modelgate.__all__` is covered by any stability
guarantee (once tagged `1.0`, per `ROADMAP.md` Fase 4):

- `modelgate.audit(path, config=None) -> Report`
- `modelgate.Report`, `modelgate.RequirementResult`, `modelgate.Manifest`

Anything under `modelgate._readers`, `modelgate._checkers`,
`modelgate._rounding` — the leading underscore is enforced, not just
documented — may change shape between minor versions without notice.
The `modelgate check` CLI's `--json` output shape (spec §4) is the other
thing meant to be stable; parse that, not Python internals, if you're
integrating from outside Python.
