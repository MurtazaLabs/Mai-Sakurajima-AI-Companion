# self_awareness/code_index.py
"""Own-code index — the repository, read the way she reads a knowledge base.

The index is deliberately structural, not semantic: modules, classes,
functions, imports, docstrings, sizes and hashes parsed with ``ast``. That is
enough to answer "where does my STT load a model?" and to notice "this module
no longer parses", without pretending to understand the code.

Read-only: ``refresh`` writes only the index document; ``read_module`` reads
source and never edits it.
"""
from __future__ import annotations

import ast
import hashlib
import logging
import time
from pathlib import Path

from core.atomic_document import AtomicDocument

logger = logging.getLogger(__name__)

_DOCUMENT_DEFAULTS = {"version": 1, "built_at": 0.0, "files": {}}
_SKIP_SUFFIXES = (".pyc",)


class OwnCodeIndex:

    def __init__(self, root=None, store_path=None, excludes=None, max_modules=4000):
        self.root = Path(root or ".")
        self.excludes = frozenset(str(name) for name in (excludes or ()))
        self.max_modules = max(1, int(max_modules))
        store_path = store_path or (self.root / "data" / "self_awareness" / "code_index.json")
        self.store = AtomicDocument(
            store_path, defaults=_DOCUMENT_DEFAULTS, label="SelfIndex",
        )

    # -- scanning ----------------------------------------------------

    def _excluded(self, relative: Path) -> bool:
        return any(part in self.excludes for part in relative.parts[:-1])

    def scan(self) -> list[Path]:
        files = []
        try:
            for path in self.root.rglob("*.py"):
                try:
                    relative = path.relative_to(self.root)
                except ValueError:
                    continue
                if path.suffix in _SKIP_SUFFIXES or self._excluded(relative):
                    continue
                files.append(path)
        except OSError as exc:
            logger.warning("[SelfIndex] scan failed under %s: %s", self.root, exc)
            return []
        files.sort(key=lambda item: item.relative_to(self.root).as_posix())
        return files[: self.max_modules]

    # -- parsing -----------------------------------------------------

    @staticmethod
    def _module_name(relative: str) -> str:
        parts = relative[:-3].split("/") if relative.endswith(".py") else []
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(part for part in parts if part) or relative

    @staticmethod
    def _first_line(text: str) -> str:
        for line in (text or "").splitlines():
            stripped = line.strip()
            if stripped:
                return stripped[:200]
        return ""

    def _describe(self, path: Path, relative: str, stat) -> dict:
        entry = {
            "path": relative,
            "module": self._module_name(relative),
            "lines": 0,
            "size": stat.st_size,
            "mtime": round(stat.st_mtime, 3),
            "sha256": "",
            "classes": [],
            "functions": [],
            "imports": [],
            "docstring": "",
        }
        try:
            # utf-8-sig strips a BOM: a BOM is not a syntax error, and ast.parse
            # rejects it as an invalid character if it survives.
            source = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            entry["error"] = f"unreadable: {exc}"
            return entry
        entry["lines"] = source.count("\n") + (1 if source else 0)
        entry["sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            entry["error"] = f"syntax error at line {exc.lineno}: {exc.msg}"
            return entry
        entry["docstring"] = self._first_line(ast.get_docstring(tree, clean=True) or "")
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                entry["classes"].append(node.name)
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        entry["functions"].append(f"{node.name}.{child.name}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                entry["functions"].append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    entry["imports"].append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and not node.level:
                    entry["imports"].append(node.module.split(".")[0])
        entry["imports"] = sorted(set(entry["imports"]))
        return entry

    # -- refresh -----------------------------------------------------

    def refresh(self, force: bool = False) -> dict:
        started = time.perf_counter()
        stored = self.store.read().get("files") or {}
        files: dict[str, dict] = {}
        changed = added = removed = 0
        for path in self.scan():
            relative = path.relative_to(self.root).as_posix()
            try:
                stat = path.stat()
            except OSError as exc:
                logger.debug("[SelfIndex] stat failed for %s: %s", relative, exc)
                continue
            previous = stored.get(relative)
            if (
                not force
                and previous
                and previous.get("mtime") == round(stat.st_mtime, 3)
                and previous.get("size") == stat.st_size
            ):
                files[relative] = previous
                continue
            files[relative] = self._describe(path, relative, stat)
            if previous is None:
                added += 1
            else:
                changed += 1
        removed = sum(1 for relative in stored if relative not in files)

        with self.store.transaction() as document:
            document["files"] = files
            document["built_at"] = time.time()

        parse_errors = sorted(rel for rel, entry in files.items() if entry.get("error"))
        summary = {
            "modules": len(files),
            "added": added,
            "changed": changed,
            "removed": removed,
            "parse_errors": len(parse_errors),
            "duration": round(time.perf_counter() - started, 3),
            "built_at": time.time(),
        }
        logger.info(
            "[SelfIndex] %d modules (%d new, %d changed, %d removed, %d unparsed) in %.2fs",
            summary["modules"], added, changed, removed, len(parse_errors), summary["duration"],
        )
        return summary

    # -- queries -----------------------------------------------------

    def entries(self) -> dict[str, dict]:
        return dict(self.store.read().get("files") or {})

    def stats(self) -> dict:
        document = self.store.read()
        files = document.get("files") or {}
        parse_errors = {
            relative: entry.get("error")
            for relative, entry in files.items()
            if entry.get("error")
        }
        stale = 0
        for relative, entry in files.items():
            try:
                stat = (self.root / relative).stat()
            except OSError:
                stale += 1
                continue
            if entry.get("mtime") != round(stat.st_mtime, 3) or entry.get("size") != stat.st_size:
                stale += 1
        return {
            "modules": len(files),
            "lines": sum(int(entry.get("lines") or 0) for entry in files.values()),
            "built_at": document.get("built_at", 0.0),
            "parse_errors": parse_errors,
            "stale": stale,
            "root": str(self.root),
        }

    def search(self, query: str, limit: int = 10) -> list[dict]:
        text = str(query or "").strip().lower()
        if not text:
            return []
        hits = []
        for relative, entry in self.entries().items():
            score, match = 0, ""
            for name in entry.get("classes", []) + entry.get("functions", []):
                lowered = str(name).lower()
                if lowered == text:
                    score, match = 4, name
                elif lowered.startswith(text) and score < 3:
                    score, match = 3, name
                elif text in lowered and score < 2:
                    score, match = 2, name
            if text in str(entry.get("module", "")).lower() and score < 2:
                score, match = 2, entry["module"]
            if text in str(entry.get("docstring", "")).lower() and score < 1:
                score, match = 1, entry.get("docstring", "")[:120]
            if text in relative.lower() and score < 1:
                score, match = 1, relative
            if score:
                hits.append({
                    "path": relative,
                    "module": entry.get("module", ""),
                    "score": score,
                    "match": match,
                    "docstring": entry.get("docstring", ""),
                    "error": entry.get("error", ""),
                })
        hits.sort(key=lambda item: (-item["score"], item["path"]))
        return hits[: max(1, int(limit))]

    def resolve_source(self, name: str) -> tuple[Path | None, str]:
        text = str(name or "").strip()
        if not text:
            return None, "a module name or path is required"
        entries = self.entries()
        relative = ""
        if text in entries:
            relative = text
        else:
            for source_path, entry in entries.items():
                if entry.get("module") == text:
                    relative = source_path
                    break
        if not relative:
            looks_like_path = text.endswith(".py") or "/" in text or "\\" in text
            if looks_like_path:
                if not text.endswith(".py"):
                    return None, "only Python sources can be read"
                relative = text
            else:
                literal = Path(text)
                if literal.suffix and literal.suffix != ".py" and (self.root / literal).is_file():
                    return None, "only Python sources can be read"
                relative = text.replace(".", "/") + ".py"
        candidate = Path(relative)
        if candidate.is_absolute() or candidate.anchor:
            return None, "absolute paths are refused"
        if any(part == ".." for part in candidate.parts):
            return None, "path traversal is refused"
        if candidate.suffix != ".py":
            return None, "only Python sources can be read"
        target = (self.root / candidate)
        try:
            resolved = target.resolve()
            root = self.root.resolve()
        except OSError:
            return None, "invalid path"
        if resolved != root and not resolved.is_relative_to(root):
            return None, "path escapes the project root"
        if not target.is_file():
            return None, f"no such module: {relative}"
        return target, ""

    def read_module(self, name: str, max_lines: int = 400) -> dict:
        target, error = self.resolve_source(name)
        if target is None:
            return {"error": error}
        try:
            source = target.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as exc:
            return {"error": f"unreadable: {exc}"}
        lines = source.splitlines()
        limit = max(1, min(int(max_lines or 400), 2000))
        return {
            "path": target.relative_to(self.root).as_posix(),
            "module": self._module_name(target.relative_to(self.root).as_posix()),
            "lines": len(lines),
            "returned": min(len(lines), limit),
            "truncated": len(lines) > limit,
            "content": "\n".join(lines[:limit]),
        }


__all__ = ["OwnCodeIndex"]
