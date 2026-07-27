from uuid import UUID
from sqlalchemy.orm import Session
from models.orm import Audit, AnalysisResult
from services.health_score import calculate_health_score

# Matches analysis_service/consumer.py's INFORMATIVE_ANALYZER_TYPE — these
# two services communicate only via the DB row shape and RabbitMQ
# messages (separate containers, can't share a Python import), so this
# string is duplicated by convention, the same way the "MGS-000X" ids
# already are.
INFORMATIVE_ANALYZER_TYPE = "informative"


def _overall_verdict(requirement_rows: dict[str, dict]) -> str | None:
    """Same precedence as modelgate-core's Report.overall_verdict (spec §3):
    FAIL beats NOT_EVALUATED/PARTIAL beats PASS. None if there's nothing
    to compute from at all (e.g. the audit's execution itself failed, so
    no requirement was genuinely evaluated — see consumer.py's
    catastrophic-failure fallback, which stores rows with no verdict)."""
    verdicts = {r["verdict"] for r in requirement_rows.values() if r.get("verdict")}
    if not verdicts:
        return None
    if "FAIL" in verdicts:
        return "FAIL"
    if "NOT_EVALUATED" in verdicts or "PARTIAL" in verdicts:
        return "NOT_EVALUATED"
    return "PASS"


def get_report_data(audit_id: UUID, db: Session) -> dict | None:
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        return None

    results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.audit_id == audit_id)
        .order_by(AnalysisResult.completed_at)
        .all()
    )

    # Fase 5 (G4/D2.1, BACKLOG.md): analyzer_type is now an MGS requirement
    # id ("MGS-0001".."MGS-0004") or the special "informative" row — not
    # one of the 5 old analyzer names. requirement_rows only holds rows
    # that actually carry a result_payload (a catastrophic execution
    # failure stores rows with result_payload=None, which correctly
    # excludes them from verdict/health-score computation below, rather
    # than crashing on a missing "verdict" key).
    requirement_rows: dict[str, dict] = {}
    informative: dict | None = None
    dataset_hash: str | None = None
    spec_version: str | None = None
    requirements_list = []
    for r in results:
        if r.analyzer_type == INFORMATIVE_ANALYZER_TYPE:
            # dataset_hash/spec_version ride along on this row (see
            # consumer.py) rather than needing their own column — pulled
            # out here so `informative` in the returned dict matches
            # modelgate-core's own Report.informative shape exactly
            # (just {"resolution": {...}}), for byte-for-byte comparison
            # in the conformance corpus (spec §7, G5).
            payload = dict(r.result_payload or {})
            dataset_hash = payload.pop("dataset_hash", None)
            spec_version = payload.pop("spec_version", None)
            informative = payload
            continue
        if r.result_payload is not None:
            requirement_rows[r.analyzer_type] = r.result_payload
            requirements_list.append({"id": r.analyzer_type, **r.result_payload})
        else:
            requirements_list.append({
                "id": r.analyzer_type,
                "verdict": None,
                "error": r.error_message,
            })

    overall_verdict = _overall_verdict(requirement_rows) if audit.status == "completed" else None
    health = calculate_health_score(requirement_rows, informative) if requirement_rows else None

    return {
        "audit_id": str(audit.id),
        "dataset_id": str(audit.dataset_id),
        "user_id": str(audit.user_id) if audit.user_id else None,
        "audit_status": audit.status,
        "spec_version": spec_version,
        "dataset_hash": dataset_hash,
        "overall_verdict": overall_verdict,
        # health_score is informative, not normative (F4/C3, BACKLOG.md) —
        # a secondary metric for comparing dataset versions, never a
        # substitute for overall_verdict. None (not a neutral-default
        # number) whenever any input wasn't actually evaluated — see
        # health_score.py's docstring for why this matters (bug A2).
        "health_score": health["score"] if health else None,
        "health_score_components": health["components"] if health else None,
        "requirements": requirements_list,
        "informative": informative,
        "requested_analyzers": audit.requested_analyzers,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
    }
