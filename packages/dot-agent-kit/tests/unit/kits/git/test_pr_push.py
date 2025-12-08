"""Unit tests for git pr-push kit CLI commands.

Tests the preflight and finalize commands using dependency injection
with DotAgentContext.for_test() and fake implementations.
"""

import json
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.git.kit_cli_commands.git.pr_push import (
    finalize,
    preflight,
)


def _make_pr_info(number: int, branch: str) -> PullRequestInfo:
    """Create a PullRequestInfo with default values for testing."""
    return PullRequestInfo(
        number=number,
        state="OPEN",
        url=f"https://github.com/org/repo/pull/{number}",
        is_draft=False,
        title=f"PR #{number}: {branch}",
        checks_passing=None,
        owner="org",
        repo="repo",
    )


def _extract_json(output: str) -> dict:
    """Extract the JSON object from CLI output that may contain progress messages."""
    # Find where JSON starts (first '{' character)
    start = output.find("{")
    if start == -1:
        raise ValueError(f"No JSON found in output: {output}")
    # Find the matching closing brace
    brace_count = 0
    for i, char in enumerate(output[start:], start):
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0:
                return json.loads(output[start : i + 1])
    raise ValueError(f"Unclosed JSON in output: {output}")


def test_preflight_uses_injected_cwd(tmp_path: Path) -> None:
    """Test that preflight uses cwd from context, not Path.cwd()."""
    git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
        repository_roots={tmp_path: tmp_path},
        file_statuses={tmp_path: ([], [], [])},  # Clean
        commit_messages_since={(tmp_path, "main"): ["Add feature"]},
    )

    # FakeGitHub with unauthenticated - should fail at auth check
    github = FakeGitHub(authenticated=False)

    context = DotAgentContext.for_test(
        git=git,
        github=github,
        cwd=tmp_path,
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(preflight, ["--session-id", "test-session"], obj=context)

    # The command should have used the injected cwd (tmp_path)
    # and failed at auth check - verifying the context is used
    output = _extract_json(result.output)
    assert output["success"] is False
    assert output["error_type"] == "gh_not_authenticated"


def test_preflight_auth_failure(tmp_path: Path) -> None:
    """Test preflight fails with clear error when GitHub not authenticated."""
    git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
        repository_roots={tmp_path: tmp_path},
    )
    github = FakeGitHub(authenticated=False)

    context = DotAgentContext.for_test(
        git=git,
        github=github,
        cwd=tmp_path,
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(preflight, ["--session-id", "test-session"], obj=context)

    assert result.exit_code == 1
    output = _extract_json(result.output)
    assert output["success"] is False
    assert "gh_not_authenticated" in output["error_type"]


def test_preflight_with_existing_pr(tmp_path: Path) -> None:
    """Test preflight success when PR already exists for branch."""
    git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
        repository_roots={tmp_path: tmp_path},
        file_statuses={tmp_path: ([], [], [])},  # Clean
        commit_messages_since={(tmp_path, "main"): ["Add feature"]},
    )

    pr_info = _make_pr_info(123, "feature")
    github = FakeGitHub(
        authenticated=True,
        prs={"feature": pr_info},
        pr_details={
            123: PRDetails(
                number=123,
                title="Add feature",
                url="https://github.com/org/repo/pull/123",
                state="OPEN",
                body="",
                is_draft=False,
                base_ref_name="main",
                head_ref_name="feature",
                is_cross_repository=False,
                mergeable="MERGEABLE",
                merge_state_status="CLEAN",
                owner="org",
                repo="repo",
            )
        },
        pr_diffs={123: "diff --git a/file.py b/file.py\n+new line"},
    )

    context = DotAgentContext.for_test(
        git=git,
        github=github,
        cwd=tmp_path,
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(preflight, ["--session-id", "test-session"], obj=context)

    assert result.exit_code == 0
    output = _extract_json(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123
    assert "feature" in output["branch_name"]


def test_finalize_uses_injected_cwd(tmp_path: Path) -> None:
    """Test that finalize uses cwd from context, not Path.cwd()."""
    git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
        repository_roots={tmp_path: tmp_path},
    )

    pr_info = _make_pr_info(123, "feature")
    github = FakeGitHub(
        authenticated=True,
        prs={"feature": pr_info},
        pr_details={
            123: PRDetails(
                number=123,
                title="Old title",
                url="https://github.com/org/repo/pull/123",
                state="OPEN",
                body="",
                is_draft=False,
                base_ref_name="main",
                head_ref_name="feature",
                is_cross_repository=False,
                mergeable="MERGEABLE",
                merge_state_status="CLEAN",
                owner="org",
                repo="repo",
            )
        },
    )

    context = DotAgentContext.for_test(
        git=git,
        github=github,
        cwd=tmp_path,
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        finalize,
        [
            "--pr-number",
            "123",
            "--pr-title",
            "New title",
            "--pr-body",
            "New body content",
        ],
        obj=context,
    )

    assert result.exit_code == 0
    output = _extract_json(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123

    # Verify PR was updated via the fake
    assert len(github.updated_pr_titles) == 1
    assert github.updated_pr_titles[0] == (123, "New title")


def test_finalize_pr_update_failure(tmp_path: Path) -> None:
    """Test finalize handles PR update failure gracefully."""
    git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
        repository_roots={tmp_path: tmp_path},
    )

    pr_info = _make_pr_info(123, "feature")
    github = FakeGitHub(
        authenticated=True,
        prs={"feature": pr_info},
        pr_details={
            123: PRDetails(
                number=123,
                title="Old title",
                url="https://github.com/org/repo/pull/123",
                state="OPEN",
                body="",
                is_draft=False,
                base_ref_name="main",
                head_ref_name="feature",
                is_cross_repository=False,
                mergeable="MERGEABLE",
                merge_state_status="CLEAN",
                owner="org",
                repo="repo",
            )
        },
        pr_update_should_succeed=False,  # Simulate failure
    )

    context = DotAgentContext.for_test(
        git=git,
        github=github,
        cwd=tmp_path,
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        finalize,
        [
            "--pr-number",
            "123",
            "--pr-title",
            "New title",
            "--pr-body",
            "New body",
        ],
        obj=context,
    )

    assert result.exit_code == 1
    output = _extract_json(result.output)
    assert output["success"] is False
    assert "pr_update_failed" in output["error_type"]


def test_finalize_validates_body_args() -> None:
    """Test finalize requires exactly one of --pr-body or --pr-body-file."""
    runner = CliRunner()

    # Neither provided
    result = runner.invoke(
        finalize,
        [
            "--pr-number",
            "123",
            "--pr-title",
            "Title",
        ],
    )

    assert result.exit_code == 1
    # Should have validation error
    assert "Validation error" in result.output or "error" in result.output.lower()
