"""Memory lifecycle classification — determines whether a node should be
kept in working memory, promoted to long-term, archived, or deleted."""

import logging
import time

from memory.schema import MemoryObject

logger = logging.getLogger(__name__)

SHORT_TERM_TTL = 3600         # 1 hour
LONG_TERM_TTL = 86400         # 24 hours
ARCHIVE_TTL = 604800          # 7 days
DELETE_IMPORTANCE = 0.1
DELETE_AGE_DAYS = 7


class MemoryLifecycle:
    """Classifies MemoryObject nodes by importance and age for pipeline routing."""

    def classify(self, node: MemoryObject) -> str:
        age = time.time() - (node.timestamp or 0)
        if age < SHORT_TERM_TTL:
            return "working"
        if node.importance >= 0.7:
            return "long_term"
        if SHORT_TERM_TTL <= age < LONG_TERM_TTL:
            return "short_term"
        if LONG_TERM_TTL <= age < ARCHIVE_TTL:
            return "archive" if node.importance < 0.3 else "short_term"
        return "archived"

    def should_delete(self, node: MemoryObject) -> bool:
        age_days = (time.time() - (node.timestamp or 0)) / 86400
        return node.importance < DELETE_IMPORTANCE and age_days > DELETE_AGE_DAYS

    def should_archive(self, node: MemoryObject) -> bool:
        age_days = (time.time() - (node.timestamp or 0)) / 86400
        return age_days > 7 and node.importance < 0.3

    def apply_lifecycle(self, nodes):
        """Sort nodes into active, to_archive, to_delete lists."""
        active, to_archive, to_delete = [], [], []
        for node in nodes:
            if self.should_delete(node):
                to_delete.append(node)
            elif self.should_archive(node):
                to_archive.append(node)
            else:
                active.append(node)
        return active, to_archive, to_delete
