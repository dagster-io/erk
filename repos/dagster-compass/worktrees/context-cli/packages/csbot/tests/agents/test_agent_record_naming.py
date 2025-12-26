"""Tests for agent record naming conventions."""

import json
import tempfile
from pathlib import Path

from csbot.compass_dev.agent_record.naming import (
    find_naming_violations,
    is_valid_scenario_name,
    suggest_valid_name,
)


class TestScenarioNaming:
    """Test scenario name validation."""

    def test_valid_names(self):
        """Test that valid names pass validation."""
        valid_names = [
            "simple-test",
            "calculator-tool",
            "weather-api",
            "test123",
            "multi-word-scenario",
            "a",
            "test-with-numbers-123",
        ]

        for name in valid_names:
            assert is_valid_scenario_name(name), f"'{name}' should be valid"

    def test_invalid_names(self):
        """Test that invalid names fail validation."""
        invalid_names = [
            "simple_test",  # underscore
            "Simple-Test",  # uppercase
            "test@123",  # special character
            "test.name",  # period
            "test name",  # space
            "test-",  # trailing hyphen
            "-test",  # leading hyphen
            "",  # empty
            "test--name",  # double hyphen
            "UPPERCASE",  # all uppercase
        ]

        for name in invalid_names:
            assert not is_valid_scenario_name(name), f"'{name}' should be invalid"

    def test_suggest_valid_name(self):
        """Test name suggestion functionality."""
        test_cases = [
            ("simple_test", "simple-test"),
            ("Simple_Test", "simple-test"),
            ("TEST_CASE", "test-case"),
            ("test@123", "test-123"),
            ("test.name", "test-name"),
            ("test name", "test-name"),
            ("test___name", "test-name"),
            ("__test__", "test"),
            ("test--name", "test-name"),
            ("", ""),
            ("A_B_C", "a-b-c"),
        ]

        for input_name, expected in test_cases:
            result = suggest_valid_name(input_name)
            assert result == expected, (
                f"suggest_valid_name('{input_name}') should return '{expected}', got '{result}'"
            )


class TestNamingViolations:
    """Test finding naming violations in files."""

    def test_find_naming_violations(self):
        """Test finding files with naming violations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            test_files = {
                "valid-name.json": {"scenario": "valid-name"},
                "another-valid.json": {"scenario": "another-valid"},
                "invalid_name.json": {"scenario": "invalid_name"},
                "Another_Invalid.json": {"scenario": "Another_Invalid"},
                "_private.json": {"scenario": "_private"},  # Should be skipped
                "valid123.json": {"scenario": "valid123"},
            }

            for filename, content in test_files.items():
                file_path = temp_path / filename
                with open(file_path, "w") as f:
                    json.dump(content, f)

            violations = find_naming_violations(temp_path)

            # Should find invalid_name.json and Another_Invalid.json
            # Should NOT find _private.json (private files are skipped)
            violation_names = [name for _, name in violations]

            assert "invalid_name" in violation_names
            assert "Another_Invalid" in violation_names
            assert "_private" not in violation_names  # Private files skipped
            assert "valid-name" not in violation_names
            assert "another-valid" not in violation_names
            assert "valid123" not in violation_names

            assert len(violations) == 2

    def test_find_violations_empty_directory(self):
        """Test finding violations in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            violations = find_naming_violations(temp_path)
            assert violations == []

    def test_find_violations_no_json_files(self):
        """Test finding violations with no JSON files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create non-JSON files
            (temp_path / "test.txt").write_text("test")
            (temp_path / "another.py").write_text("# python")

            violations = find_naming_violations(temp_path)
            assert violations == []
