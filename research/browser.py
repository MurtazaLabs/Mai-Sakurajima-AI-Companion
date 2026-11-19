"""Optional headless-browser fetch path (Playwright).

Zero windows ever: the context is persistent but always ``headless=True``, and
every request is checked against the same public-target guard as the urllib
path. If Playwright or its Chromium build is missing the caller falls back to
``research.fetch.fetch_text``.
"""
from __future__ import annotations

import logging
import urllib.parse
from typing import Any

from core.net_safety import require_public_target
from research.fetch import extract_text

logger = logging.getLogger(__name__)


def playwright_available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except Exception:
        return False


def _route_filter(route):
    """Abort anything that is not a public http(s) subresource."""
    url = route.request.url
    scheme = urllib.parse.urlparse(url).scheme
    if scheme not in ("http", "https"):
        try:
            route.abort()
        except Exception:
            pass
        return
    try:
        require_public_target(url)
        route.continue_()
    except Exception:
        try:
            route.abort()
        except Exception:
            pass


def fetch_with_browser(url: str, timeout: float = 20.0,
                       max_chars: int = 60_000,
                       profile_dir=None) -> dict:
    result = {"url": url, "final_url": url, "title": "", "text": "", "chars": 0,
              "truncated": False, "error": ""}
    try:
        require_public_target(url)
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        result["error"] = f"browser unavailable: {exc}"
        return result

    context = None
    try:
        with sync_playwright() as playwright:
            launch: dict[str, Any] = {"headless": True}
            if profile_dir is not None:
                context = playwright.chromium.launch_persistent_context(
                    str(profile_dir), **launch
                )
            else:
                browser = playwright.chromium.launch(**launch)
                context = browser.new_context()
            page = context.new_page()
            page.route("**/*", _route_filter)
            page.goto(url, timeout=int(timeout * 1000), wait_until="domcontentloaded")
            html = page.content()
            title = page.title()
            final_url = page.url
            require_public_target(final_url)
        _title, text = extract_text(html)
        result.update({
            "final_url": final_url,
            "title": title or _title,
            "text": text[:max_chars],
            "chars": len(text[:max_chars]),
            "truncated": len(text) > max_chars,
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        logger.info("[Research] browser fetch failed %s: %s", url, result["error"])
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
    return result
