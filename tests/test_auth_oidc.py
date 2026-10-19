"""Auth cookie + post-login redirect hardening (bug-audit sprint Oct 19 2026).

Verifies:
- _safe_redirect_target only lets in-app local paths through (open-redirect
  guard for the OIDC redirect_after / SAML relay_state values).
- _set_session_cookie emits HttpOnly + SameSite=Lax always, Secure when the
  request is served over HTTPS (all 9 auth set_cookie sites route through it).
"""
import pytest
from fastapi import Request, Response

from api.auth import _safe_redirect_target, _set_session_cookie


class TestSafeRedirectTarget:

    @pytest.mark.parametrize(
        "target,expected",
        [
            ("/", "/"),
            ("/dashboard", "/dashboard"),
            ("https://evil.com", "/"),
            ("http://evil.com/steal", "/"),
            ("//evil.com", "/"),
            ("javascript:alert(1)", "/"),
            ("data:text/html,evil", "/"),
            ("evil.com/path", "/"),
            ("\n/js", "/"),
            ("", "/"),
            (None, "/"),
        ],
    )
    def test_targets(self, target, expected):
        assert _safe_redirect_target(target) == expected

    def test_non_string_rejected(self):
        assert _safe_redirect_target(123) == "/"


class TestSessionCookieHardening:

    @staticmethod
    def _request(scheme: str) -> Request:
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "method": "GET",
            "scheme": scheme,
            "path": "/",
            "headers": [],
            "query_string": b"",
            "server": ("localhost", 8000),
        }
        return Request(scope)

    def test_secure_flag_on_https(self):
        resp = Response()
        _set_session_cookie(resp, self._request("https"), "access_token", "t", 900)
        header = resp.headers["set-cookie"].lower()
        assert "secure" in header
        assert "samesite=lax" in header
        assert "httponly" in header

    def test_no_secure_flag_on_http(self):
        resp = Response()
        _set_session_cookie(resp, self._request("http"), "access_token", "t", 900)
        header = resp.headers["set-cookie"].lower()
        assert "samesite=lax" in header
        assert "secure" not in header
