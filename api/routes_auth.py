"""Authentication routes — login, token refresh, user info."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger("api.routes_auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Global ProfileStore reference (set by server on bootstrap) ──────────
_profile_store = None


def set_profile_store(store):
    global _profile_store
    _profile_store = store


# ── Schemas ──────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str


# ── Routes ───────────────────────────────────────────────────────────────
def _store():
    if _profile_store is None:
        raise HTTPException(status_code=503, detail="Profile store not available")
    return _profile_store


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    pw = _store().get_password_hash(body.username)
    if pw is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not verify_password(body.password, pw):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return LoginResponse(
        access_token=create_access_token(body.username),
        refresh_token=create_refresh_token(body.username),
    )


@router.post("/refresh", response_model=LoginResponse)
def refresh(body: TokenRefreshRequest):
    from api.auth import decode_token
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token is not a refresh token")
    username = payload.get("sub", "")
    if not username or not _store().user_exists(username):
        raise HTTPException(status_code=401, detail="User not found")
    return LoginResponse(
        access_token=create_access_token(username),
        refresh_token=create_refresh_token(username),
    )


@router.post("/register", response_model=UserInfo)
def register(body: UserCreate):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if _store().user_exists(body.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    _store().create_user(body.username, hash_password(body.password))
    logger.info("Registered user: %s", body.username)
    return UserInfo(username=body.username)


@router.get("/me", response_model=UserInfo)
def me(current_user: str = Depends(get_current_user)):
    return UserInfo(username=current_user)
