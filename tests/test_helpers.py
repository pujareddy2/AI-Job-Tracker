"""
tests/test_helpers.py — Tests for utils/helpers.py
===================================================
Tests verify:
    1. sanitise_text collapses whitespace correctly.
    2. utc_now returns a timezone-aware datetime.
    3. format_timestamp produces a valid ISO-8601 string.
    4. retry decorator retries on failure and raises after max attempts.
    5. ensure_dir creates a directory.
"""

from __future__ import annotations

import time
from datetime import timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from utils.helpers import (
    ensure_dir,
    format_timestamp,
    retry,
    sanitise_text,
    utc_now,
)


class TestSanitiseText:
    def test_strips_leading_trailing_whitespace(self) -> None:
        assert sanitise_text("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self) -> None:
        assert sanitise_text("hello   world") == "hello world"

    def test_handles_newlines(self) -> None:
        assert sanitise_text("hello\n\nworld") == "hello world"

    def test_empty_string(self) -> None:
        assert sanitise_text("") == ""

    def test_already_clean(self) -> None:
        assert sanitise_text("clean string") == "clean string"


class TestUtcNow:
    def test_returns_aware_datetime(self) -> None:
        dt = utc_now()
        assert dt.tzinfo is not None
        assert dt.tzinfo == timezone.utc


class TestFormatTimestamp:
    def test_returns_string(self) -> None:
        ts = format_timestamp()
        assert isinstance(ts, str)

    def test_contains_utc_offset(self) -> None:
        ts = format_timestamp()
        assert "+00:00" in ts or "Z" in ts or "UTC" in ts or "00:00" in ts

    def test_accepts_datetime_argument(self) -> None:
        from datetime import datetime
        dt = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        ts = format_timestamp(dt)
        assert "2024-01-15" in ts


class TestRetryDecorator:
    def test_succeeds_on_first_attempt(self) -> None:
        mock_fn = MagicMock(return_value="ok")

        @retry(max_attempts=3, delay=0)
        def func() -> str:
            return mock_fn()

        result = func()
        assert result == "ok"
        mock_fn.assert_called_once()

    def test_retries_on_failure_then_succeeds(self) -> None:
        results = [ValueError("fail"), ValueError("fail"), "ok"]

        def side_effect():
            result = results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        mock_fn = MagicMock(side_effect=side_effect)

        @retry(max_attempts=3, delay=0, exceptions=(ValueError,))
        def func() -> str:
            return mock_fn()

        result = func()
        assert result == "ok"
        assert mock_fn.call_count == 3

    def test_raises_after_max_attempts(self) -> None:
        @retry(max_attempts=2, delay=0, exceptions=(ValueError,))
        def always_fails() -> None:
            raise ValueError("always fail")

        with pytest.raises(ValueError, match="always fail"):
            always_fails()

    def test_does_not_retry_on_unlisted_exception(self) -> None:
        @retry(max_attempts=3, delay=0, exceptions=(TypeError,))
        def raises_value_error() -> None:
            raise ValueError("not retried")

        with pytest.raises(ValueError):
            raises_value_error()


class TestEnsureDir:
    def test_creates_directory(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "sub" / "nested"
        result = ensure_dir(new_dir)
        assert new_dir.is_dir()
        assert result == new_dir

    def test_does_not_fail_if_exists(self, tmp_path: Path) -> None:
        ensure_dir(tmp_path)   # already exists — should not raise
