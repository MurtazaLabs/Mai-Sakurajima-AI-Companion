"""M0 Frontend Validation Tests

Validates that M0 requirements are met:
- Fix 1: No getUserMedia / browser mic capture in any static JS
- Fix 2: State primitives in components.css, api-client with JWT refresh
- Design tokens present, login page routes correctly, no clobbering of legacy router
"""
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
STATIC_DIR = PROJECT_ROOT / "api" / "static"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"


class TestM0FilesExist:
    """Core M0 files must exist."""

    def test_css_files_exist(self):
        for name in ["reset.css", "typography.css", "layout.css", "utilities.css"]:
            assert (CSS_DIR / name).exists(), f"Missing CSS file: {name}"

    def test_js_core_files_exist(self):
        for name in [
            "event-bus.js",
            "api-client.js",
            "history-router.js",
            "keyboard.js",
            "accessibility.js",
            "login.js",
        ]:
            assert (JS_DIR / name).exists(), f"Missing JS file: {name}"

    def test_login_page_exists(self):
        assert (STATIC_DIR / "login.html").exists(), "Missing login.html"


class TestFix1_NoBrowserMicCapture:
    """Fix 1: Voice page must not use browser microphone (getUserMedia)."""

    FORBIDDEN_PATTERNS = [
        r"getUserMedia",
        r"MediaDevices",
        r"webkitSpeechRecognition",
        r"SpeechRecognition",
        r"AudioContext.*getUserMedia",
        r"navigator\.mediaDevices",
    ]

    def test_no_getusermedia_in_static_js(self):
        js_files = list(JS_DIR.rglob("*.js"))
        assert js_files, "No JS files found"
        violations = []
        for js_file in js_files:
            content = js_file.read_text(encoding="utf-8")
            for pattern in self.FORBIDDEN_PATTERNS:
                if re.search(pattern, content):
                    violations.append(f"{js_file.name}: {pattern}")
        assert not violations, f"Fix 1 violated (browser mic capture found):\n" + "\n".join(violations)


class TestFix2_StatePrimitivesAndAuth:
    """Fix 2: State primitives in components.css, api-client with JWT refresh."""

    def test_components_has_state_primitives(self):
        css = (CSS_DIR / "components.css").read_text(encoding="utf-8")
        assert ".state-loading" in css, "Missing .state-loading in components.css"
        assert ".state-empty" in css, "Missing .state-empty in components.css"
        assert ".state-error" in css, "Missing .state-error in components.css"
        assert "@keyframes state-orbit" in css, "Missing state-orbit keyframes"
        assert "@keyframes state-breathe" in css, "Missing state-breathe keyframes"
        assert "@keyframes state-slide" in css, "Missing state-slide keyframes"

    def test_api_client_has_refresh_logic(self):
        js = (JS_DIR / "api-client.js").read_text(encoding="utf-8")
        assert "Bearer" in js, "api-client.js missing Authorization Bearer"
        assert "/api/auth/refresh" in js, "api-client.js missing refresh endpoint"
        assert "refreshTokens" in js, "api-client.js missing refreshTokens function"
        assert "redirectToLogin" in js, "api-client.js missing redirectToLogin"
        assert "localStorage" in js, "api-client.js missing token storage"
        assert "refreshPromise" in js, "api-client.js missing single-flight refresh"
        assert "AUTH_PATHS" in js, "api-client.js missing auth path exclusions"

    def test_design_tokens_has_accent_primary(self):
        css = (CSS_DIR / "design-tokens.css").read_text(encoding="utf-8")
        assert "--color-accent-primary: #7C5CFF" in css, "Design tokens missing MAI purple"

    def test_login_page_links_tokens_and_components(self):
        html = (STATIC_DIR / "login.html").read_text(encoding="utf-8")
        for href in [
            "reset.css",
            "design-tokens.css",
            "typography.css",
            "layout.css",
            "components.css",
            "utilities.css",
        ]:
            assert f'href="/css/{href}"' in html or f'href="css/{href}"' in html, f"login.html missing {href}"
        assert 'src="/js/login.js"' in html or 'src="js/login.js"' in html, "login.html missing login.js"

    def test_login_page_no_inline_script(self):
        html = (STATIC_DIR / "login.html").read_text(encoding="utf-8")
        script_tags = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
        for script in script_tags:
            assert script.strip() == "", "login.html should have no inline scripts (use module)"


class TestRouterDoesNotClobberMaiRouter:
    """History router must not overwrite window.MaiRouter."""

    def test_history_router_exposes_maihistoryrouter(self):
        js = (JS_DIR / "history-router.js").read_text(encoding="utf-8")
        assert "MaiHistoryRouter" in js, "history-router.js must expose MaiHistoryRouter"
        assert "window.MaiRouter" not in js, "history-router.js must not touch window.MaiRouter"

    def test_legacy_router_unchanged(self):
        js = (JS_DIR / "router.js").read_text(encoding="utf-8")
        assert "window.MaiRouter" in js, "Legacy router.js must still export MaiRouter"
        # Legacy router uses pushState to /desktop#space=... — it's the desktop shell router
        # Just ensure it doesn't reference the new HistoryRouter symbol
        assert "MaiHistoryRouter" not in js, "Legacy router must not reference MaiHistoryRouter"


class TestServerRouteRegistration:
    """Server must register /login route."""

    def test_server_page_files_includes_login(self):
        server = (PROJECT_ROOT / "api" / "server.py").read_text(encoding="utf-8")
        assert '"login"' in server or "'login'" in server, "server.py _page_files missing 'login'"


class TestCSSNoTailwindRing:
    """Design tokens should not use invalid Tailwind `ring` properties."""

    def test_no_ring_properties(self):
        css = (CSS_DIR / "design-tokens.css").read_text(encoding="utf-8")
        # Check for invalid Tailwind ring-* properties on their own lines (not substrings)
        for prop in [r"^\s*ring:\s", r"^\s*ring-color:\s", r"^\s*ring-offset:\s", r"^\s*ring-offset-color:\s"]:
            assert not re.search(prop, css, re.MULTILINE), f"design-tokens.css contains invalid Tailwind '{prop}' property"


class TestLoginPageFormFields:
    """Login page has expected form structure."""

    def test_login_form_elements(self):
        html = (STATIC_DIR / "login.html").read_text(encoding="utf-8")
        assert 'id="username"' in html, "Missing username input"
        assert 'id="password"' in html, "Missing password input"
        assert 'id="submit-btn"' in html, "Missing submit button"
        assert 'id="mode-toggle"' in html, "Missing register toggle"
        assert 'id="login-error"' in html, "Missing error display"
        assert 'role="alert"' in html, "Error region missing role=alert"


class TestAccessibilityFocusStyles:
    """Focus visible styles must be valid CSS."""

    def test_focus_visible_has_outline(self):
        css = (CSS_DIR / "design-tokens.css").read_text(encoding="utf-8")
        assert "outline:" in css and "outline-offset:" in css, "Focus styles must use outline"

# NOTE: The v3.x "Cognitive Desktop" contract-alignment tests that lived
# here were removed when api/static was restored to the M0 foundation.
# They asserted redesigned-page behaviour (shell modules, raw-response
# envelope handling, canvas graph, service-worker caching). The M0 tests
# above still apply, including the no-browser-microphone guard.
# The v3.x suite is preserved on branch cognitive-desktop-v3.
