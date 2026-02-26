"""Tests for scripts/execute_objective.py helper functions."""

import os
import sys
from pathlib import Path

import pytest

# Add scripts directory to path so we can import execute_objective
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from execute_objective import _build_claude_env, slugify


class TestSlugify:
    """Tests for slugify() branch-name slug generation."""

    def test_converts_spaces_to_hyphens(self) -> None:
        result = slugify("hello world", max_len=30)
        assert result == "hello-world"

    def test_lowercases_text(self) -> None:
        result = slugify("Hello World", max_len=30)
        assert result == "hello-world"

    def test_removes_special_characters(self) -> None:
        result = slugify("feat: add (new) stuff!", max_len=30)
        assert result == "feat-add-new-stuff"

    def test_strips_leading_hyphens(self) -> None:
        result = slugify("--leading", max_len=30)
        assert result == "leading"

    def test_strips_trailing_hyphens(self) -> None:
        result = slugify("trailing--", max_len=30)
        assert result == "trailing"

    def test_truncates_to_max_len(self) -> None:
        result = slugify("this is a very long description", max_len=10)
        assert len(result) <= 10

    def test_truncation_does_not_end_with_hyphen(self) -> None:
        result = slugify("abc def ghi jkl", max_len=8)
        assert not result.endswith("-")

    def test_empty_string(self) -> None:
        result = slugify("", max_len=30)
        assert result == ""

    def test_only_special_characters(self) -> None:
        result = slugify("!@#$%", max_len=30)
        assert result == ""


class TestBuildClaudeEnv:
    """Tests for _build_claude_env() environment setup."""

    def test_strips_claudecode_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDECODE", "1")
        env = _build_claude_env()
        assert "CLAUDECODE" not in env

    def test_preserves_other_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TEST_VAR", "hello")
        env = _build_claude_env()
        assert env["MY_TEST_VAR"] == "hello"

    def test_works_without_claudecode(self) -> None:
        if "CLAUDECODE" in os.environ:
            pytest.skip("CLAUDECODE is set in test environment")
        env = _build_claude_env()
        assert "CLAUDECODE" not in env
