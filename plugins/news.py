import logging
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from core.plugin_system import Plugin

logger = logging.getLogger("Mai.Plugin.News")


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._text = []

    def handle_data(self, data):
        self._text.append(data)

    def text(self):
        return " ".join(self._text)


class NewsPlugin(Plugin):

    FEEDS = [
        ("techcrunch", "https://feeds.feedburner.com/TechCrunch/"),
        ("hackernews", "https://hnrss.org/frontpage"),
        ("bbc", "https://feeds.bbci.co.uk/news/rss.xml"),
    ]

    def __init__(self):
        super().__init__(
            name="NewsPlugin",
            version="1.0.0",
            description="RSS/Atom feed reader for recent headlines",
        )

    def on_load(self, hooks, brain, event_bus):
        hooks.register("pre_chat", self.on_pre_chat, priority=5)
        logger.info("Loaded (%d feeds)", len(self.FEEDS))

    def on_unload(self):
        logger.info("Unloaded")

    def on_pre_chat(self, user_input, **kwargs):
        text = user_input.lower().strip()
        match = re.match(r"news\s*(.+)?", text)
        if not match:
            return None
        feed_name = match.group(1)
        if feed_name:
            feed_name = feed_name.strip().lower()
            url = dict(self.FEEDS).get(feed_name)
            if not url:
                available = ", ".join(n for n, _ in self.FEEDS)
                return f"Unknown feed '{feed_name}'. Available: {available}"
            return self._fetch_feed(url, feed_name)
        results = []
        for name, url in self.FEEDS:
            items = self._fetch_feed_items(url, limit=2)
            for item in items:
                results.append(f"[{name}] {item}")
        if not results:
            return "No news items could be fetched."
        return "\n".join(results[:6])

    def _fetch_feed(self, url, name):
        items = self._fetch_feed_items(url, limit=5)
        if not items:
            return f"No items from {name}."
        lines = [f"--- {name} ---"]
        lines.extend(items)
        return "\n".join(lines)

    def _fetch_feed_items(self, url, limit=5):
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                raw = resp.read()
        except Exception as e:
            logger.warning("Feed fetch failed for %s: %s", url, e)
            return []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return []
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = []
        for entry in root.iter("item"):
            title_el = entry.find("title")
            link_el = entry.find("link")
            if title_el is not None:
                title = _strip_html(title_el.text or "")
                link = link_el.text if link_el is not None else ""
                items.append(f"{title} — {link}" if link else title)
                if len(items) >= limit:
                    break
        if not items:
            for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
                title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                title = _strip_html(title_el.text or "") if title_el is not None else ""
                link = link_el.get("href", "") if link_el is not None else ""
                items.append(f"{title} — {link}" if link else title)
                if len(items) >= limit:
                    break
        return items


def _strip_html(text):
    extractor = _TextExtractor()
    extractor.feed(text)
    return extractor.text().strip()
