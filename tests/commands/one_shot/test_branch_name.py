"""Tests for one-shot branch name generation."""

import re

from erk.cli.commands.one_shot_dispatch import generate_branch_name
from erk_shared.gateway.time.fake import FakeTime


def test_generate_branch_name_basic() -> None:
    """Test basic branch name generation with no plan issue (oneshot- prefix)."""
    name = generate_branch_name(
        "fix the import", time=FakeTime(), plan_issue_number=None, objective_id=None
    )
    assert name.startswith("oneshot-fix-the-import-")
    # Should end with timestamp pattern -MM-DD-HHMM
    assert re.search(r"-\d{2}-\d{2}-\d{4}$", name) is not None


def test_generate_branch_name_sanitizes_special_chars() -> None:
    """Test that special characters are sanitized."""
    name = generate_branch_name(
        "Fix: Bug #123!", time=FakeTime(), plan_issue_number=None, objective_id=None
    )
    assert name.startswith("oneshot-")
    # No special characters in the branch name (except hyphens and digits)
    assert re.match(r"^oneshot-[a-z0-9-]+-\d{2}-\d{2}-\d{4}$", name) is not None


def test_generate_branch_name_truncates_long_instruction() -> None:
    """Test that long instructions are truncated."""
    long_instruction = "a" * 100
    name = generate_branch_name(
        long_instruction, time=FakeTime(), plan_issue_number=None, objective_id=None
    )
    # Should be bounded in length: oneshot- (8) + slug (max ~23) + timestamp (-MM-DD-HHMM, 10)
    assert len(name) <= 50


def test_generate_branch_name_with_plan_issue_number() -> None:
    """Test branch name uses P<N>- prefix when plan_issue_number is provided."""
    name = generate_branch_name(
        "fix the import", time=FakeTime(), plan_issue_number=42, objective_id=None
    )
    assert name.startswith("P42-fix-the-import-")
    assert re.search(r"-\d{2}-\d{2}-\d{4}$", name) is not None


def test_generate_branch_name_with_large_plan_issue_number() -> None:
    """Test branch name with a large plan issue number truncates slug appropriately."""
    name = generate_branch_name(
        "a" * 100, time=FakeTime(), plan_issue_number=12345, objective_id=None
    )
    # P12345- is 7 chars, timestamp is 10 chars, total slug space is 31-7=24
    assert name.startswith("P12345-")
    assert len(name) <= 50


def test_generate_branch_name_with_objective_id() -> None:
    """Test branch name encodes O{N} when both plan_issue_number and objective_id are provided."""
    name = generate_branch_name(
        "fix the import", time=FakeTime(), plan_issue_number=42, objective_id=100
    )
    assert name.startswith("P42-O100-")
    assert re.search(r"-\d{2}-\d{2}-\d{4}$", name) is not None
