"""Correlation ID context management — framework-neutral ContextVar utilities.

Provides low-level get/set helpers for correlation ID tracking across async
boundaries without depending on any specific web framework.

Usage:
    from logging_mixin.context import set_correlation_id, get_correlation_id

    # In a request handler (manually set):
    set_correlation_id("request-uuid-1234")

    # In a background task:
    cid = get_correlation_id()  # → "request-uuid-1234"

    # In an async context:
    async def async_handler():
        cid = get_correlation_id()  # → inherits from parent context
"""

from __future__ import annotations

import contextvars
from typing import Optional

# ContextVar to store correlation_id across async boundaries
_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def get_correlation_id() -> Optional[str]:
    """Returns the current correlation_id, or None if not set.

    Safe to call in any context:
    - HTTP request handlers (set by framework middleware adapter)
    - Background tasks (inherited via ContextVar across task boundaries)
    - Sync functions called from async code
    - Standalone scripts or tests

    Returns:
        Correlation ID string if set, None otherwise.
        Callers should treat None as "no active correlation" and use a fallback
        (typically "-" in logs).

    Example:
        from logging_mixin.context import get_correlation_id
        cid = get_correlation_id()
        logger.info("Processing", extra={"correlation_id": cid or "-"})
    """
    value = _correlation_id_var.get("")
    return value if value else None


def set_correlation_id(value: Optional[str]) -> None:
    """Explicitly set the correlation_id for code outside the request lifecycle.

    Useful for:
    - Celery tasks that need to inherit the original request's correlation_id
    - Background jobs spawned from async handlers
    - Manual test isolation
    - Cross-service tracing (forward correlation ID from client header)

    Args:
        value: Correlation ID string (e.g., UUID, opaque identifier) or None to clear.

    Example:
        from logging_mixin.context import set_correlation_id
        set_correlation_id("abc123def456")
        # Now any logging in this context will include this correlation_id
    """
    _correlation_id_var.set(value or "")


def clear_correlation_id() -> None:
    """Clear the current correlation_id.

    Resets the ContextVar to its default (empty string). Useful for
    test isolation or explicit cleanup between requests in same-process contexts.

    Example:
        from logging_mixin.context import clear_correlation_id
        clear_correlation_id()  # Safe to call even if not set
    """
    _correlation_id_var.set("")
