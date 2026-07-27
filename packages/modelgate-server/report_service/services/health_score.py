"""Health score — informative, not normative (BACKLOG.md F4 / C3).

The authoritative signal for a dataset is `overall_verdict` (computed in
aggregator.py from each MGS Requirement's own PASS/FAIL/NOT_EVALUATED
verdict — the same logic as modelgate-core's Report.overall_verdict).
This module produces a secondary 0-1 metric for comparing dataset
versions over time, nothing more — it must never be read as a
conformance claim.

It must also never silently substitute a neutral value for a
NOT_EVALUATED requirement. That was bug A2 (BACKLOG.md, pre-Fase-5): a
zero-image dataset scored 0.80 ("grade A") because every missing metric
defaulted to a neutral 1.0. This function returns None — not a number
that looks real but isn't — whenever any input it needs wasn't actually
evaluated.
"""


def calculate_health_score(requirement_rows: dict[str, dict], informative: dict | None) -> dict | None:
    """
    Score = 0.30*I + 0.25*U + 0.25*D + 0.20*Q

    I = 1 - corruption_rate     (MGS-0002 metrics)
    U = 1 - duplicate_rate      (MGS-0003 metrics)
    D = 1 - gini_coefficient    (MGS-0004 metrics)
    Q = images_in_normal_range  (informative.resolution — not a
                                 Requirement, spec §5.5)

    `requirement_rows`: {analyzer_type -> result_payload} for the 4 MGS
    requirement rows, each result_payload shaped like
    {"verdict": ..., "config": ..., "metrics": ..., "findings": ...}.
    """
    integrity = requirement_rows.get("MGS-0002")
    duplicate = requirement_rows.get("MGS-0003")
    balance = requirement_rows.get("MGS-0004")

    if not all([integrity, duplicate, balance]):
        return None
    if any(r["verdict"] == "NOT_EVALUATED" for r in (integrity, duplicate, balance)):
        return None

    resolution = (informative or {}).get("resolution") or {}
    if not resolution or resolution.get("total", 0) == 0:
        return None

    I = 1.0 - integrity["metrics"]["corruption_rate"]
    U = 1.0 - duplicate["metrics"]["duplicate_rate"]
    D = 1.0 - balance["metrics"]["gini_coefficient"]
    Q = resolution["images_in_normal_range"]

    score = round(0.30 * I + 0.25 * U + 0.25 * D + 0.20 * Q, 4)

    return {
        "score": score,
        "components": {
            "I": round(I, 4),
            "U": round(U, 4),
            "D": round(D, 4),
            "Q": round(Q, 4),
        },
    }
