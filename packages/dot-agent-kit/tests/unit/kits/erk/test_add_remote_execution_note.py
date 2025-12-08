"""Unit tests for add_remote_execution_note kit CLI command.

Tests adding remote execution tracking notes to PR bodies.
Uses FakeGitHub for fast, reliable testing (Layer 4: Business Logic over Fakes).
"""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.fake import FakeGitHub

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.add_remote_execution_note import (
    add_remote_execution_note,
)

# ============================================================================
# Success Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_add_remote_execution_note_success(tmp_path: Path) -> None:
    """Test successfully adding a remote execution note to a PR."""
    fake_github = FakeGitHub(
        pr_bodies_by_number={100: "Initial PR body"},
    )
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_remote_execution_note,
            [
                "--pr-number",
                "100",
                "--run-id",
                "12345678",
                "--run-url",
                "https://github.com/owner/repo/actions/runs/12345678",
            ],
            obj=DotAgentContext.for_test(github=fake_github, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    assert "Added remote execution note to PR #100" in result.output

    # Verify the PR body was updated
    assert len(fake_github.updated_pr_bodies) == 1
    pr_number, new_body = fake_github.updated_pr_bodies[0]
    assert pr_number == 100
    assert "Initial PR body" in new_body
    assert "[Run #12345678]" in new_body
    assert "https://github.com/owner/repo/actions/runs/12345678" in new_body


def test_add_remote_execution_note_to_empty_body(tmp_path: Path) -> None:
    """Test adding note to PR with no existing body."""
    fake_github = FakeGitHub(
        pr_bodies_by_number={200: ""},
    )
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_remote_execution_note,
            [
                "--pr-number",
                "200",
                "--run-id",
                "99999",
                "--run-url",
                "https://example.com/runs/99999",
            ],
            obj=DotAgentContext.for_test(github=fake_github, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output

    # Verify the note was still added
    assert len(fake_github.updated_pr_bodies) == 1
    _, new_body = fake_github.updated_pr_bodies[0]
    assert "[Run #99999]" in new_body


def test_add_remote_execution_note_preserves_existing_body(tmp_path: Path) -> None:
    """Test that existing PR body content is preserved."""
    existing_body = """## Summary

This PR implements feature X.

## Test Plan

- [x] Unit tests pass
"""
    fake_github = FakeGitHub(
        pr_bodies_by_number={300: existing_body},
    )
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_remote_execution_note,
            [
                "--pr-number",
                "300",
                "--run-id",
                "11111",
                "--run-url",
                "https://github.com/test/repo/runs/11111",
            ],
            obj=DotAgentContext.for_test(github=fake_github, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output

    _, new_body = fake_github.updated_pr_bodies[0]
    # Original content preserved
    assert "## Summary" in new_body
    assert "This PR implements feature X" in new_body
    assert "## Test Plan" in new_body
    # New note appended
    assert "[Run #11111]" in new_body


def test_add_remote_execution_note_when_body_is_none(tmp_path: Path) -> None:
    """Test handling when PR body is None (not set)."""
    fake_github = FakeGitHub()  # No pr_bodies_by_number configured
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_remote_execution_note,
            [
                "--pr-number",
                "400",
                "--run-id",
                "77777",
                "--run-url",
                "https://example.com/77777",
            ],
            obj=DotAgentContext.for_test(github=fake_github, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output

    # Should still work with empty string as starting point
    assert len(fake_github.updated_pr_bodies) == 1
    _, new_body = fake_github.updated_pr_bodies[0]
    assert "[Run #77777]" in new_body


# ============================================================================
# CLI Argument Tests
# ============================================================================


def test_missing_pr_number(tmp_path: Path) -> None:
    """Test error when pr-number is missing."""
    fake_github = FakeGitHub()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_remote_execution_note,
            [
                "--run-id",
                "123",
                "--run-url",
                "https://example.com/123",
            ],
            obj=DotAgentContext.for_test(github=fake_github, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code != 0
    assert "pr-number" in result.output.lower()


def test_missing_run_id(tmp_path: Path) -> None:
    """Test error when run-id is missing."""
    fake_github = FakeGitHub()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_remote_execution_note,
            [
                "--pr-number",
                "100",
                "--run-url",
                "https://example.com/123",
            ],
            obj=DotAgentContext.for_test(github=fake_github, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code != 0
    assert "run-id" in result.output.lower()


def test_missing_run_url(tmp_path: Path) -> None:
    """Test error when run-url is missing."""
    fake_github = FakeGitHub()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_remote_execution_note,
            [
                "--pr-number",
                "100",
                "--run-id",
                "123",
            ],
            obj=DotAgentContext.for_test(github=fake_github, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code != 0
    assert "run-url" in result.output.lower()
