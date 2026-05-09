"""Framework adapters for LoggingMixin correlation ID context.

Each adapter wires framework-specific lifecycle events to the generic
set_correlation_id / get_correlation_id helpers in logging_mixin.context.

Provides optional import paths to avoid hard dependencies on frameworks:
    from logging_mixin.adapters.django import CorrelationIdMiddleware
    from logging_mixin.adapters.fastapi import correlation_id_dependency
    from logging_mixin.adapters.aws_lambda import setup_correlation_id
"""
