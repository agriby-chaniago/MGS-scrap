import os
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session

from models.database import get_db
from models.orm import ApiKey, User
from services.security import decode_access_token, hash_api_key

router = APIRouter(prefix="/internal")

# F9 (BACKLOG.md, ROADMAP.md Fase 5): auth is optional, off by default.
# A self-hosted single-user deployment shouldn't need to register/log in
# just to run local audits; a multi-user deployment still needs real
# ownership enforcement. The toggle lives here — not in nginx.conf, which
# has no clean way to conditionally skip a whole auth_request directive —
# so /internal/verify is still always called by every gated location, but
# short-circuits to a fixed pseudo-user when auth isn't required.
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "false").lower() == "true"
# Nil UUID, not a human-readable string like "local" — every service's
# `user_id` column is typed UUID (dataset_svc.datasets.user_id,
# audit_svc.audits.user_id), so a non-UUID string here would fail with a
# Postgres InvalidTextRepresentation error the very first time any
# ownership-filtered query ran (found by actually running this end to
# end, not just reading the code — every gated list/get endpoint filters
# by user_id).
LOCAL_USER_ID = "00000000-0000-0000-0000-000000000000"


def _token_from_original_uri(x_original_uri: str | None) -> str | None:
    # Nginx's auth_request module runs this endpoint as a subrequest whose
    # own URI has no query string — the WebSocket handshake's ?token=...
    # (browsers can't set custom headers on a WS upgrade) only survives via
    # X-Original-URI, which nginx.conf sets to $request_uri (always the
    # ORIGINAL client request, unlike subrequest args).
    if not x_original_uri:
        return None
    query = urlparse(x_original_uri).query
    values = parse_qs(query).get("token")
    return values[0] if values else None


def _verify_jwt(token: str, db: Session) -> str | None:
    payload = decode_access_token(token)
    if not payload:
        return None
    return payload["sub"]


def _verify_api_key(raw_key: str, db: Session) -> str | None:
    key_hash = hash_api_key(raw_key)
    api_key = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash, ApiKey.revoked.is_(False)
    ).first()
    if not api_key:
        return None
    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user:
        return None
    return str(user.id)


@router.get("/verify")
def verify(
    response: Response,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_original_uri: str | None = Header(default=None, alias="X-Original-URI"),
    token: str | None = None,
    db: Session = Depends(get_db),
):
    if not AUTH_REQUIRED:
        # Single-user self-hosted mode: every request is attributed to
        # the same fixed pseudo-user, no credentials checked at all.
        # Every dataset/audit ends up owned by "local", so the existing
        # ownership checks in each service still work unchanged — they
        # just always compare against the same id.
        response.headers["X-User-Id"] = LOCAL_USER_ID
        return {"user_id": LOCAL_USER_ID}

    # Checked in priority order: Bearer JWT header, X-API-Key header, then
    # a ?token= query param — either passed directly (curl/testing) or via
    # X-Original-URI (real Nginx auth_request subrequests for /ws/, since
    # browsers cannot set custom headers on a WebSocket handshake).
    user_id = None
    ws_token = token or _token_from_original_uri(x_original_uri)

    if authorization and authorization.lower().startswith("bearer "):
        user_id = _verify_jwt(authorization.split(" ", 1)[1], db)
    elif x_api_key:
        user_id = _verify_api_key(x_api_key, db)
    elif ws_token:
        # The WS query-param fallback carries whatever credential the
        # client has — the browser (React) always holds a JWT, but the
        # `mgs` CLI only ever holds an API key (no login flow). Try both
        # rather than assuming JWT, since it's just an opaque string here.
        user_id = _verify_jwt(ws_token, db) or _verify_api_key(ws_token, db)

    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # No more X-User-Plan (Fase 5, G8, BACKLOG.md) — there is no plan.
    response.headers["X-User-Id"] = user_id
    return {"user_id": user_id}
