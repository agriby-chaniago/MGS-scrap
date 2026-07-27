from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         UUID
    email:      str
    created_at: datetime


class ApiKeyCreatedResponse(BaseModel):
    id:      UUID
    api_key: str
