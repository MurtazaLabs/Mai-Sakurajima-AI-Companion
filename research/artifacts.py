"""Research artifacts — structured Markdown notes written to the vault.

The write is verified by reading the file back and comparing content before the
job may be marked done (the roadmap's "reads them back before reporting").
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_TITLE_CHARS = 90


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (slug[:60] or "research").strip("-")


class ResearchArtifacts:

    def __init__(self, root):
        self.root = Path(root)

    def render(self, job, notes: list[dict]) -> str:
        stamp = time.strftime("%Y-%m-%d", time.localtime(job.created_at or time.time()))
        lines = [
            "---",
            f"title: {job.query[:MAX_TITLE_CHARS]}",
            f"date: {stamp}",
            f"job: {job.id}",
            f"depth: {job.depth}",
            "type: research",
            "sources:",
        ]
        for source in job.sources:
            url = source.get("url", "")
            lines.append(f"  - {url}")
        lines.extend(["---", "", f"# {job.query[:MAX_TITLE_CHARS]}", ""])
        lines.append("## Findings")
        lines.append("")
        if not notes:
            lines.append("_No extractable findings._")
        for note in notes:
            title = (note.get("title") or note.get("url") or "").strip()
            summary = (note.get("summary") or "").strip()
            lines.append(f"### {title[:120]}")
            lines.append("")
            if summary:
                lines.append(summary)
                lines.append("")
            url = note.get("url")
            if url:
                lines.append(f"Source: {url}")
                lines.append("")
        lines.append("## Sources")
        lines.append("")
        for source in job.sources:
            title = source.get("title") or source.get("url", "")
            error = source.get("error")
            suffix = f" — failed: {error}" if error else ""
            lines.append(f"- {title}{suffix}")
        lines.append("")
        return "\n".join(lines)

    def write(self, job, notes: list[dict]) -> tuple[str, str]:
        """Write the artifact and verify the read-back. Returns (path, error)."""
        self.root.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d", time.localtime(job.created_at or time.time()))
        name = f"{stamp}-{_slug(job.query)}-{job.id[-6:]}.md"
        target = self.root / name
        body = self.render(job, notes)
        try:
            target.write_text(body, encoding="utf-8")
            readback = target.read_text(encoding="utf-8")
        except OSError as exc:
            return "", f"artifact write failed: {exc}"
        if readback != body:
            return "", "artifact read-back mismatch"
        return str(target), ""
