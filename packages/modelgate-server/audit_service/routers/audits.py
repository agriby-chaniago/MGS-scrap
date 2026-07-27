from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db
from models.orm import Audit, DatasetReadOnly
from models.schemas import CreateAuditRequest, AuditSchema
from services.state_machine import transition
from services.publisher import publish_audit_job
from shared.response import success_response

router = APIRouter()

SERVICE_NAME = "audit_service"

# The four MGS-1.0 normative Requirements (specs/mgs/MGS-1.0.md §5) —
# always all of them, for every audit. Fase 5 (G8, BACKLOG.md) removed
# the tier system that used to pick a subset here (free=3 of 5,
# pro/max=all 5): conformance can't be something a paid plan unlocks
# more of (C2, BACKLOG.md) — a Requirement not evaluated must be a real
# NOT_EVALUATED verdict, never quietly skipped by plan.
MGS_REQUIREMENTS = ["MGS-0001", "MGS-0002", "MGS-0003", "MGS-0004"]


def _check_ownership(resource, x_user_id: str | None):
    # 404, not 403 — a user shouldn't be able to tell whether another
    # user's resource even exists.
    if resource.user_id is not None and str(resource.user_id) != x_user_id:
        raise HTTPException(status_code=404, detail="Resource not found")


@router.post("/api/v1/audits", status_code=201)
def create_audit(
    body: CreateAuditRequest,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    # 1. Dataset must exist, not deleted, AND belong to this caller (or be
    # unowned/legacy). This ownership check was missing here — the only
    # one of the three dataset/audit endpoints in this file that lacked
    # it (retry_audit and get_audit both already had it). Its absence let
    # any authenticated user start (and read the resulting metadata of)
    # an audit against another user's dataset by guessing/enumerating its
    # id — an IDOR. See BACKLOG.md B2.
    dataset = db.query(DatasetReadOnly).filter(
        DatasetReadOnly.id == body.dataset_id,
        DatasetReadOnly.status != "deleted",
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or already deleted")
    _check_ownership(dataset, x_user_id)

    # 2. Dedup: return an existing completed audit for this dataset (skip if force=True)
    if not body.force:
        existing = db.query(Audit).filter(
            Audit.dataset_id == body.dataset_id,
            Audit.status == "completed",
        ).order_by(Audit.created_at.desc()).first()
        if existing:
            data = AuditSchema.model_validate(existing).model_dump()
            data["cached"] = True
            return success_response(data=data, service=SERVICE_NAME)

    # 3. Create the audit record — every Requirement, every time (see
    # MGS_REQUIREMENTS above). No per-tier selection and no daily quota
    # here anymore (G8) — the old free-tier quota's only real effect,
    # combined with the IDOR this fix closes, was that it could be
    # bypassed entirely via the dedup path above, since quota was
    # checked after dedup, not before.
    audit = Audit(dataset_id=body.dataset_id, user_id=x_user_id, requested_analyzers=MGS_REQUIREMENTS)
    db.add(audit)

    # 4. Commit first — so audit_id is visible to the consumer before it
    # receives the message.
    db.commit()
    db.refresh(audit)

    # 5. Transition to QUEUED **before** publishing — bugfix: the old order
    # (publish first, then commit "queued") had a real race condition: the
    # consumer could dequeue and read status="pending" (still the ORM
    # default, pre-transition), skip processing, and ack the message —
    # the audit would get permanently stuck (no longer in the queue, and
    # not retryable since its status isn't "failed"). Committing the
    # status before publishing closes this race window.
    transition(audit, "queued", db)
    db.commit()
    db.refresh(audit)

    # 6. Publish to RabbitMQ
    try:
        publish_audit_job({
            "audit_id":            str(audit.id),
            "dataset_id":          str(audit.dataset_id),
            "dataset_minio_path":  dataset.minio_path,
            "requested_analyzers": audit.requested_analyzers,
            "created_at":          audit.created_at.isoformat(),
        })
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to publish job to queue")

    return success_response(
        data=AuditSchema.model_validate(audit).model_dump(),
        service=SERVICE_NAME,
    )


@router.post("/api/v1/audits/{audit_id}/retry", status_code=200)
def retry_audit(
    audit_id: UUID,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    _check_ownership(audit, x_user_id)
    if audit.status != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Only audits with status 'failed' can be retried (current status: {audit.status})",
        )

    dataset = db.query(DatasetReadOnly).filter(
        DatasetReadOnly.id == audit.dataset_id,
        DatasetReadOnly.status != "deleted",
    ).first()
    if not dataset:
        raise HTTPException(status_code=400, detail="Dataset was deleted, cannot retry")

    transition(audit, "queued", db)
    audit.error_message = None
    audit.completed_at = None
    db.commit()
    db.refresh(audit)

    try:
        publish_audit_job({
            "audit_id":            str(audit.id),
            "dataset_id":          str(audit.dataset_id),
            "dataset_minio_path":  dataset.minio_path,
            "requested_analyzers": audit.requested_analyzers,
            "created_at":          audit.created_at.isoformat(),
            "force":               True,
        })
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to publish retry job to queue")

    return success_response(
        data=AuditSchema.model_validate(audit).model_dump(),
        service=SERVICE_NAME,
    )


@router.get("/api/v1/audits/{audit_id}")
def get_audit(
    audit_id: UUID,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    _check_ownership(audit, x_user_id)

    return success_response(
        data=AuditSchema.model_validate(audit).model_dump(),
        service=SERVICE_NAME,
    )
