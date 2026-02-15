"""Tests for one-shot branch name generation."""

import re

from erk.cli.commands.one_shot_dispatch import generate_branch_name
from erk_shared.gateway.time.fake import FakeTime


def test_generate_branch_name_basic() -> None:
    """Test basic branch name generation."""
    name = generate_branch_name("fix the import", time=FakeTime())
    assert name.startswith("oneshot-fix-the-import-")
    # Should end with timestamp pattern -MM-DD-HHMM
    assert re.search(r"-\d{2}-\d{2}-\d{4}$", name) is not None


def test_generate_branch_name_sanitizes_special_chars() -> None:
    """Test that special characters are sanitized."""
    name = generate_branch_name("Fix: Bug #123!", time=FakeTime())
    assert name.startswith("oneshot-")
    # No special characters in the branch name (except hyphens and digits)
    assert re.match(r"^oneshot-[a-z0-9-]+-\d{2}-\d{2}-\d{4}$", name) is not None


def test_generate_branch_name_truncates_long_instruction() -> None:
    """Test that long instructions are truncated."""
    long_instruction = "a" * 100
    name = generate_branch_name(long_instruction, time=FakeTime())
    # Should be bounded in length: oneshot- (8) + slug (max ~23) + timestamp (-MM-DD-HHMM, 10)
    assert len(name) <= 50
