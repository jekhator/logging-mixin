"""AWS Lambda adapter for LoggingMixin correlation ID tracking.

Wires Lambda request context to the generic set_correlation_id() function
for use in serverless architectures.

Setup:
    from logging_mixin.adapters.aws_lambda import setup_correlation_id

    def lambda_handler(event, context):
        setup_correlation_id(context)
        # Now LoggingMixin can access correlation_id via get_correlation_id()
        ...

Behavior:
1. Reads X-Correlation-ID from event headers (API Gateway / ALB)
2. Falls back to Lambda context.request_id if no header
3. Sets ContextVar for downstream logging
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..context import clear_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)


def setup_correlation_id(
    event: dict[str, Any],
    context: Any,
    fallback_to_context_id: bool = True,
) -> str:
    """Setup correlation_id from Lambda event + context.

    Reads X-Correlation-ID from event headers (API Gateway, ALB, or direct
    invocation). Falls back to Lambda context.request_id if available.

    Usage:
        from logging_mixin.adapters.aws_lambda import setup_correlation_id

        def lambda_handler(event, context):
            cid = setup_correlation_id(event, context)
            # Now LoggingMixin can access it
            ...

    Args:
        event: Lambda event dict (from API Gateway, ALB, direct invoke, etc.)
        context: Lambda context object (has request_id, function_name, etc.)
        fallback_to_context_id: If True, use context.request_id as fallback
                               (recommended for tracing)

    Returns:
        Correlation ID string that was set
    """
    clear_correlation_id()

    # Try to get from event headers (API Gateway / ALB)
    correlation_id: Optional[str] = None

    if isinstance(event, dict):
        # API Gateway v2 / ALB (headers is a dict)
        headers = event.get("headers", {})
        if isinstance(headers, dict):
            correlation_id = headers.get("x-correlation-id") or headers.get(
                "X-Correlation-ID"
            )

    # Fallback to Lambda context.request_id
    if not correlation_id and fallback_to_context_id:
        correlation_id = getattr(context, "request_id", None)

    # Final fallback to empty string (will be converted to "-" in logs)
    if not correlation_id:
        correlation_id = ""

    set_correlation_id(correlation_id)

    logger.debug(
        "lambda.invoke",
        extra={
            "correlation_id": correlation_id or "-",
            "function": getattr(context, "function_name", "unknown"),
            "request_id": getattr(context, "request_id", "unknown"),
        },
    )

    return correlation_id or "-"
