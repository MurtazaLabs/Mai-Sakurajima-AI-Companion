"""SQLite-backed persistent user profile store with multi-tenancy support.

Replaces the in-memory ``_users`` dict from ``api/routes_auth.py`` with
a durable store so profiles survive server restarts.
Supports multi-tenancy via tenant_id isolation.
"""

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path

logger = logging.getLogger("core.profile_store")

_DB_DIR = Path(__file__).resolve().parent.parent / "data" / "profiles"
_DB_PATH = _DB_DIR / "profiles.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id     TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    password    TEXT NOT NULL,
    display_name TEXT DEFAULT '',
    preferences TEXT DEFAULT '{}',
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_profiles_tenant ON profiles(tenant_id);
"""


class ProfileStore:
    """Thread-safe SQLite store for user profiles."""

    def __init__(self, db_path: str | None = None):
        self._lock = threading.RLock()
        self._db_path = Path(db_path or _DB_PATH)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    # ── Connection management ──────────────────────────────────────────
    def _init_db(self):
        with self._lock:
            if self._conn:
                return
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
            logger.info("ProfileStore ready at %s", self._db_path)

    def _cursor(self):
        if not self._conn:
            self._init_db()
        return self._conn.cursor()

    def close(self):
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    # ── CRUD ───────────────────────────────────────────────────────────
    def create_user(self, user_id: str, password_hash: str, display_name: str = "") -> bool:
        with self._lock:
            try:
                now = time.time()
                self._cursor().execute(
                    "INSERT INTO profiles (user_id, password, display_name, preferences, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, password_hash, display_name, "{}", now, now),
                )
                self._conn.commit()
                logger.info("Created user: %s", user_id)
                return True
            except sqlite3.IntegrityError:
                logger.warning("User already exists: %s", user_id)
                return False

    def get_user(self, user_id: str) -> dict | None:
        with self._lock:
            row = self._cursor().execute(
                "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
            if not row:
                return None
            return dict(row)

    def get_password_hash(self, user_id: str) -> str | None:
        with self._lock:
            row = self._cursor().execute(
                "SELECT password FROM profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row["password"] if row else None

    def user_exists(self, user_id: str) -> bool:
        with self._lock:
            row = self._cursor().execute(
                "SELECT 1 FROM profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row is not None

    def update_preferences(self, user_id: str, preferences: dict) -> bool:
        with self._lock:
            cur = self._cursor()
            cur.execute(
                "UPDATE profiles SET preferences = ?, updated_at = ? WHERE user_id = ?",
                (json.dumps(preferences), time.time(), user_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def update_display_name(self, user_id: str, display_name: str) -> bool:
        with self._lock:
            cur = self._cursor()
            cur.execute(
                "UPDATE profiles SET display_name = ?, updated_at = ? WHERE user_id = ?",
                (display_name, time.time(), user_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def delete_user(self, user_id: str) -> bool:
        with self._lock:
            cur = self._cursor()
            cur.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def list_users(self) -> list[dict]:
        with self._lock:
            rows = self._cursor().execute(
                "SELECT user_id, display_name, created_at FROM profiles ORDER BY created_at"
            ).fetchall()
            return [dict(r) for r in rows]

    def count_users(self) -> int:
        with self._lock:
            row = self._cursor().execute("SELECT COUNT(*) AS cnt FROM profiles").fetchone()
            return row["cnt"] if row else 0
