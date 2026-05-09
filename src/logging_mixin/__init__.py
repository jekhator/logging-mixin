"""LoggingMixin — class-bound structured logging with auto-injected correlation IDs.

Provides a lightweight mixin for Python services that replaces module-level loggers
with per-class loggers that automatically inject correlation IDs for distributed tracing.

Core components:
    - LoggingMixin: Mixin providing log_debug/info/warning/error/exception methods
    - get_correlation_id(): Retrieve current correlation ID from ContextVar
    - set_correlation_id(): Manually set correlation ID (for tasks, background jobs)
    - Framework adapters: Django middleware, FastAPI dependency, AWS Lambda helper

Example usage:
    from logging_mixin import LoggingMixin, get_correlation_id, set_correlation_id

    class OrderService(LoggingMixin):
        def create_order(self, user_id: int) -> Order:
            self.log_info("order.create", user_id=user_id)
            # Logs with: logger="module.OrderService", extra={"correlation_id": "abc123"}
            ...

    # In a background task:
    def process_order(order_id: int):
        cid = get_correlation_id()  # Inherited from parent request context
        self.log_info("order.process", order_id=order_id)
        ...

Framework adapters (optional, for auto-injection):
    # Django:
    from logging_mixin.adapters.django import CorrelationIdMiddleware
    MIDDLEWARE = ["logging_mixin.adapters.django.CorrelationIdMiddleware", ...]

    # FastAPI:
    from logging_mixin.adapters.fastapi import correlation_id_middleware
    app.add_middleware(correlation_id_middleware)

    # AWS Lambda:
    from logging_mixin.adapters.aws_lambda import setup_correlation_id
    def lambda_handler(event, context):
        setup_correlation_id(event, context)
        ...

Design:
- LoggingMixin provides instance-only methods (cannot be called from @classmethod)
- Correlation ID is stored in a ContextVar (async-safe, cross-thread-safe)
- Each class gets its own logger (module.ClassName) for clean log grouping
- Composes with masking mixins: if mask_for_logging() exists, it's auto-included
"""

from __future__ import annotations

from .context import clear_correlation_id, get_correlation_id, set_correlation_id
from .mixin import LoggingMixin

__all__ = [
    "LoggingMixin",
    "get_correlation_id",
    "set_correlation_id",
    "clear_correlation_id",
]
__version__ = "0.1.0"
