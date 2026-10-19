"""Tests for ProfileStore and profile API routes."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestProfileStore:

    @pytest.fixture
    def store(self):
        from core.profile_store import ProfileStore
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test_profiles.db"
            s = ProfileStore(str(db))
            yield s
            s.close()

    def test_create_and_get_user(self, store):
        assert store.create_user("alice", "hashed_pw_123")
        user = store.get_user("alice")
        assert user is not None
        assert user["user_id"] == "alice"
        assert user["password"] == "hashed_pw_123"

    def test_create_duplicate_user(self, store):
        assert store.create_user("bob", "hash1")
        assert not store.create_user("bob", "hash2")

    def test_get_password_hash(self, store):
        store.create_user("charlie", "secret_hash")
        assert store.get_password_hash("charlie") == "secret_hash"
        assert store.get_password_hash("nonexistent") is None

    def test_user_exists(self, store):
        store.create_user("dave", "hash")
        assert store.user_exists("dave")
        assert not store.user_exists("eve")

    def test_update_display_name(self, store):
        store.create_user("frank", "hash", display_name="Frank")
        assert store.update_display_name("frank", "Frankie")
        user = store.get_user("frank")
        assert user["display_name"] == "Frankie"

    def test_update_preferences(self, store):
        store.create_user("grace", "hash")
        prefs = {"theme": "dark", "language": "en"}
        assert store.update_preferences("grace", prefs)
        user = store.get_user("grace")
        saved = json.loads(user["preferences"]) if isinstance(user["preferences"], str) else user["preferences"]
        assert saved == prefs

    def test_delete_user(self, store):
        store.create_user("heidi", "hash")
        assert store.user_exists("heidi")
        assert store.delete_user("heidi")
        assert not store.user_exists("heidi")

    def test_delete_nonexistent_user(self, store):
        assert not store.delete_user("nobody")

    def test_list_users(self, store):
        store.create_user("ivan", "hash", display_name="Ivan")
        store.create_user("judy", "hash", display_name="Judy")
        users = store.list_users()
        assert len(users) >= 2
        ids = [u["user_id"] for u in users]
        assert "ivan" in ids
        assert "judy" in ids

    def test_count_users(self, store):
        store.create_user("karen", "hash")
        store.create_user("leo", "hash")
        assert store.count_users() >= 2

    def test_get_nonexistent_user(self, store):
        assert store.get_user("nobody") is None


class TestProfileAPI:

    @pytest.fixture(autouse=True)
    def _setup(self):
        import os
        import tempfile

        from api import routes_auth, routes_profile
        from api.server import mai
        from core.profile_store import ProfileStore
        tmp = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp, "test_profiles.db")
            store = ProfileStore(db_path)
            mai.profile_store = store
            routes_profile.set_profile_store(store)
            routes_auth.set_profile_store(store)
            yield store
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.fixture
    def client(self):
        from api.server import app
        return TestClient(app)

    def test_get_profile_me(self, client):
        from api.auth import create_access_token, hash_password
        from api.server import mai
        mai.profile_store.create_user("testuser", hash_password("testpass"))
        token = create_access_token("testuser")
        headers = {"Authorization": f"Bearer {token}"}
        with patch("config.runtime.API_REQUIRE_AUTH", True), patch("app.config_loader.API_REQUIRE_AUTH", True):
            resp = client.get("/api/profile/me", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["user_id"] == "testuser"

    def test_get_profile_me_not_found(self, client):
        resp = client.get("/api/profile/me")
        assert resp.status_code == 404

    def test_update_display_name(self, client):
        from api.auth import create_access_token, hash_password
        from api.server import mai
        mai.profile_store.create_user("testuser", hash_password("testpass"))
        token = create_access_token("testuser")
        headers = {"Authorization": f"Bearer {token}"}
        with patch("config.runtime.API_REQUIRE_AUTH", True), patch("app.config_loader.API_REQUIRE_AUTH", True):
            resp = client.put("/api/profile/me/display-name", json={"display_name": "Test User"}, headers=headers)
            assert resp.status_code == 200
            assert resp.json()["display_name"] == "Test User"

    def test_update_preferences(self, client):
        from api.auth import create_access_token, hash_password
        from api.server import mai
        mai.profile_store.create_user("testuser", hash_password("testpass"))
        token = create_access_token("testuser")
        headers = {"Authorization": f"Bearer {token}"}
        with patch("config.runtime.API_REQUIRE_AUTH", True), patch("app.config_loader.API_REQUIRE_AUTH", True):
            prefs = {"theme": "light", "notifications": False}
            resp = client.put("/api/profile/me/preferences", json={"preferences": prefs}, headers=headers)
            assert resp.status_code == 200

    def test_delete_my_account(self, client):
        from api.auth import create_access_token, hash_password
        from api.server import mai
        mai.profile_store.create_user("testuser", hash_password("testpass"))
        token = create_access_token("testuser")
        headers = {"Authorization": f"Bearer {token}"}
        with patch("config.runtime.API_REQUIRE_AUTH", True), patch("app.config_loader.API_REQUIRE_AUTH", True):
            resp = client.delete("/api/profile/me", headers=headers)
            assert resp.status_code == 200


class TestServerSecurityConsistency:
    """S-4: single-source auth dependency + STREAM_TOPICS dedup + CORS."""

    def test_require_auth_delegates_to_auth_module(self):
        """``_require_auth`` must be a thin wrapper over ``get_current_user``
        so JWT/static-token logic cannot drift across two implementations."""

        from api.server import _require_auth
        src = _require_auth.__code__.co_code
        assert src is not None
        # Verify it calls the auth dependency by importing the module-level
        # delegation rather than inlining token parsing.
        import inspect
        body = inspect.getsource(_require_auth)
        assert "get_current_user" in body
        assert "decode_token" not in body
        assert "API_AUTH_TOKEN" not in body

    def test_stream_topics_single_source(self):
        """ws_bridge must not duplicate the STREAM_TOPICS list."""
        import inspect

        from api import ws_bridge
        body = inspect.getsource(ws_bridge.WSBridge.wire)
        assert "STREAM_TOPICS" in body
        assert 'state.voice.listening' not in body

    def test_cors_credentials_disabled_for_wildcard(self):
        """Wildcard origins must not send ``Access-Control-Allow-Credentials``
        (browsers reject the combo). Explicit origins may enable credentials."""
        from api.server import _allow_credentials, _cors_origins
        if _cors_origins == ["*"]:
            assert _allow_credentials is False
        else:
            assert _allow_credentials is True
