"""AuthManager — JWT authentication, API keys, token blacklist, audit logging.

Load this file when the user needs the full AuthManager implementation.
Usage:
    auth = AuthManager(jwt_secret=os.getenv("JWT_SECRET"))
    token = auth.create_access_token("user_abc")
    payload = auth.verify_token(token, expected_type="access")
"""

import hashlib
import json
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Set

import bcrypt
from fastapi import HTTPException, Request
from jose import JWTError, jwt

logger = logging.getLogger("api.auth")


class AuthManager:
    """Central auth — JWT issuance/verification, API keys, token blacklist.

    Principles applied:
    - Defence in depth: JWT + API keys + fallback chain
    - Fail secure: exceptions return 401, never 200
    - Audit everything: every auth event logged
    - Never commit secrets: env vars only
    """

    def __init__(
        self,
        jwt_secret: str = "",
        algorithm: str = "HS256",
        access_expire_minutes: int = 15,
        refresh_expire_days: int = 7,
        api_key_store_path: str = "",
    ):
        self._secret = jwt_secret or os.getenv("JWT_SECRET", "")
        if not self._secret:
            raise RuntimeError("JWT_SECRET must be set via env var or constructor")
        self._algorithm = algorithm
        self._access_ttl = timedelta(minutes=access_expire_minutes)
        self._refresh_ttl = timedelta(days=refresh_expire_days)
        self._blacklock = threading.RLock()
        self._blacklist: Set[str] = set()
        self._api_key_store_path = api_key_key_store_path or os.getenv(
            "API_KEY_STORE_PATH", ""
        )
        self._api_keys: dict = {}
        self._api_lock = threading.RLock()
        self._load_api_keys()

    def create_access_token(
        self, subject: str, extra: Optional[dict] = None
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "iat": now,
            "exp": now + self._access_ttl,
            "type": "access",
            "jti": secrets.token_hex(16),
        }
        if extra:
            payload.update(extra)
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_refresh_token(self, subject: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "iat": now,
            "exp": now + self._refresh_ttl,
            "type": "refresh",
            "jti": secrets.token_hex(16),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify_token(self, token: str, expected_type: str = "access") -> dict:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["sub", "exp", "type", "jti"]},
            )
            if payload.get("type") != expected_type:
                raise HTTPException(
                    status_code=401, detail=f"Invalid token type: expected {expected_type}"
                )
            if payload["exp"] < time.time():
                raise HTTPException(status_code=401, detail="Token expired")
            with self._blacklock:
                if payload["jti"] in self._blacklist:
                    raise HTTPException(status_code=401, detail="Token revoked")
            return payload
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    def revoke_token(self, jti: str) -> None:
        with self._blacklock:
            self._blacklist.add(jti)
            logger.info("auth_event event=token_revoke jti=%s", jti)

    def refresh_token(self, refresh_token: str) -> dict:
        payload = self._verify_token(refresh_token, expected_type="refresh")
        subject = payload["sub"]
        self.revoke_token(payload["jti"])
        return {
            "access_token": self.create_access_token(subject),
            "refresh_token": self.create_refresh_token(subject),
        }

    def create_api_key(self, label: str) -> dict:
        raw = "mai_" + secrets.token_hex(32)
        key_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
        hashed = bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()
        entry = {
            "id": key_id,
            "label": label,
            "prefix": raw[:12],
            "hash": hashed,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._api_lock:
            self._api_keys[key_id] = entry
            self._save_api_keys()
        logger.info("auth_event event=api_key_create label=%s id=%s", label, key_id)
        return {"id": key_id, "key": raw, "label": label}

    def verify_api_key(self, key: str) -> Optional[str]:
        if not key.startswith("mai_"):
            return None
        key_id = hashlib.sha256(key.encode()).hexdigest()[:16]
        with self._api_lock:
            entry = self._api_keys.get(key_id)
            if entry and bcrypt.checkpw(key.encode(), entry["hash"].encode()):
                return entry["id"]
        return None

    async def get_current_user(self, request: Request) -> dict:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return self.verify_token(token, expected_type="access")
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            key_id = self.verify_api_key(api_key)
            if key_id:
                return {"sub": f"api_key:{key_id}", "type": "api_key"}
        raise HTTPException(status_code=401, detail="Not authenticated")

    def _load_api_keys(self) -> None:
        if not self._api_key_store_path:
            return
        path = Path(self._api_key_store_path)
        if path.exists():
            with self._api_lock:
                self._api_keys = json.loads(path.read_text())

    def _save_api_keys(self) -> None:
        if not self._api_key_store_path:
            return
        path = Path(self._api_key_store_path)
        to_save = {k: v for k, v in self._api_keys.items()}
        path.write_text(json.dumps(to_save, indent=2))
