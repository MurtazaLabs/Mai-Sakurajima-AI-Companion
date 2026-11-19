# partner/workspace.py
"""A small sandboxed text workspace for approval-gated file writes.

``create_file`` sits in the approval tier: nothing is written until the user
approves it, and the executor is rebuilt from persisted parameters after a
restart. The sandbox — not a closure — is what keeps the write inside Mai's own
workspace directory, so a restored approval cannot be pointed somewhere else
later.
"""
from __future__ import annotations

import logging
from pathlib import Path, PureWindowsPath

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 4000
MAX_PATH_CHARS = 200


class PartnerWorkspace:
    """Relative-path-only text files under one root directory."""

    def __init__(self, root):
        self.root = Path(root)

    def resolve(self, relative) -> tuple[Path | None, str]:
        """Map a user-supplied name into the sandbox, or refuse it."""
        name = str(relative or "").strip().replace("\\", "/")
        if not name:
            return None, "path required"
        if len(name) > MAX_PATH_CHARS:
            return None, "path too long"
        if "\x00" in name:
            return None, "invalid path"
        candidate = Path(name)
        # ``anchor`` catches POSIX-absolute, UNC and Windows root-relative
        # ("\\etc\\passwd") forms; ``PureWindowsPath`` also catches drive-letter
        # paths ("C:/Windows/x.md") on POSIX, where Path() reads them as a plain
        # relative name.
        if candidate.anchor or PureWindowsPath(name).drive:
            return None, "absolute paths are refused"
        parts = [part for part in candidate.parts if part not in ("", ".")]
        if not parts:
            return None, "path required"
        if any(part == ".." for part in parts):
            return None, "path traversal is refused"
        target = self.root.joinpath(*parts)
        try:
            root = self.root.resolve()
            resolved = target.resolve()
        except OSError:
            return None, "invalid path"
        if resolved != root and not resolved.is_relative_to(root):
            return None, "path escapes the workspace"
        return target, ""

    def write(self, relative, content) -> dict:
        target, error = self.resolve(relative)
        if target is None:
            raise ValueError(error)
        text = "" if content is None else str(content)
        if len(text) > MAX_CONTENT_CHARS:
            raise ValueError(f"content too large (max {MAX_CONTENT_CHARS} chars)")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return {
            "path": target.relative_to(self.root).as_posix(),
            "chars": len(text),
            "bytes": target.stat().st_size,
        }

    def exists(self, relative) -> bool:
        target, _error = self.resolve(relative)
        return bool(target and target.is_file())

    def stats(self) -> dict:
        files = 0
        if self.root.exists():
            try:
                files = sum(1 for path in self.root.rglob("*") if path.is_file())
            except OSError as exc:
                logger.warning("[Workspace] stats failed: %s", exc)
        return {"root": str(self.root), "files": files}


__all__ = ["MAX_CONTENT_CHARS", "MAX_PATH_CHARS", "PartnerWorkspace"]
