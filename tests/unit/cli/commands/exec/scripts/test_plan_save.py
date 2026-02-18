"""Unit tests for plan-save command (backend-aware dispatcher)."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_save import plan_save
from erk_shared.context.context import ErkContext
from erk_shared.context.testing import context_for_test
from erk_shared.context.types import LoadedConfig
from erk_shared.gateway.claude_installation.fake import FakeClaudeInstallation
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues

# Valid plan content that passes validation (100+ chars with structure)
VALID_PLAN_CONTENT = """# Feature Plan

This plan describes the implementation of a new feature.

- Step 1: Set up the environment
- Step 2: Implement the core logic
- Step 3: Add tests and documentation"""


def _draft_pr_context(
    *,
    tmp_path: Path,
    fake_github: FakeGitHub | None = None,
    fake_git: FakeGit | None = None,
    fake_claude: FakeClaudeInstallation | None = None,
    plan_backend: str = "draft_pr",
) -> ErkContext:
    """Build an ErkContext configured for draft-PR plan backend."""
    if fake_git is None:
        fake_git = FakeGit(current_branches={tmp_path: "main"})
    if fake_github is None:
        fake_github = FakeGitHub()
    if fake_claude is None:
        fake_claude = FakeClaudeInstallation.for_test(plans={"plan": VALID_PLAN_CONTENT})

    return context_for_test(
        local_config=LoadedConfig.test(plan_backend=plan_backend),
        github=fake_github,
        git=fake_git,
        claude_installation=fake_claude,
        cwd=tmp_path,
        repo_root=tmp_path,
    )


def test_draft_pr_success_json(tmp_path: Path) -> None:
    """Happy path: exit 0, JSON output has success/issue_number/branch_name."""
    ctx = _draft_pr_context(tmp_path=tmp_path)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "issue_number" in output
    assert "branch_name" in output
    assert output["branch_name"].startswith("plan-")


def test_draft_pr_success_display(tmp_path: Path) -> None:
    """Display format: output contains 'Plan saved as draft PR'."""
    ctx = _draft_pr_context(tmp_path=tmp_path)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "display"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "Plan saved as draft PR" in result.output
    assert "Title: Feature Plan" in result.output
    assert "Branch: plan-" in result.output


def test_delegates_to_issue_when_not_draft_pr(tmp_path: Path) -> None:
    """plan_backend=None delegates to plan_save_to_issue."""
    fake_issues = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    ctx = context_for_test(
        local_config=LoadedConfig.test(plan_backend=None),
        github=fake_github,
        claude_installation=FakeClaudeInstallation.for_test(plans={"plan": VALID_PLAN_CONTENT}),
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # Issue-based save creates issues, not PRs
    assert len(fake_issues.created_issues) == 1
    assert len(fake_github.created_prs) == 0


def test_draft_pr_no_plan_found(tmp_path: Path) -> None:
    """Empty claude_installation: exit code 1."""
    ctx = _draft_pr_context(
        tmp_path=tmp_path,
        fake_claude=FakeClaudeInstallation.for_test(),
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No plan found" in output["error"]


def test_draft_pr_validation_failure(tmp_path: Path) -> None:
    """Short plan: exit code 2, error_type='validation_failed'."""
    short_plan = "# Short\n\n- Step"
    ctx = _draft_pr_context(
        tmp_path=tmp_path,
        fake_claude=FakeClaudeInstallation.for_test(plans={"short": short_plan}),
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 2
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "validation_failed"


def test_draft_pr_session_deduplication(tmp_path: Path) -> None:
    """Second call with same session_id: skipped_duplicate=True."""
    ctx = _draft_pr_context(tmp_path=tmp_path)
    runner = CliRunner()
    session_id = "dedup-session"

    # First call creates the plan
    result1 = runner.invoke(
        plan_save,
        ["--format", "json", "--session-id", session_id],
        obj=ctx,
    )
    assert result1.exit_code == 0, f"First call failed: {result1.output}"
    output1 = json.loads(result1.output)
    assert output1["success"] is True
    assert "skipped_duplicate" not in output1

    # Second call with same session_id should detect duplicate
    result2 = runner.invoke(
        plan_save,
        ["--format", "json", "--session-id", session_id],
        obj=ctx,
    )
    assert result2.exit_code == 0, f"Second call failed: {result2.output}"
    output2 = json.loads(result2.output)
    assert output2["success"] is True
    assert output2["skipped_duplicate"] is True


def test_draft_pr_plan_file_priority(tmp_path: Path) -> None:
    """--plan-file takes priority over claude_installation."""
    plan_file = tmp_path / "custom-plan.md"
    plan_file.write_text(
        "# Custom Plan\n\nThis is a custom plan from a file that should take priority.\n\n"
        "- Step 1: Custom step\n- Step 2: Another custom step",
        encoding="utf-8",
    )
    ctx = _draft_pr_context(tmp_path=tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--plan-file", str(plan_file)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["title"] == "Custom Plan"


def test_draft_pr_objective_issue_metadata(tmp_path: Path) -> None:
    """--objective-issue 123 includes in branch name and metadata."""
    ctx = _draft_pr_context(tmp_path=tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--objective-issue", "123"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # Branch name should include objective ID
    assert "O123" in output["branch_name"]
