"""Tests for logging_mixin.context ContextVar utilities."""

import pytest

from logging_mixin.context import (
    clear_correlation_id,
    get_correlation_id,
    set_correlation_id,
)


class TestCorrelationIdContext:
    """Test ContextVar get/set/clear helpers."""

    def test_get_when_not_set(self):
        """get_correlation_id() returns None when not set."""
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_set_and_get(self):
        """set_correlation_id() stores value that get_correlation_id() retrieves."""
        clear_correlation_id()
        set_correlation_id("test-123")
        assert get_correlation_id() == "test-123"

    def test_set_empty_string(self):
        """set_correlation_id('') is equivalent to not set (returns None on get)."""
        clear_correlation_id()
        set_correlation_id("")
        assert get_correlation_id() is None

    def test_set_none(self):
        """set_correlation_id(None) clears the value."""
        set_correlation_id("test-123")
        set_correlation_id(None)
        assert get_correlation_id() is None

    def test_clear(self):
        """clear_correlation_id() resets to unset state."""
        set_correlation_id("test-456")
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_clear_when_not_set(self):
        """clear_correlation_id() is safe to call when already cleared."""
        clear_correlation_id()
        clear_correlation_id()  # Should not raise
        assert get_correlation_id() is None

    def test_set_overwrites_previous(self):
        """set_correlation_id() overwrites previous value."""
        set_correlation_id("old")
        set_correlation_id("new")
        assert get_correlation_id() == "new"

    def test_uuid_format(self):
        """set_correlation_id() accepts UUID-like strings."""
        uuid_val = "a1b2c3d4-e5f6-4789-abcd-ef1234567890"
        set_correlation_id(uuid_val)
        assert get_correlation_id() == uuid_val

    def test_hex_format(self):
        """set_correlation_id() accepts hex strings."""
        hex_val = "abc123def456"
        set_correlation_id(hex_val)
        assert get_correlation_id() == hex_val
