import ipaddress
import logging
import os
import re
import socket
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

from core.plugin_system import Plugin

logger = logging.getLogger("Mai.Plugin.WebScraper")

# Cap the raw HTML read at 2 MB so a hostile/huge page cannot exhaust memory
# before text extraction even begins.
MAX_READ_BYTES = 2 * 1024 * 1024

# Only an explicit "read/scrape/fetch/summarize ... <url>" intent triggers a
# network fetch. A bare URL pasted into an unrelated message no longer causes
# an unconditional scrape (old behavior: any message containing a URL).
_INTENT_RE = re.compile(
    r"\b(?:scrape|fetch|read|summarize|browse)\s+"
    r"(?:the\s+|this\s+|that\s+)?(?:page|link|article|url|site)?\s*"
    r"(?:at|from)?\s*:?\s*(?P<target>\S+)",
    re.IGNORECASE,
)


def _private_targets_allowed() -> bool:
    return os.environ.get("MAI_SCRAPER_ALLOW_PRIVATE", "").strip().lower() in (
        "1", "true", "yes"
    )


def _resolves_to_public_ip(url: str) -> bool:
    """True when EVERY resolved address for the host is a globally-routable
    public IP (SSRF guard). Non-public candidates: loopback, private ranges,
    link-local, reserved, multicast, unspecified."""
    host = urlparse(url).hostname
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, OSError, UnicodeError):
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


def require_public_target(url: str) -> None:
    """Refuse private/loopback/link-local destinations (initial request or
    redirect). MAI_SCRAPER_ALLOW_PRIVATE=1 opts a development setup in."""
    if _private_targets_allowed():
        return
    if not _resolves_to_public_ip(url):
        raise urllib.error.URLError(f"Blocked non-public target: {url}")


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block redirects to non-http(s) schemes (file:, ftp:, data: ...) and to
    non-public destinations (SSRF guard)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme.lower() not in ("http", "https"):
            raise urllib.error.URLError(f"Redirect to non-HTTP scheme blocked: {newurl}")
        require_public_target(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._text.append(stripped)

    def text(self, max_chars=2000):
        result = " ".join(self._text)
        return result[:max_chars]


class WebScraperPlugin(Plugin):

    def __init__(self):
        super().__init__(
            name="WebScraperPlugin",
            version="1.0.0",
            description="Fetches and extracts text content from URLs",
        )
        self.max_content = 3000

    def on_load(self, hooks, brain, event_bus):
        hooks.register("pre_chat", self.on_pre_chat, priority=5)
        logger.info("Loaded")

    def on_unload(self):
        logger.info("Unloaded")

    def on_pre_chat(self, user_input, **kwargs):
        text = user_input.strip()
        url = self._extract_url(text)
        if not url:
            return None
        return self._scrape(url)

    def _extract_url(self, text):
        match = _INTENT_RE.search(text)
        if not match:
            return None
        target = match.group("target").strip().rstrip(".,;:!?)\"'")
        scheme = urlparse(target).scheme.lower()
        if target.startswith("//"):
            target = "https:" + target
        elif scheme not in ("http", "https"):
            if scheme:
                # ftp://, file://, data:, etc. are never fetched.
                return None
            # Only URL-shaped bare targets qualify (domain with a dot); bare
            # words like "chrome" or "it" never trigger a fetch.
            if "." not in target:
                return None
            target = "https://" + target
        return target

    def _scrape(self, url):
        try:
            require_public_target(url)
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "MaiAI/1.0 (knowledge assistant)",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            opener = urllib.request.build_opener(_SafeRedirectHandler)
            with opener.open(req, timeout=15) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    return f"Cannot extract text from non-HTML content ({content_type})"
                raw_bytes = resp.read(MAX_READ_BYTES + 1)
            if len(raw_bytes) > MAX_READ_BYTES:
                return f"Page at {url} exceeds the {MAX_READ_BYTES // (1024 * 1024)} MB limit; not downloaded."
            raw = raw_bytes.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return f"HTTP error {e.code} fetching {url}"
        except urllib.error.URLError as e:
            return f"URL error fetching {url}: {e.reason}"
        except Exception as e:
            return f"Failed to fetch {url}: {e}"
        extractor = _TextExtractor()
        try:
            extractor.feed(raw)
        except Exception as e:
            return f"Failed to parse HTML: {e}"
        content = extractor.text(max_chars=self.max_content)
        if not content.strip():
            return f"No readable content found at {url}."
        return f"Content from {url}:\n{content}"
