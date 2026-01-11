"""Tests for learn plan handling in submit."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import is_issue_learn_plan, submit_cmd
from erk_shared.gateway.gt.operations.finalize import ERK_SKIP_EXTRACTION_LABEL
from tests.commands.submit.conftest import (
    create_plan,
    make_learn_plan_body,
    make_plan_body,
    setup_submit_context,
)


def test_is_issue_learn_plan_returns_true_for_learn_plan() -> None:
    """Test is_issue_learn_plan returns True when plan_type is 'learn'."""
    body = make_learn_plan_body()
    result = is_issue_learn_plan(body)
    assert result is True


def test_is_issue_learn_plan_returns_false_for_standard_plan() -> None:
    """Test is_issue_learn_plan returns False when plan_type is not 'learn'."""
    body = make_plan_body()
    result = is_issue_learn_plan(body)
    assert result is False


def test_is_issue_learn_plan_returns_false_for_no_metadata() -> None:
    """Test is_issue_learn_plan returns False when there's no plan-header block."""
    body = "# Just a plain issue\n\nNo metadata here."
    result = is_issue_learn_plan(body)
    assert result is False


def test_submit_learn_plan_adds_skip_extraction_label(tmp_path: Path) -> None:
    """Test submit adds erk-skip-extraction label to PR for learn plans."""
    # Plan with learn plan_type in metadata
    learn_body = make_learn_plan_body()
    plan = create_plan("123", "Extract documentation from session X", body=learn_body)
    ctx, _, fake_github, _, _ = setup_submit_context(tmp_path, {"123": plan})

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify erk-skip-extraction label was added to PR
    assert len(fake_github.added_labels) == 1
    pr_number, label = fake_github.added_labels[0]
    assert pr_number == 999  # FakeGitHub returns 999 for created PRs
    assert label == ERK_SKIP_EXTRACTION_LABEL

    # Verify PR body was updated (checkout command, no extraction marker)
    assert len(fake_github.updated_pr_bodies) == 1
    _, updated_body = fake_github.updated_pr_bodies[0]
    assert "erk pr checkout" in updated_body


def test_submit_standard_plan_does_not_add_skip_extraction_label(tmp_path: Path) -> None:
    """Test submit does NOT add erk-skip-extraction label for standard plans."""
    # Standard plan (not learn)
    standard_body = make_plan_body()
    plan = create_plan("456", "Implement feature Y", body=standard_body)
    ctx, _, fake_github, _, _ = setup_submit_context(tmp_path, {"456": plan})

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["456"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify NO label was added (standard plan, not learn)
    assert len(fake_github.added_labels) == 0

    # Verify PR body was updated (checkout command only)
    assert len(fake_github.updated_pr_bodies) == 1
    _, updated_body = fake_github.updated_pr_bodies[0]
    assert "erk pr checkout" in updated_body
