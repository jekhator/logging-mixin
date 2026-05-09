"""FastAPI dependency adapter for LoggingMixin correlation ID tracking.

Wires FastAPI request lifecycle to the generic set_correlation_id() function
so that LoggingMixin can access the correlation_id via get_correlation_id().

Setup (middleware approach):
    from fastapi import FastAPI
    from logging_mixin.adapters.fastapi import correlation_id_middleware

    app = FastAPI()
    app.add_middleware(correlation_id_middleware)

Or (dependency approach):
    from fastapi import Depends
    from logging_mixin.adapters.fastapi import correlation_id_dependency

    @app.get("/items/")
    def get_items(cid: str = Depends(correlation_id_dependency)):
        # cid is set in ContextVar; LoggingMixin can access it
        ...

Both approaches work. The middleware is simpler (automatic for all routes);
the dependency is more explicit and composable.
"""

from __future__ import annotations

import logging
import uuid
from typing import Callable

from fastapi import Request

from ..context import clear_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)


async def correlation_id_dependency(request: Request) -> str:
    """FastAPI dependency that sets correlation_id from request header.

    Use in route handlers via:
        @app.get("/items/")
        def get_items(cid: str = Depends(correlation_id_dependency)):
            ...

    Args:
        request: FastAPI Request object

    Returns:
        Correlation ID string (for dependency injection)
    """
    clear_correlation_id()

    # Read X-Correlation-ID header; generate UUID if absent
    correlation_id = request.headers.get("X-Correlation-ID", "").strip()
    if not correlation_id:
        correlation_id = uuid.uuid4().hex[:12]

    # Store in ContextVar (for logging and async tasks)
    set_correlation_id(correlation_id)

    logger.debug(
        "request.start",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
        },
    )

    return correlation_id


def correlation_id_middleware(app) -> Callable:
    """FastAPI middleware factory that sets correlation_id from request header.

    Usage:
        from fastapi import FastAPI
        from logging_mixin.adapters.fastapi import correlation_id_middleware

        app = FastAPI()
        app.add_middleware(correlation_id_middleware)

    Args:
        app: FastAPI application

    Returns:
        Middleware callable
    """

    async def middleware(request: Request, call_next):
        """ASGI middleware that injects correlation_id.

        Args:
            request: FastAPI Request
            call_next: Next middleware/handler callable

        Returns:
            Response with X-Correlation-ID header
        """
        clear_correlation_id()

        # Read X-Correlation-ID header; generate UUID if absent
        correlation_id = request.headers.get("X-Correlation-ID", "").strip()
        if not correlation_id:
            correlation_id = uuid.uuid4().hex[:12]

        # Store in ContextVar
        set_correlation_id(correlation_id)

        logger.debug(
            "request.start",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        # Continue to next handler
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        logger.debug(
            "request.end",
            extra={
                "correlation_id": correlation_id,
                "status": response.status_code,
            },
        )

        return response

    return middleware
