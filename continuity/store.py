# continuity/store.py
"""Single-document JSON persistence for the Continuity Engine.

One file holds projects, commitments and checkpoints so a write is atomic
across all three. The atomic-write and rollback mechanics live in
:class:`core.atomic_document.AtomicDocument`; this subclass just declares the
document shape.
"""
from __future__ import annotations

from core.atomic_document import AtomicDocument

_DOC_VERSION = 1


def _empty_document() -> dict:
    return {
        "version": _DOC_VERSION,
        "projects": {},
        "commitments": {},
        "checkpoints": {},
    }


class ContinuityStore(AtomicDocument):

    def __init__(self, path):
        super().__init__(path, defaults=_empty_document(), label="Continuity")
