"""Tests for LoggingMixin instance method logging."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from logging_mixin import LoggingMixin, clear_correlation_id, set_correlation_id


class SampleService(LoggingMixin):
    """Test service using LoggingMixin."""

    def do_something(self):
        """Sample method that logs."""
        self.log_info("sample.event", key="value")

    def do_error(self):
        """Sample method that logs an error."""
        self.log_error("sample.error", error_code=500)


class SampleWithMasking(LoggingMixin):
    """Test service with mask_for_logging() method (composition)."""

    def __init__(self):
        self.sensitive_data = "secret123"
        self.public_data = "public"

    def mask_for_logging(self):
        """Mask sensitive fields for logging."""
        return {"sensitive_data": "<MASKED>", "public_data": self.public_data}

    def do_something_masked(self):
        """Method that logs with masked instance data."""
        self.log_info("masked.event")


class TestLoggingMixinBasic:
    """Test basic LoggingMixin functionality."""

    def test_log_info(self, caplog):
        """log_info() logs at INFO level."""
        clear_correlation_id()
        set_correlation_id("test-123")

        service = SampleService()
        with caplog.at_level(logging.INFO):
            service.log_info("test.event", item=42)

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "INFO"
        assert record.getMessage() == "test.event"
        assert record.correlation_id == "test-123"
        assert record.item == 42

    def test_log_debug(self, caplog):
        """log_debug() logs at DEBUG level."""
        clear_correlation_id()
        set_correlation_id("debug-456")

        service = SampleService()
        with caplog.at_level(logging.DEBUG):
            service.log_debug("test.debug", detail="verbose")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "DEBUG"
        assert record.correlation_id == "debug-456"
        assert record.detail == "verbose"

    def test_log_warning(self, caplog):
        """log_warning() logs at WARNING level."""
        clear_correlation_id()
        set_correlation_id("warn-789")

        service = SampleService()
        with caplog.at_level(logging.WARNING):
            service.log_warning("test.warn", issue="something")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert record.correlation_id == "warn-789"
        assert record.issue == "something"

    def test_log_error(self, caplog):
        """log_error() logs at ERROR level."""
        clear_correlation_id()
        set_correlation_id("error-abc")

        service = SampleService()
        with caplog.at_level(logging.ERROR):
            service.log_error("test.error", code=500)

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "ERROR"
        assert record.correlation_id == "error-abc"
        assert record.code == 500

    def test_log_exception(self, caplog):
        """log_exception() logs at ERROR level with traceback."""
        clear_correlation_id()
        set_correlation_id("exc-def")

        service = SampleService()
        try:
            raise ValueError("test exception")
        except ValueError:
            with caplog.at_level(logging.ERROR):
                service.log_exception("test.exc")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "ERROR"
        assert record.correlation_id == "exc-def"
        # exc_info should be captured
        assert record.exc_info is not None

    def test_logger_name_includes_class(self):
        """Logger name includes module and class name."""
        service = SampleService()
        logger_name = service._logger.name
        assert logger_name.endswith("SampleService")
        assert "test_mixin" in logger_name  # Module name

    def test_correlation_id_fallback_to_dash(self, caplog):
        """When correlation_id is not set, extra gets '-' as fallback."""
        clear_correlation_id()

        service = SampleService()
        with caplog.at_level(logging.INFO):
            service.log_info("test.fallback")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.correlation_id == "-"

    def test_extra_fields_passed_through(self, caplog):
        """Extra keyword arguments are included in log record."""
        clear_correlation_id()
        set_correlation_id("extra-123")

        service = SampleService()
        with caplog.at_level(logging.INFO):
            service.log_info("test.extra", count=5, status="ok", value=99.5)

        record = caplog.records[0]
        assert record.count == 5
        assert record.status == "ok"
        assert record.value == 99.5


class TestLoggingMixinWithMasking:
    """Test LoggingMixin composition with masking mixin."""

    def test_mask_for_logging_included_in_extra(self, caplog):
        """When mask_for_logging() exists, its output is added to extra['instance']."""
        clear_correlation_id()
        set_correlation_id("masked-123")

        service = SampleWithMasking()
        with caplog.at_level(logging.INFO):
            service.log_info("masked.test")

        record = caplog.records[0]
        assert record.correlation_id == "masked-123"
        assert "instance" in record.__dict__
        assert record.instance == {  # type: ignore
            "sensitive_data": "<MASKED>",
            "public_data": "public",
        }

    def test_mask_for_logging_combined_with_extra_fields(self, caplog):
        """mask_for_logging() and caller fields both appear in extra."""
        clear_correlation_id()
        set_correlation_id("combo-456")

        service = SampleWithMasking()
        with caplog.at_level(logging.INFO):
            service.log_info("masked.combo", action="test")

        record = caplog.records[0]
        assert record.correlation_id == "combo-456"
        assert record.instance == {  # type: ignore
            "sensitive_data": "<MASKED>",
            "public_data": "public",
        }
        assert record.action == "test"  # type: ignore


class TestLoggingMixinMultipleInstances:
    """Test that multiple instances can log independently."""

    def test_different_instances_different_contexts(self, caplog):
        """Different service instances can log with different correlation IDs."""
        service1 = SampleService()
        service2 = SampleService()

        # Service 1 logs with correlation_id "service1"
        set_correlation_id("service1")
        with caplog.at_level(logging.INFO):
            service1.log_info("event1")

        # Service 2 logs with correlation_id "service2"
        set_correlation_id("service2")
        with caplog.at_level(logging.INFO):
            service2.log_info("event2")

        assert len(caplog.records) == 2
        assert caplog.records[0].correlation_id == "service1"
        assert caplog.records[1].correlation_id == "service2"
