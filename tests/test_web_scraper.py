"""Web scraper plugin hardening (bug-audit sprint Oct 19 2026).

Verifies the pre_chat hook only fires on an explicit read/fetch/scrape intent
(bare URLs in unrelated messages no longer trigger network fetches), URL-shape
and scheme validation, and the 2 MB response-body cap.
"""
import io

import pytest

from plugins.web_scraper.web_scraper import MAX_READ_BYTES, WebScraperPlugin


@pytest.fixture
def plugin():
    return WebScraperPlugin()


class TestExtractUrlIntent:

    def test_bare_url_in_message_no_intent(self, plugin):
        assert plugin._extract_url("hey look https://example.com/post") is None

    def test_plain_question_with_url_no_intent(self, plugin):
        assert plugin._extract_url("is https://example.com legit?") is None

    def test_open_application_name_not_url(self, plugin):
        assert plugin._extract_url("open chrome") is None

    def test_scrape_command(self, plugin):
        assert plugin._extract_url("scrape example.com") == "https://example.com"

    def test_read_with_trailing_punctuation(self, plugin):
        assert plugin._extract_url(
            "read https://example.com/post."
        ) == "https://example.com/post"

    def test_summarize_the_article_at(self, plugin):
        assert plugin._extract_url(
            "summarize the article at https://example.com/article"
        ) == "https://example.com/article"

    def test_fetch_this_url(self, plugin):
        assert plugin._extract_url(
            "fetch this https://example.com/doc"
        ) == "https://example.com/doc"

    def test_protocol_relative_target_gets_https(self, plugin):
        assert plugin._extract_url("read //example.com/page") == "https://example.com/page"

    def test_non_http_scheme_rejected(self, plugin):
        assert plugin._extract_url("read ftp://example.org/payload") is None
        assert plugin._extract_url("read file:///etc/passwd") is None

    def test_no_url_intent(self, plugin):
        assert plugin._extract_url("scrape it, please") is None


class TestScrapeCaps:

    @staticmethod
    def _fake_resp(payload: bytes, content_type: str, ip: str = "93.184.216.34"):
        """BytesIO fake shaped like an http.client response: the peer-guard
        reads resp.fp.raw.sock.getpeername()."""

        class _Sock:
            def getpeername(self):
                return (ip, 443)

        class _Raw:
            sock = _Sock()

        class _FP:
            raw = _Raw()

        resp = io.BytesIO(payload)
        resp.headers = {"Content-Type": content_type}
        resp.fp = _FP()
        return resp

    def test_oversized_body_capped(self, plugin, monkeypatch):
        big = b"<html><body>ok" + b"x" * (MAX_READ_BYTES + 10) + b"</body></html>"
        resp = self._fake_resp(big, "text/html")

        class _FakeOpener:
            def open(self, req, timeout=15):
                return resp

        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.require_public_target", lambda url: None
        )
        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.urllib.request.build_opener",
            lambda *a, **k: _FakeOpener(),
        )
        out = plugin._scrape("https://example.com/page")
        assert "exceeds" in out and "limit" in out

    def test_bad_content_type_not_fetched_into_text(self, plugin, monkeypatch):
        resp = self._fake_resp(b"%PDF-1.4", "application/pdf")

        class _FakeOpener:
            def open(self, req, timeout=15):
                return resp

        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.require_public_target", lambda url: None
        )
        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.urllib.request.build_opener",
            lambda *a, **k: _FakeOpener(),
        )
        out = plugin._scrape("https://example.com/file.pdf")
        assert "non-HTML" in out


class TestSSRFGuard:

    def test_loopback_initial_target_blocked(self, plugin, monkeypatch):
        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper._resolves_to_public_ip",
            lambda url: False,
        )
        out = plugin._scrape("http://127.0.0.1:9/admin")
        assert "Blocked" in out or "URL error" in out

    def test_dns_failure_blocked(self, plugin, monkeypatch):
        import socket
        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.socket.getaddrinfo",
            lambda *a, **k: (_ for _ in ()).throw(socket.gaierror(8, "not resolved")),
        )
        out = plugin._scrape("https://nonexistent-host.invalid/page")
        assert "Blocked" in out or "URL error" in out

    def test_redirect_to_loopback_blocked(self, plugin, monkeypatch):
        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper._resolves_to_public_ip",
            lambda url: False,
        )
        import urllib.error

        from plugins.web_scraper.web_scraper import _SafeRedirectHandler
        with pytest.raises(urllib.error.URLError) as exc:
            _SafeRedirectHandler().redirect_request(
                None, None, 302, "Found", {}, "http://127.0.0.1:8000/internal"
            )
        assert "127.0.0.1" in str(exc.value)

    def test_resolves_to_public_ip_classifies(self, monkeypatch):
        import socket

        from plugins.web_scraper.web_scraper import _resolves_to_public_ip

        def fake_gai(host, *a, **k):
            ip = "10.0.0.5" if host == "internal.lan" else "93.184.216.34"
            return [(socket.AF_INET, None, None, None, (ip, 0))]

        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.socket.getaddrinfo", fake_gai
        )
        assert _resolves_to_public_ip("https://internal.lan/x") is False
        assert _resolves_to_public_ip("https://example.com/x") is True

    def test_dev_opt_in_allows_private_target(self, plugin, monkeypatch):
        monkeypatch.setenv("MAI_SCRAPER_ALLOW_PRIVATE", "1")

        class _FakeResp(io.BytesIO):
            headers = {"Content-Type": "text/html"}

        resp = _FakeResp(b"<html><body>internal service status ok</body></html>")
        resp.seek(0)

        class _FakeOpener:
            def open(self, req, timeout=15):
                return resp

        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.urllib.request.build_opener",
            lambda *a, **k: _FakeOpener(),
        )
        out = plugin._scrape("http://127.0.0.1:8000/status")
        assert "Content from" in out


class TestConnectedPeer:
    """Connected-peer TOCTOU guard: assert_public_peer() re-checks the IP the
    socket actually connected to, after every pre-connect DNS validation."""

    def test_private_peer_aborts(self, plugin, monkeypatch):
        resp = TestScrapeCaps._fake_resp(
            b"<html><body>secret</body></html>", "text/html", ip="10.0.0.5"
        )

        class _FakeOpener:
            def open(self, req, timeout=15):
                return resp

        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.require_public_target", lambda url: None
        )
        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.urllib.request.build_opener",
            lambda *a, **k: _FakeOpener(),
        )
        out = plugin._scrape("https://example.com/page")
        assert "non-public peer" in out

    def test_unverifiable_peer_fails_closed(self, plugin, monkeypatch):
        resp = TestScrapeCaps._fake_resp(b"<html><body>ok</body></html>", "text/html")

        class _DeadSock:
            def getpeername(self):
                raise OSError(10057, "Socket is not connected")

        resp.fp.raw.sock = _DeadSock()

        class _FakeOpener:
            def open(self, req, timeout=15):
                return resp

        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.require_public_target", lambda url: None
        )
        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.urllib.request.build_opener",
            lambda *a, **k: _FakeOpener(),
        )
        out = plugin._scrape("https://example.com/page")
        assert "Could not verify connected peer IP" in out

    def test_public_peer_passes(self, plugin, monkeypatch):
        resp = TestScrapeCaps._fake_resp(
            b"<html><body>hello world</body></html>", "text/html"
        )

        class _FakeOpener:
            def open(self, req, timeout=15):
                return resp

        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.require_public_target", lambda url: None
        )
        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.urllib.request.build_opener",
            lambda *a, **k: _FakeOpener(),
        )
        out = plugin._scrape("https://example.com/page")
        assert "Content from" in out and "hello world" in out

    def test_empty_proxy_handler_in_opener_chain(self, plugin, monkeypatch):
        captured = {}

        class _FakeOpener:
            def open(self, req, timeout=15):
                return TestScrapeCaps._fake_resp(
                    b"<html><body>hi</body></html>", "text/html"
                )

        def fake_build(*handlers, **kwargs):
            captured["handlers"] = handlers
            return _FakeOpener()

        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.require_public_target", lambda url: None
        )
        monkeypatch.setattr(
            "plugins.web_scraper.web_scraper.urllib.request.build_opener", fake_build
        )
        plugin._scrape("https://example.com/page")
        proxies = [
            h for h in captured["handlers"]
            if isinstance(h, __import__("urllib.request", fromlist=["ProxyHandler"]).ProxyHandler)
        ]
        assert proxies and proxies[0].proxies == {}
