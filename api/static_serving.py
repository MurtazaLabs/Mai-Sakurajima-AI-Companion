"""Static HTML page serving for the Mai web UI.

Reads page HTML from ``api/static`` and renders it, or returns a fallback
error page when a page is missing. Used by ``api.server`` to mount the
dashboard routes.
"""
import os
import logging
from fastapi.responses import HTMLResponse

logger = logging.getLogger("api.server")

static_dir = os.path.join(os.path.dirname(__file__), "static")


def read_static_html(filename):
    """Read an HTML file from the static directory."""
    if not os.path.isdir(static_dir):
        return None
    p = os.path.join(static_dir, filename)
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return f.read()
    return None


def make_html_response(page_name):
    """Return HTMLResponse for a page, or a fallback error page."""
    html = read_static_html(f"{page_name}.html")
    if html:
        return HTMLResponse(html)
    return HTMLResponse(
        f"<html><body style='background:#090B10;color:#70798C;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;gap:8px'>"
        f"<h1 style='color:#4FA7FF;font-size:24px'>🔭</h1>"
        f"<p>Page '{page_name}' not found</p>"
        f"<a href='/' style='color:#4FA7FF;text-decoration:none;font-size:13px'>← Back to Desktop</a>"
        f"</body></html>"
    )
