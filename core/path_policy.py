# core/path_policy.py
"""Cross-platform path policy shared by the sandboxed file surfaces.

``Path(name).is_absolute()`` only recognises the host platform's own form, so a
``C:/Windows/x.md`` name looks like a plain relative name to a POSIX sandbox and
would be written *inside* the sandbox under a ``C:`` directory. The reflector's
own-code index, the partner workspace and the file tools all refuse absolute
names, so they all ask the same question here.
"""
from __future__ import annotations

from pathlib import Path, PureWindowsPath


def is_absolute_path(name: str) -> bool:
    """True for POSIX-absolute, UNC, Windows root-relative and drive-letter names."""
    candidate = Path(name)
    return bool(candidate.is_absolute() or candidate.anchor or PureWindowsPath(name).drive)


__all__ = ["is_absolute_path"]
