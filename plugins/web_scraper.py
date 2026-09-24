import logging
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser

from core.plugin_system import Plugin

logger = logging.getLogger("Mai.Plugin.WebScraper")


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
        match = re.search(r"https?://[^\s]+", text)
        if match:
            return match.group(0)
        match = re.match(r"scrape\s+(.+)", text, re.IGNORECASE)
        if match:
            url = match.group(1).strip()
            if not url.startswith("http"):
                url = "https://" + url
            return url
        return None

    def _scrape(self, url):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "MaiAI/1.0 (knowledge assistant)",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    return f"Cannot extract text from non-HTML content ({content_type})"
                raw = resp.read().decode("utf-8", errors="replace")
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
