"""Django middleware adapter for LoggingMixin correlation ID tracking.

Injects correlation IDs into Django requests so that all downstream logging
(views, services, background tasks) can access the correlation ID via
LoggingMixin and get_correlation_id().

Setup:
    MIDDLEWARE = [
        "logging_mixin.adapters.django.CorrelationIdMiddleware",
        # ... other middleware ...
    ]

Behavior:
1. Checks for X-Correlation-ID request header (client-provided or from ALB)
2. If absent, generates a random UUID4 (12 hex chars)
3. Stores in ContextVar so all downstream logging can access it
4. Adds to response X-Correlation-ID header so client can track the request
5. Logs request.start / request.end with correlation_id
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from ..context import clear_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CorrelationIdMiddleware:
    """Django middleware that injects correlation_id from headers or generates UUID.

    Integrates with logging_mixin.context to set the ContextVar that
    LoggingMixin reads in log_* methods.

    Attributes:
        get_response: Django WSGI response callable
    """

    get_response: Callable[[Any], Any]

    def __call__(self, request):
        """Process request, inject correlation ID, clear on response.

        Args:
            request: Django HttpRequest

        Returns:
            Django HttpResponse with X-Correlation-ID header
        """
        # Reset ContextVar at start to ensure clean state for this request
        # (prevents stale values from previous requests in same async context)
        clear_correlation_id()

        # Read X-Correlation-ID header; generate UUID if absent
        correlation_id = request.META.get("HTTP_X_CORRELATION_ID", "").strip()
        if not correlation_id:
            correlation_id = uuid.uuid4().hex[:12]

        # Attach to request object (for direct access)
        request.correlation_id = correlation_id

        # Store in ContextVar (for logging and async tasks)
        set_correlation_id(correlation_id)

        # Log request start
        logger.debug(
            "request.start",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.path,
            },
        )

        # Continue to next middleware/view
        response = self.get_response(request)

        # Add correlation ID to response headers for clients to track
        response["X-Correlation-ID"] = correlation_id

        # Log request end
        logger.debug(
            "request.end",
            extra={
                "correlation_id": correlation_id,
                "status": response.status_code,
            },
        )

        return response
