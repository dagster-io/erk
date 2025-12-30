"""Tests for scripts/code_stats.py date parsing functionality."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add scripts directory to path so we can import code_stats
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from code_stats import InvalidDateFormat, parse_since_date


class TestParseSinceDateISODate:
    """Tests for ISO date format parsing."""

    def test_parses_valid_iso_date(self) -> None:
        result = parse_since_date("2025-12-28")
        assert result == datetime(2025, 12, 28, 0, 0, 0)

    def test_parses_iso_date_at_midnight(self) -> None:
        result = parse_since_date("2025-01-01")
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0


class TestParseSinceDateISODatetime:
    """Tests for ISO datetime format parsing."""

    def test_parses_valid_iso_datetime(self) -> None:
        result = parse_since_date("2025-12-28T14:30:00")
        assert result == datetime(2025, 12, 28, 14, 30, 0)

    def test_parses_iso_datetime_with_zeros(self) -> None:
        result = parse_since_date("2025-12-28T00:00:00")
        assert result == datetime(2025, 12, 28, 0, 0, 0)


class TestParseSinceDateErrors:
    """Tests for invalid input handling."""

    def test_raises_on_invalid_format(self) -> None:
        with pytest.raises(InvalidDateFormat) as exc_info:
            parse_since_date("not-a-date")
        assert "Cannot parse date: not-a-date" in str(exc_info.value)

    def test_raises_on_empty_string(self) -> None:
        with pytest.raises(InvalidDateFormat) as exc_info:
            parse_since_date("")
        assert "Cannot parse date: " in str(exc_info.value)

    def test_raises_on_partial_iso_date(self) -> None:
        with pytest.raises(InvalidDateFormat):
            parse_since_date("2025-12")

    def test_raises_on_relative_expression(self) -> None:
        # Relative expressions like "last 2 hours" are handled by the LLM,
        # not the Python script
        with pytest.raises(InvalidDateFormat):
            parse_since_date("last 2 hours")
