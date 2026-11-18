"""SSRF-guarded HTTP text extraction (no browser, no new dependencies)."""
from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser

from core.net_safety import require_public_target

logger = logging.getLogger(__name__)

USER_AGENT = "MaiResearch/1.0 (+local research assistant)"
MAX_BYTES = 2 * 1024 * 1024
MAX_TEXT_CHARS = 60_000

_SKIP_TAGS = {
    "script", "style", "noscript", "svg", "nav", "header", "footer", "aside",
    "form", "iframe", "template",
}
_BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "section", "article", "h1", "h2", "h3",
    "h4", "h5", "h6", "blockquote", "pre",
}


def _ssl_context():
    """Use certifi's CA bundle (the Windows store is not visible to Python)."""
    try:
        import ssl

        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        import ssl
        return ssl.create_default_context()


def build_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        _GuardedRedirectHandler(),
        urllib.request.HTTPSHandler(context=_ssl_context()),
    )


class _GuardedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate every redirect hop against the public-target guard."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require_public_target(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _ArticleExtractor(HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._article_depth = 0
        self._in_title = False
        self._title: list[str] = []
        self._all: list[str] = []
        self._main: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
            return
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag in ("article", "main"):
            self._article_depth += 1
        if tag in _BLOCK_TAGS:
            self._push("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
            return
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in ("article", "main"):
            self._article_depth = max(0, self._article_depth - 1)
        if tag in _BLOCK_TAGS:
            self._push("\n")

    def handle_data(self, data):
        text = re.sub(r"\s+", " ", data or "").strip()
        if not text:
            return
        if self._in_title:
            self._title.append(text)
            return
        if self._skip_depth:
            return
        self._push(text + " ")

    def _push(self, text):
        self._all.append(text)
        if self._article_depth:
            self._main.append(text)

    def result(self) -> tuple[str, str]:
        title = re.sub(r"\s+", " ", " ".join(self._title)).strip()
        main = "".join(self._main).strip()
        body = main if len(main) >= 200 else "".join(self._all)
        body = re.sub(r"[ \t]+", " ", body)
        body = re.sub(r"\n\s*\n+", "\n\n", body).strip()
        return title, body


def extract_text(html: str) -> tuple[str, str]:
    parser = _ArticleExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # malformed HTML is common; return what we have
        logger.debug("[Research] HTML parse stopped early: %s", exc)
    return parser.result()


def fetch_text(url: str, timeout: float = 15.0, max_chars: int = MAX_TEXT_CHARS) -> dict:
    """Fetch one public URL and return extracted text. Never raises."""
    result = {"url": url, "final_url": url, "title": "", "text": "", "chars": 0,
              "truncated": False, "error": ""}
    try:
        require_public_target(url)
        opener = build_opener()
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8",
        })
        with opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
            require_public_target(final_url)
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(MAX_BYTES + 1)
            truncated = len(raw) > MAX_BYTES
            if truncated:
                raw = raw[:MAX_BYTES]
            html = raw.decode(charset, errors="replace")
            content_type = (response.headers.get("Content-Type") or "").lower()
        result["final_url"] = final_url
        if "html" not in content_type and "<html" not in html[:2000].lower():
            text = html.strip()
            title = ""
        else:
            title, text = extract_text(html)
        result["title"] = title
        result["text"] = text[:max_chars]
        result["chars"] = len(result["text"])
        result["truncated"] = truncated or len(text) > max_chars
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        logger.info("[Research] fetch failed %s: %s", url, result["error"])
    return result
