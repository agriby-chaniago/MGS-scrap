from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from models.database import AuthBase


class User(AuthBase):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth_svc"}

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email         = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    # `plan` column removed in Fase 5 (G8, BACKLOG.md) — the tier system
    # (free/pro/max) is gone. Ownership/auth still exist (F9); paid tiers
    # do not.
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ApiKey(AuthBase):
    __tablename__ = "api_keys"
    __table_args__ = {"schema": "auth_svc"}

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id    = Column(UUID(as_uuid=True), index=True, nullable=False)
    key_hash   = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    revoked    = Column(Boolean, default=False, nullable=False)
