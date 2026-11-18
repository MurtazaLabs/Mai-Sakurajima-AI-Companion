"""Sandboxed file tools — one policy for the LLM surface and the executor.

The workspace root is the only place Mai writes autonomously. Reads may also
reach the vault (research artifacts). Nothing here touches the network; path
resolution refuses absolute paths outside the configured roots, ``..``
traversal and NUL bytes, and every method returns a plain dict so tool handlers
never need to translate exceptions.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_READ_CHARS = 200_000
MAX_WRITE_CHARS = 20_000
MAX_ENTRIES = 200
MAX_PATH_CHARS = 300

_BAD_NAME = re.compile(r"[\x00-\x1f]")


class FileTools:

    def __init__(self, workspace_root, extra_read_roots=()):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self._read_roots = [self.workspace_root] + [Path(p) for p in extra_read_roots]
        self._write_roots = [self.workspace_root]

    # -- path policy --------------------------------------------------

    def _under(self, target: Path, roots) -> bool:
        try:
            resolved = target.resolve()
        except (OSError, RuntimeError):
            return False
        for root in roots:
            try:
                resolved.relative_to(Path(root).resolve())
                return True
            except (ValueError, OSError):
                continue
        return False

    def resolve(self, path) -> tuple[Path | None, str]:
        raw = str(path or "").strip()
        if not raw:
            return None, "path required"
        if len(raw) > MAX_PATH_CHARS:
            return None, "path too long"
        if _BAD_NAME.search(raw):
            return None, "invalid path"
        candidate = Path(raw)
        if candidate.is_absolute():
            target = candidate
        else:
            if ".." in candidate.parts:
                return None, "path traversal is refused"
            target = self.workspace_root.joinpath(*candidate.parts)
        if not self._under(target, self._read_roots):
            return None, "outside the file sandbox"
        return target, ""

    def in_sandbox(self, path) -> bool:
        target, error = self.resolve(path)
        return bool(target is not None and not error)

    def writable(self, path) -> bool:
        target, error = self.resolve(path)
        if target is None or error:
            return False
        return self._under(target, self._write_roots)

    # -- operations ---------------------------------------------------

    def read(self, path, max_chars=MAX_READ_CHARS) -> dict:
        target, error = self.resolve(path)
        if target is None:
            return {"ok": False, "error": error, "path": str(path)}
        if not target.is_file():
            return {"ok": False, "error": "not_a_file", "path": str(path)}
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"ok": False, "error": str(exc), "path": str(path)}
        limit = max(1, min(int(max_chars or MAX_READ_CHARS), MAX_READ_CHARS))
        truncated = len(text) > limit
        return {
            "ok": True,
            "path": str(target),
            "text": text[:limit],
            "chars": min(len(text), limit),
            "truncated": truncated,
        }

    def list(self, path="", limit=MAX_ENTRIES) -> dict:
        target, error = self.resolve(path or ".")
        if target is None:
            return {"ok": False, "error": error, "path": str(path)}
        if not target.is_dir():
            return {"ok": False, "error": "not_a_directory", "path": str(path)}
        limit = max(1, min(int(limit or MAX_ENTRIES), MAX_ENTRIES))
        entries = []
        try:
            for child in sorted(target.iterdir())[:limit]:
                if child.name.startswith(".git"):
                    continue
                try:
                    entries.append({
                        "name": child.name,
                        "type": "dir" if child.is_dir() else "file",
                        "size": child.stat().st_size if child.is_file() else 0,
                    })
                except OSError:
                    continue
        except OSError as exc:
            return {"ok": False, "error": str(exc), "path": str(path)}
        return {"ok": True, "path": str(target), "entries": entries, "count": len(entries)}

    def write(self, path, content, overwrite=True) -> dict:
        target, error = self.resolve(path)
        if target is None:
            return {"ok": False, "error": error, "path": str(path)}
        if not self.writable(path):
            return {"ok": False, "error": "write outside workspace", "path": str(path)}
        text = "" if content is None else str(content)
        if len(text) > MAX_WRITE_CHARS:
            return {"ok": False, "error": "content too large", "path": str(path)}
        if target.exists() and not overwrite:
            return {"ok": False, "error": "file_exists", "path": str(path)}
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "error": str(exc), "path": str(path)}
        return {"ok": True, "path": str(target), "chars": len(text)}

    def create(self, path, content) -> dict:
        return self.write(path, content, overwrite=False)

    def stats(self) -> dict:
        files = 0
        try:
            files = sum(1 for p in self.workspace_root.rglob("*") if p.is_file())
        except OSError:
            files = 0
        return {"workspace": str(self.workspace_root), "files": files}
