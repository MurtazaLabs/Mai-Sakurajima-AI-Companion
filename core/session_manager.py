"""
Session Manager — manages active user sessions with expiry and limits.
"""
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class Session:
    """Active user session."""
    session_id: str
    user_id: str
    created_at: float
    last_activity: float
    expires_at: float
    metadata: dict = field(default_factory=dict)


class SessionManager:
    """Manages active user sessions with TTL and concurrent limits."""

    def __init__(
        self,
        session_ttl_seconds: int = 3600,
        max_sessions_per_user: int = 5,
        max_total_sessions: int = 1000,
        cleanup_interval_seconds: int = 300,
    ):
        self.session_ttl = session_ttl_seconds
        self.max_sessions_per_user = max_sessions_per_user
        self.max_total_sessions = max_total_sessions
        self.cleanup_interval = cleanup_interval_seconds

        self._sessions: dict[str, Session] = {}
        self._user_sessions: dict[str, list[str]] = {}
        self._lock = threading.RLock()

        self._cleanup_thread: threading.Thread | None = None
        self._stop_cleanup = threading.Event()

    def start(self):
        """Start background cleanup thread."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return
        self._stop_cleanup.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True, name="session-cleanup"
        )
        self._cleanup_thread.start()

    def stop(self):
        """Stop background cleanup thread."""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)

    def _cleanup_loop(self):
        """Background loop to expire old sessions."""
        while not self._stop_cleanup.is_set():
            time.sleep(self.cleanup_interval)
            if self._stop_cleanup.is_set():
                break
            self._expire_sessions()

    def _expire_sessions(self):
        """Remove expired sessions."""
        now = time.time()
        with self._lock:
            expired = [
                sid for sid, sess in self._sessions.items()
                if sess.expires_at <= now
            ]
            for sid in expired:
                self._remove_session(sid)

    def create_session(self, user_id: str, metadata: dict | None = None) -> Session:
        """Create a new session for a user."""
        with self._lock:
            # Enforce per-user limit
            user_session_ids = self._user_sessions.get(user_id, [])
            if len(user_session_ids) >= self.max_sessions_per_user:
                # Remove oldest session for this user
                oldest_sid = min(
                    user_session_ids,
                    key=lambda sid: self._sessions[sid].created_at if sid in self._sessions else 0
                )
                self._remove_session(oldest_sid)

            # Enforce total limit
            if len(self._sessions) >= self.max_total_sessions:
                # Remove oldest session overall
                oldest_sid = min(
                    self._sessions.keys(),
                    key=lambda sid: self._sessions[sid].created_at
                )
                self._remove_session(oldest_sid)

            now = time.time()
            session = Session(
                session_id=uuid.uuid4().hex,
                user_id=user_id,
                created_at=now,
                last_activity=now,
                expires_at=now + self.session_ttl,
                metadata=metadata or {},
            )
            self._sessions[session.session_id] = session
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            self._user_sessions[user_id].append(session.session_id)
            return session

    def get_session(self, session_id: str) -> Session | None:
        """Get session by ID, extending expiry on access."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.expires_at > time.time():
                session.last_activity = time.time()
                session.expires_at = time.time() + self.session_ttl
                return session
            elif session:
                self._remove_session(session_id)
            return None

    def get_user_sessions(self, user_id: str) -> list[Session]:
        """Get all active sessions for a user."""
        with self._lock:
            session_ids = self._user_sessions.get(user_id, [])
            sessions = []
            for sid in session_ids:
                sess = self._sessions.get(sid)
                if sess and sess.expires_at > time.time():
                    sessions.append(sess)
                elif sess:
                    self._remove_session(sid)
            return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a specific session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                self._remove_session(session_id)
                return True
            return False

    def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user."""
        with self._lock:
            session_ids = self._user_sessions.get(user_id, [])
            count = 0
            for sid in list(session_ids):
                if self._remove_session(sid):
                    count += 1
            return count

    def _remove_session(self, session_id: str) -> bool:
        """Internal: remove session from all indexes."""
        session = self._sessions.pop(session_id, None)
        if session:
            user_sessions = self._user_sessions.get(session.user_id, [])
            if session_id in user_sessions:
                user_sessions.remove(session_id)
            if not user_sessions:
                self._user_sessions.pop(session.user_id, None)
            return True
        return False

    def stats(self) -> dict:
        """Get session statistics."""
        with self._lock:
            now = time.time()
            active = sum(1 for s in self._sessions.values() if s.expires_at > now)
            return {
                "total_sessions": len(self._sessions),
                "active_sessions": active,
                "users_with_sessions": len(self._user_sessions),
            }


def create_session_manager(
    session_ttl_seconds: int = 3600,
    max_sessions_per_user: int = 5,
    max_total_sessions: int = 1000,
    cleanup_interval_seconds: int = 300,
) -> SessionManager:
    """Factory function to create a configured SessionManager."""
    return SessionManager(
        session_ttl_seconds=session_ttl_seconds,
        max_sessions_per_user=max_sessions_per_user,
        max_total_sessions=max_total_sessions,
        cleanup_interval_seconds=cleanup_interval_seconds,
    )


if __name__ == "__main__":
    # Quick test
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
    mgr = create_session_manager(session_ttl_seconds=10)
    mgr.start()
    s1 = mgr.create_session("user1", {"device": "web"})
    s2 = mgr.create_session("user1", {"device": "mobile"})
    s3 = mgr.create_session("user2")
    logger.info("Created: %s, %s, %s", s1.session_id, s2.session_id, s3.session_id)
    logger.info("User1 sessions: %d", len(mgr.get_user_sessions("user1")))
    logger.info("Stats: %s", mgr.stats())
    time.sleep(11)
    logger.info("After expiry - Stats: %s", mgr.stats())
    mgr.stop()