"""Tests for @classmethod constraint on LoggingMixin.

LoggingMixin's log_* methods are instance methods bound to self._logger.
They CANNOT be called from @classmethod or @staticmethod because those
don't receive self. This test suite verifies the constraint and documents
the workaround: use module-level logger + manual correlation ID injection.

Design note (VIO-89 ASK 2b learning context):
- LoggingMixin provides log_debug/info/warning/error/exception as INSTANCE METHODS
- @classmethod and @staticmethod don't have self, so they can't call these methods
- Attempting to call them raises TypeError: missing 1 required positional argument 'self'
- Services that need @classmethod should declare module-level logger instead
"""

import logging
from unittest.mock import patch

import pytest

from logging_mixin import LoggingMixin, get_correlation_id, set_correlation_id


class ServiceWithClassMethod(LoggingMixin):
    """Service that attempts to use @classmethod with LoggingMixin."""

    @classmethod
    def bad_classmethod(cls):
        """This will fail if called with self.log_info()."""
        # Cannot use self.log_info() here — it raises TypeError
        # Trying to call an instance method from a classmethod without an instance
        cls.log_info("test")  # type: ignore

    @staticmethod
    def bad_staticmethod():
        """This will fail if called with self.log_info()."""
        # Cannot use self.log_info() in a staticmethod — no self available
        ServiceWithClassMethod.log_info("test")  # type: ignore


# Module-level logger (the workaround)
logger = logging.getLogger(__name__)


class ServiceWithModuleLogger(LoggingMixin):
    """Service that correctly uses @classmethod with module-level logger."""

    @classmethod
    def good_classmethod(cls):
        """Use module-level logger for class methods."""
        cid = get_correlation_id()
        logger.info("classmethod.event", extra={"correlation_id": cid or "-"})


class TestClassMethodConstraint:
    """Verify @classmethod incompatibility and document workaround."""

    def test_classmethod_cannot_call_log_info(self):
        """Calling self.log_info() from @classmethod raises TypeError."""
        with pytest.raises(TypeError, match="missing 1 required positional argument"):
            # This will fail because we're trying to call an unbound method
            ServiceWithClassMethod.bad_classmethod()

    def test_staticmethod_cannot_call_log_info(self):
        """Calling self.log_info() from @staticmethod raises TypeError."""
        with pytest.raises(TypeError, match="missing 1 required positional argument"):
            # This will fail because @staticmethod has no self or cls
            ServiceWithClassMethod.bad_staticmethod()

    def test_classmethod_with_module_logger_works(self, caplog):
        """Module-level logger in @classmethod works fine."""
        set_correlation_id("cid-123")

        with caplog.at_level(logging.INFO):
            ServiceWithModuleLogger.good_classmethod()

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.correlation_id == "cid-123"

    def test_manual_correlation_id_injection_in_classmethod(self, caplog):
        """@classmethod can manually inject correlation_id using get_correlation_id()."""
        set_correlation_id("manual-456")

        with caplog.at_level(logging.INFO):
            cid = get_correlation_id()
            logger.info("manual.injection", extra={"correlation_id": cid or "-"})

        record = caplog.records[0]
        assert record.correlation_id == "manual-456"


class ExampleServiceWithBothPatterns(LoggingMixin):
    """Demonstrates mixing instance methods (LoggingMixin) with class methods."""

    def instance_method(self):
        """Instance method can use LoggingMixin."""
        self.log_info("instance.event")

    @classmethod
    def class_method(cls):
        """Class method must use module-level logger."""
        cid = get_correlation_id()
        logger.info("class.event", extra={"correlation_id": cid or "-"})


class TestMixedPatterns:
    """Test services that use both instance methods and class methods."""

    def test_both_patterns_coexist(self, caplog):
        """Service can have both instance methods (LoggingMixin) and class methods (module logger)."""
        set_correlation_id("mixed-789")

        instance = ExampleServiceWithBothPatterns()

        with caplog.at_level(logging.INFO):
            instance.instance_method()
            ExampleServiceWithBothPatterns.class_method()

        assert len(caplog.records) == 2
        assert caplog.records[0].correlation_id == "mixed-789"
        assert caplog.records[1].correlation_id == "mixed-789"
