"""Unit tests for plan-save command (backend-aware dispatcher)."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_save import plan_save
from erk_shared.context.context import ErkContext
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.claude_installation.fake import FakeClaudeInstallation
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.graphite.fake import FakeGraphite

# Valid plan content that passes validation (100+ chars with structure)
VALID_PLAN_CONTENT = """# Feature Plan

This plan describes the implementation of a new feature.

- Step 1: Set up the environment
- Step 2: Implement the core logic
- Step 3: Add tests and documentation"""


@pytest.fixture(autouse=True)
def _use_draft_pr_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set ERK_PLAN_BACKEND to draft_pr for all tests in this module."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "draft_pr")


def _draft_pr_context(
    *,
    tmp_path: Path,
    fake_github: FakeGitHub | None = None,
    fake_git: FakeGit | None = None,
    fake_claude: FakeClaudeInstallation | None = None,
) -> ErkContext:
    """Build an ErkContext configured for draft-PR plan backend."""
    if fake_git is None:
        fake_git = FakeGit(current_branches={tmp_path: "main"})
    if fake_github is None:
        fake_github = FakeGitHub()
    if fake_claude is None:
        fake_claude = FakeClaudeInstallation.for_test(plans={"plan": VALID_PLAN_CONTENT})

    return context_for_test(
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
    assert output["plan_backend"] == "draft_pr"


def test_draft_pr_success_display(tmp_path: Path) -> None:
    """Display format: output contains 'Plan saved as draft PR'."""
    ctx = _draft_pr_context(tmp_path=tmp_path)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "display"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "Plan saved as draft PR" in result.output
    assert "Title: Feature Plan" in result.output
    assert "Branch: plan-" in result.output


def test_delegates_to_issue_when_not_draft_pr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ERK_PLAN_BACKEND="github" delegates to plan_save_to_issue."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "github")
    fake_issues = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    ctx = context_for_test(
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
    """--objective-issue 123 includes in branch name, metadata, and ref.json."""
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
    # ref.json should include objective_id
    ref_file = tmp_path / ".erk" / "branch-data" / "ref.json"
    assert ref_file.exists()
    ref_data = json.loads(ref_file.read_text(encoding="utf-8"))
    assert ref_data["objective_id"] == 123


def test_draft_pr_restores_original_branch(tmp_path: Path) -> None:
    """plan-save checks out plan branch for commit, then restores original."""
    fake_git = FakeGit(current_branches={tmp_path: "feature-branch"})
    ctx = _draft_pr_context(tmp_path=tmp_path, fake_git=fake_git)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    # Four checkouts: branch_manager.create_branch() does checkout+restore for gt track,
    # then plan_save does checkout+restore for committing plan file
    assert len(fake_git.checked_out_branches) == 4
    assert fake_git.checked_out_branches[0][1].startswith("plan-")  # for gt track
    assert fake_git.checked_out_branches[1] == (tmp_path, "feature-branch")  # restore
    assert fake_git.checked_out_branches[2][1].startswith("plan-")  # for plan commit
    assert fake_git.checked_out_branches[3] == (tmp_path, "feature-branch")  # final restore


def test_draft_pr_commits_plan_file(tmp_path: Path) -> None:
    """plan-save commits .erk/branch-data/plan.md to the plan branch."""
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = _draft_pr_context(tmp_path=tmp_path, fake_git=fake_git)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    # Verify commit was created with .erk/branch-data/ files
    assert len(fake_git.commits) == 1
    commit = fake_git.commits[0]
    assert ".erk/branch-data/plan.md" in commit.staged_files
    assert ".erk/branch-data/ref.json" in commit.staged_files
    assert "Feature Plan" in commit.message
    # Verify plan file was written
    plan_file = tmp_path / ".erk" / "branch-data" / "plan.md"
    assert plan_file.exists()
    assert "Feature Plan" in plan_file.read_text(encoding="utf-8")
    # Verify ref.json was written
    ref_file = tmp_path / ".erk" / "branch-data" / "ref.json"
    assert ref_file.exists()
    ref_data = json.loads(ref_file.read_text(encoding="utf-8"))
    assert ref_data["provider"] == "github-draft-pr"


def test_draft_pr_trunk_branch_passes_through_to_pr_base(tmp_path: Path) -> None:
    """trunk_branch detected by detect_trunk_branch flows through metadata to PR base."""
    fake_git = FakeGit(current_branches={tmp_path: "main"}, trunk_branches={tmp_path: "master"})
    fake_github = FakeGitHub()
    ctx = _draft_pr_context(tmp_path=tmp_path, fake_git=fake_git, fake_github=fake_github)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert len(fake_github.created_prs) == 1
    assert fake_github.created_prs[0][3] == "master"


def test_draft_pr_tracks_branch_with_graphite(tmp_path: Path) -> None:
    """Plan branch is tracked with Graphite so it can be used as a stack parent."""
    fake_git = FakeGit(current_branches={tmp_path: "main"}, trunk_branches={tmp_path: "master"})
    fake_graphite = FakeGraphite()
    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        claude_installation=FakeClaudeInstallation.for_test(plans={"plan": VALID_PLAN_CONTENT}),
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    branch_name = output["branch_name"]

    # Verify track_branch was called with the plan branch and current branch as parent
    # (branch_manager.create_branch uses base_branch as Graphite parent)
    assert len(fake_graphite.track_branch_calls) == 1
    tracked_call = fake_graphite.track_branch_calls[0]
    assert tracked_call[0] == tmp_path  # repo_root
    assert tracked_call[1] == branch_name  # branch_name
    assert tracked_call[2] == "main"  # parent_branch (current branch used as base)
