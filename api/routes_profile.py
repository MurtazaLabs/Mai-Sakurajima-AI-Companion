"""Profile CRUD routes — manage user preferences, display name, and sessions."""

import json as _json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from api.auth import get_current_user

logger = logging.getLogger("api.routes_profile")

router = APIRouter(prefix="/api/profile", tags=["profile"])

_profile_store = None
_session_manager = None


def set_profile_store(store):
    global _profile_store
    _profile_store = store


def set_session_manager(mgr):
    global _session_manager
    _session_manager = mgr


# ── Schemas ──────────────────────────────────────────────────────────────
class ProfileResponse(BaseModel):
    user_id: str
    display_name: str
    preferences: dict
    created_at: float


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    created_at: float
    last_activity: float
    expires_at: float
    metadata: dict


class SessionCreateRequest(BaseModel):
    user_id: str
    metadata: dict = {}


# ── Routes ───────────────────────────────────────────────────────────────
def _store():
    if _profile_store is None:
        raise HTTPException(status_code=503, detail="Profile store not available")
    return _profile_store


def _session_mgr():
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not available")
    return _session_manager


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(current_user: str = Depends(get_current_user)):
    user = _store().get_user(current_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    prefs = user.get("preferences", "{}")
    if isinstance(prefs, str):
        prefs = _json.loads(prefs)
    return ProfileResponse(
        user_id=user["user_id"],
        display_name=user.get("display_name", ""),
        preferences=prefs,
        created_at=user["created_at"],
    )


@router.put("/me/display-name")
async def update_display_name(request: Request, current_user: str = Depends(get_current_user)):
    body = await request.json()
    display_name = body.get("display_name", "")
    if not _store().update_display_name(current_user, display_name):
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "ok", "display_name": display_name}


@router.put("/me/preferences")
async def update_preferences(request: Request, current_user: str = Depends(get_current_user)):
    body = await request.json()
    preferences = body.get("preferences", {})
    if not _store().update_preferences(current_user, preferences):
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "ok", "preferences": preferences}


@router.delete("/me")
def delete_my_account(current_user: str = Depends(get_current_user)):
    if not _store().delete_user(current_user):
        raise HTTPException(status_code=404, detail="User not found")
    logger.info("Deleted user: %s", current_user)
    return {"status": "ok"}


# Admin/profile management endpoints
@router.post("/admin", response_model=ProfileResponse)
async def create_user(request: Request, current_user: str = Depends(get_current_user)):
    """Create a new user (admin only)."""
    body = await request.json()
    username = body.get("username")
    password = body.get("password")
    display_name = body.get("display_name", "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if _store().user_exists(username):
        raise HTTPException(status_code=409, detail="Username already exists")
    from api.auth import hash_password
    _store().create_user(username, hash_password(password), display_name)
    user = _store().get_user(username)
    return ProfileResponse(
        user_id=user["user_id"],
        display_name=user.get("display_name", ""),
        preferences={},
        created_at=user["created_at"],
    )


@router.get("/admin", response_model=list[ProfileResponse])
def list_users(current_user: str = Depends(get_current_user)):
    """List all users (admin only)."""
    users = _store().list_users()
    return [
        ProfileResponse(
            user_id=u["user_id"],
            display_name=u.get("display_name", ""),
            preferences=_json.loads(u.get("preferences", "{}")) if isinstance(u.get("preferences"), str) else u.get("preferences", {}),
            created_at=u["created_at"],
        )
        for u in users
    ]


@router.get("/admin/{user_id}", response_model=ProfileResponse)
def get_user(user_id: str, current_user: str = Depends(get_current_user)):
    """Get user by ID (admin only)."""
    user = _store().get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    prefs = user.get("preferences", "{}")
    if isinstance(prefs, str):
        prefs = _json.loads(prefs)
    return ProfileResponse(
        user_id=user["user_id"],
        display_name=user.get("display_name", ""),
        preferences=prefs,
        created_at=user["created_at"],
    )


@router.delete("/admin/{user_id}")
def delete_user(user_id: str, current_user: str = Depends(get_current_user)):
    """Delete a user (admin only)."""
    if not _store().delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    # Also delete all sessions for this user
    if _session_manager:
        _session_manager.delete_user_sessions(user_id)
    logger.info("Deleted user: %s", user_id)
    return {"status": "ok"}


# Session management endpoints
@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: Request, current_user: str = Depends(get_current_user)):
    """Create a new session for a user."""
    body = await request.json()
    user_id = body.get("user_id", current_user)
    metadata = body.get("metadata", {})
    session = _session_mgr().create_session(user_id, metadata)
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at,
        last_activity=session.last_activity,
        expires_at=session.expires_at,
        metadata=session.metadata,
    )


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(user_id: str = Query(None), current_user: str = Depends(get_current_user)):
    """List sessions. If user_id not provided, lists current user's sessions."""
    target_user = user_id or current_user
    sessions = _session_mgr().get_user_sessions(target_user)
    return [
        SessionResponse(
            session_id=s.session_id,
            user_id=s.user_id,
            created_at=s.created_at,
            last_activity=s.last_activity,
            expires_at=s.expires_at,
            metadata=s.metadata,
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, current_user: str = Depends(get_current_user)):
    """Delete a session."""
    if not _session_mgr().delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "ok"}


@router.delete("/sessions/user/{user_id}")
def delete_user_sessions(user_id: str, current_user: str = Depends(get_current_user)):
    """Delete all sessions for a user."""
    count = _session_mgr().delete_user_sessions(user_id)
    return {"status": "ok", "deleted": count}