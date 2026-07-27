from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.database import AuditBase, ReadOnlyBase


class Audit(AuditBase):
    __tablename__ = "audits"
    __table_args__ = {"schema": "audit_svc"}

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id          = Column(UUID(as_uuid=True), nullable=False)
    user_id             = Column(UUID(as_uuid=True), nullable=True, index=True)
    status              = Column(String(50), default="pending")
    # Default kept in sync with audits.py's MGS_REQUIREMENTS (Fase 5,
    # G8, BACKLOG.md) — this default is never actually used since
    # create_audit() always passes requested_analyzers explicitly, but a
    # stale list here (still naming the 5 old tier-era analyzers) would
    # be actively misleading to read.
    requested_analyzers = Column(JSONB, default=lambda: [
                              "MGS-0001", "MGS-0002", "MGS-0003", "MGS-0004",
                          ])
    created_at          = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at        = Column(DateTime, nullable=True)
    error_message       = Column(String, nullable=True)


class DatasetReadOnly(ReadOnlyBase):
    __tablename__ = "datasets"
    __table_args__ = {"schema": "dataset_svc"}

    id         = Column(UUID(as_uuid=True), primary_key=True)
    minio_path = Column(String)
    status     = Column(String)
    # Added in Fase 5 (found by actually running create_audit() end to
    # end, not just reading the code) — the IDOR fix in audits.py's
    # create_audit() calls _check_ownership(dataset, ...), which reads
    # dataset.user_id. Without this column declared here, that raised
    # AttributeError on every single audit creation. This is a read-only
    # mirror (ReadOnlyBase, not part of create_all()/migrations) of a
    # column dataset_service's own baseline migration already has.
    user_id    = Column(UUID(as_uuid=True), nullable=True)


class AnalysisResultReadOnly(ReadOnlyBase):
    __tablename__ = "analysis_results"
    __table_args__ = {"schema": "analysis_svc"}

    id            = Column(UUID(as_uuid=True), primary_key=True)
    audit_id      = Column(UUID(as_uuid=True), index=True)
    analyzer_type = Column(String(50))
    status        = Column(String(50))
