"""Client-safe error helpers for the Mai API.

Exceptions raised inside route handlers must never leak backend details
(paths, provider names, stack traces) to API clients (S-5).  ``safe_error``
logs the real exception server-side and returns a stable generic message.
"""

import logging

logger = logging.getLogger("api.errors")


def safe_error(e: Exception, context: str = "") -> str:
    """Log the underlying exception, return a client-safe generic message."""
    if context:
        logger.error("[API] %s: %r", context, e)
    else:
        logger.error("[API] error: %r", e)
    return "internal_error"
