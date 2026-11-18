"""Best-effort HTML search (DuckDuckGo endpoint, no API key).

Only used to turn a query into candidate URLs. Job execution never depends on
it: URL-seeded jobs bypass search, and a search outage becomes an honest job
failure rather than a fabricated report.
"""
from __future__ import annotations

import logging
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from core.net_safety import require_public_target
from research.fetch import USER_AGENT, build_opener

logger = logging.getLogger(__name__)


class _ResultParser(HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._anchor_href = ""
        self._in_result = False
        self._text: list[str] = []
        self.results: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if "result__a" in classes:
            self._anchor_href = attrs.get("href") or ""
            self._in_result = True
            self._text = []

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._in_result:
            self._in_result = False
            title = " ".join("".join(self._text).split())
            url = _resolve_href(self._anchor_href)
            if url and title:
                self.results.append({"title": title, "url": url})
            self._anchor_href = ""

    def handle_data(self, data):
        if self._in_result:
            self._text.append(data)


def _resolve_href(href: str) -> str:
    href = (href or "").strip()
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    if "duckduckgo.com" in parsed.netloc:
        target = urllib.parse.parse_qs(parsed.query).get("uddg")
        if target:
            href = urllib.parse.unquote(target[0])
    return href if href.startswith(("http://", "https://")) else ""


def search_web(query: str, limit: int = 5, endpoint: str = "https://html.duckduckgo.com/html/",
               timeout: float = 15.0) -> dict:
    """Return {"results": [{title,url}], "error": ""}."""
    query = (query or "").strip()
    if not query:
        return {"results": [], "error": "empty query"}
    try:
        require_public_target(endpoint)
        url = endpoint + "?" + urllib.parse.urlencode({"q": query})
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html",
        })
        with build_opener().open(request, timeout=timeout) as response:
            html = response.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
        parser = _ResultParser()
        parser.feed(html)
        parser.close()
        seen = set()
        results = []
        for result in parser.results:
            if result["url"] in seen:
                continue
            seen.add(result["url"])
            results.append(result)
            if len(results) >= max(1, int(limit)):
                break
        return {"results": results, "error": "" if results else "no results"}
    except Exception as exc:
        logger.info("[Research] search failed: %s", exc)
        return {"results": [], "error": f"{type(exc).__name__}: {exc}"}
