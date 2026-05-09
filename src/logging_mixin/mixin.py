"""LoggingMixin — class-bound logging with auto-injected correlation IDs.

Provides instance methods that auto-inject correlation_id and class context
into log records. Designed to replace module-level loggers in business logic
while maintaining clean, type-safe logging.

Usage:
    from logging_mixin import LoggingMixin

    class FooService(LoggingMixin):
        def do_thing(self) -> None:
            self.log_info("foo.start", item_count=5)
            # → logger name: "module.FooService"
            # → extra: {"correlation_id": "abc123", "item_count": 5}

Composition with PhiAwareMixin (or any mask_for_logging() method):
    from logging_mixin import LoggingMixin
    from some_library import PhiAwareMixin

    class ResponseDTO(LoggingMixin, PhiAwareMixin):
        ...
        def trace(self):
            self.log_debug("fetched")
            # → extra: {"correlation_id": "abc123", "instance": <masked dict>}

Design constraints:
- LoggingMixin's log_* methods are instance methods tied to self._logger.
- They CANNOT be called from @classmethod or @staticmethod (would raise TypeError).
- If a service uses @classmethod, declare module-level logger instead:
    logger = logging.getLogger(__name__)
    # and use logger.* directly, optionally injecting correlation_id manually
- See test_classmethod_constraint.py for detailed examples.
"""

from __future__ import annotations

import logging
from typing import Any

from .context import get_correlation_id


class LoggingMixin:
    """Class-bound logger that auto-injects correlation_id + class context.

    Each instance gets a logger named `<module>.<ClassName>` so monitoring
    systems can group logs by class. Automatically injects the current
    correlation_id (from context) into every log record's `extra` dict.

    Composes naturally with masking mixins: if the instance has a
    `mask_for_logging()` method, its output is added to `extra["instance"]`.

    Instance-only (not callable from @classmethod/@staticmethod):
    The log_* methods read self._logger, which requires self to be bound.
    Calling them from class methods raises:
        TypeError: missing 1 required positional argument: 'self'
    """

    @property
    def _logger(self) -> logging.Logger:
        """Per-class logger named `<module>.<ClassName>`."""
        return logging.getLogger(self.__class__.__module__).getChild(
            self.__class__.__name__
        )

    def _log_extra(self, extra: dict[str, Any]) -> dict[str, Any]:
        """Build the `extra` dict for log records.

        Combines:
        1. correlation_id (from ContextVar, or "-" if not set)
        2. Masked instance representation (if mask_for_logging() exists)
        3. Caller-provided kwargs

        Args:
            extra: Additional fields to include in the log record

        Returns:
            Complete extra dict for log record
        """
        result: dict[str, Any] = {
            "correlation_id": get_correlation_id() or "-",
        }
        # Compose with masking mixin if present
        mask_method = getattr(self, "mask_for_logging", None)
        if callable(mask_method):
            result["instance"] = mask_method()
        if extra:
            result.update(extra)
        return result

    def log_debug(self, event: str, **extra: Any) -> None:
        """Log at DEBUG level with auto-injected context.

        Args:
            event: Log event message
            **extra: Additional fields to include in the log record
        """
        self._logger.debug(event, extra=self._log_extra(extra))

    def log_info(self, event: str, **extra: Any) -> None:
        """Log at INFO level with auto-injected context.

        Args:
            event: Log event message
            **extra: Additional fields to include in the log record
        """
        self._logger.info(event, extra=self._log_extra(extra))

    def log_warning(self, event: str, **extra: Any) -> None:
        """Log at WARNING level with auto-injected context.

        Args:
            event: Log event message
            **extra: Additional fields to include in the log record
        """
        self._logger.warning(event, extra=self._log_extra(extra))

    def log_error(self, event: str, **extra: Any) -> None:
        """Log at ERROR level with auto-injected context.

        Args:
            event: Log event message
            **extra: Additional fields to include in the log record
        """
        self._logger.error(event, extra=self._log_extra(extra))

    def log_exception(self, event: str, **extra: Any) -> None:
        """Log at ERROR level with traceback.

        Use inside `except` blocks to capture the full exception traceback.

        Args:
            event: Log event message
            **extra: Additional fields to include in the log record
        """
        self._logger.exception(event, extra=self._log_extra(extra))
