from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db
from models.orm import ApiKey, User
from models.schemas import (
    ApiKeyCreatedResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserSchema,
)
from services.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_password,
    verify_password,
)
from shared.response import success_response

router = APIRouter(prefix="/api/v1/auth")

SERVICE_NAME = "auth_service"


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token not found")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token invalid or expired")
    user = db.query(User).filter(User.id == UUID(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/register", status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id), user.email)
    return success_response(
        data=TokenResponse(access_token=token).model_dump(),
        service=SERVICE_NAME,
    )


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(str(user.id), user.email)
    return success_response(
        data=TokenResponse(access_token=token).model_dump(),
        service=SERVICE_NAME,
    )


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return success_response(
        data=UserSchema.model_validate(current_user).model_dump(),
        service=SERVICE_NAME,
    )


# /upgrade removed in Fase 5 (G8, BACKLOG.md) — there is no plan to
# upgrade to anymore.


@router.post("/api-keys", status_code=201)
def create_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # No more plan restriction (used to be Pro/Max only) — API keys are
    # available to any authenticated user now that there's no tier to
    # gate them behind (Fase 5, G8, BACKLOG.md).
    raw_key, key_hash = generate_api_key()
    api_key = ApiKey(user_id=current_user.id, key_hash=key_hash)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return success_response(
        data=ApiKeyCreatedResponse(id=api_key.id, api_key=raw_key).model_dump(),
        service=SERVICE_NAME,
    )
