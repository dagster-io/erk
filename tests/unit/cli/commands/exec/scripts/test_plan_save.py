"""Unit tests for plan-save command (draft PR creation)."""

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
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR

# Valid plan content that passes validation (100+ chars with structure)
VALID_PLAN_CONTENT = """# Feature Plan

This plan describes the implementation of a new feature.

- Step 1: Set up the environment
- Step 2: Implement the core logic
- Step 3: Add tests and documentation"""


def _planned_pr_context(
    *,
    tmp_path: Path,
    fake_github: FakeGitHub | None = None,
    fake_git: FakeGit | None = None,
    fake_claude: FakeClaudeInstallation | None = None,
    monkeypatch: pytest.MonkeyPatch,
) -> ErkContext:
    """Build an ErkContext configured for planned-PR plan backend."""
    if fake_git is None:
        fake_git = FakeGit(current_branches={tmp_path: "main"})
    if fake_github is None:
        fake_github = FakeGitHub()
    if fake_claude is None:
        fake_claude = FakeClaudeInstallation.for_test(plans={"plan": VALID_PLAN_CONTENT})

    monkeypatch.setenv("ERK_PLAN_BACKEND", "planned_pr")
    return context_for_test(
        github=fake_github,
        git=fake_git,
        claude_installation=fake_claude,
        cwd=tmp_path,
        repo_root=tmp_path,
    )


def test_planned_pr_success_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Happy path: exit 0, JSON output has success/issue_number/branch_name."""
    ctx = _planned_pr_context(tmp_path=tmp_path, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "plan_number" in output
    assert "branch_name" in output
    assert output["branch_name"].startswith("plnd/")
    assert output["plan_backend"] == "planned_pr"


def test_planned_pr_success_display(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Display format: output contains 'Plan saved as planned PR'."""
    ctx = _planned_pr_context(tmp_path=tmp_path, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(
        plan_save, ["--format", "display", "--branch-slug", "test-slug"], obj=ctx
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "Plan saved as planned PR" in result.output
    assert "Title: [erk-plan] Feature Plan" in result.output
    assert "Branch: plnd/" in result.output
    assert "erk br co" in result.output
    assert "plnd/" in result.output  # branch name appears in checkout command


def test_planned_pr_no_plan_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty claude_installation: exit code 1."""
    ctx = _planned_pr_context(
        tmp_path=tmp_path,
        fake_claude=FakeClaudeInstallation.for_test(),
        monkeypatch=monkeypatch,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No plan found" in output["error"]


def test_planned_pr_validation_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Short plan: exit code 2, error_type='validation_failed'."""
    short_plan = "# Short\n\n- Step"
    ctx = _planned_pr_context(
        tmp_path=tmp_path,
        fake_claude=FakeClaudeInstallation.for_test(plans={"short": short_plan}),
        monkeypatch=monkeypatch,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 2
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "validation_failed"


def test_planned_pr_session_deduplication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Second call with same session_id: skipped_duplicate=True."""
    ctx = _planned_pr_context(tmp_path=tmp_path, monkeypatch=monkeypatch)
    runner = CliRunner()
    session_id = "dedup-session"

    # First call creates the plan
    result1 = runner.invoke(
        plan_save,
        ["--format", "json", "--session-id", session_id, "--branch-slug", "test-slug"],
        obj=ctx,
    )
    assert result1.exit_code == 0, f"First call failed: {result1.output}"
    output1 = json.loads(result1.output)
    assert output1["success"] is True
    assert "skipped_duplicate" not in output1

    # Second call with same session_id should detect duplicate
    result2 = runner.invoke(
        plan_save,
        ["--format", "json", "--session-id", session_id, "--branch-slug", "test-slug"],
        obj=ctx,
    )
    assert result2.exit_code == 0, f"Second call failed: {result2.output}"
    output2 = json.loads(result2.output)
    assert output2["success"] is True
    assert output2["skipped_duplicate"] is True
    assert output2["plan_backend"] == "planned_pr"
    # branch_name should be included from the branch marker saved during first call
    assert "branch_name" in output2
    assert output2["branch_name"] == output1["branch_name"]


def test_planned_pr_plan_file_priority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--plan-file takes priority over claude_installation."""
    plan_file = tmp_path / "custom-plan.md"
    plan_file.write_text(
        "# Custom Plan\n\nThis is a custom plan from a file that should take priority.\n\n"
        "- Step 1: Custom step\n- Step 2: Another custom step",
        encoding="utf-8",
    )
    ctx = _planned_pr_context(tmp_path=tmp_path, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--plan-file", str(plan_file), "--branch-slug", "test-slug"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["title"] == "[erk-plan] Custom Plan"


def test_planned_pr_objective_issue_from_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Objective context marker links plan to objective via branch name, metadata, and ref.json."""
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    # Create objective-context marker
    session_id = "marker-session"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    (marker_dir / "objective-context.marker").write_text("123", encoding="utf-8")

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--session-id", session_id, "--branch-slug", "test-slug"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    # Parse JSON from output (skip stderr lines mixed in by CliRunner)
    json_line = next(line for line in result.output.strip().splitlines() if line.startswith("{"))
    output = json.loads(json_line)
    assert output["success"] is True
    # Branch name should include objective ID
    assert "O123" in output["branch_name"]
    # objective_issue in JSON output
    assert output["objective_issue"] == 123
    # ref.json content should include objective_id (via branch commit, no filesystem)
    assert len(fake_git.branch_commits) == 1
    ref_json = json.loads(fake_git.branch_commits[0].files[f"{IMPL_CONTEXT_DIR}/ref.json"])
    assert ref_json["objective_id"] == 123


def test_planned_pr_no_objective_without_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a marker, objective_issue is null in output."""
    ctx = _planned_pr_context(tmp_path=tmp_path, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["objective_issue"] is None


def test_planned_pr_does_not_checkout_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """plan-save uses git plumbing to commit without checking out the plan branch."""
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        remote_branches={tmp_path: ["origin/feature-branch"]},
    )
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    # No checkouts at all — gt track accepts branch positionally, and
    # the plan commit uses git plumbing. No checkout/restore cycle needed.
    assert len(fake_git.checked_out_branches) == 0


def test_planned_pr_commits_plan_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """plan-save commits plan.md to the plan branch via git plumbing."""
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    # Verify branch commit was created with impl-context files (via git plumbing)
    assert len(fake_git.branch_commits) == 1
    branch_commit = fake_git.branch_commits[0]
    assert f"{IMPL_CONTEXT_DIR}/plan.md" in branch_commit.files
    assert f"{IMPL_CONTEXT_DIR}/ref.json" in branch_commit.files
    assert "Feature Plan" in branch_commit.message
    assert branch_commit.branch.startswith("plnd/")
    # Verify plan content
    assert "Feature Plan" in branch_commit.files[f"{IMPL_CONTEXT_DIR}/plan.md"]
    # Verify ref.json content
    ref_data = json.loads(branch_commit.files[f"{IMPL_CONTEXT_DIR}/ref.json"])
    assert ref_data["provider"] == "github-draft-pr"
    assert ref_data["title"] == "Feature Plan"
    assert "url" not in ref_data
    # No regular commits should exist (git plumbing bypasses stage+commit)
    assert len(fake_git.commits) == 0


def test_planned_pr_trunk_branch_passes_through_to_pr_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When on trunk, trunk_branch flows through metadata to PR base."""
    fake_git = FakeGit(current_branches={tmp_path: "master"}, trunk_branches={tmp_path: "master"})
    fake_github = FakeGitHub()
    ctx = _planned_pr_context(
        tmp_path=tmp_path,
        fake_git=fake_git,
        fake_github=fake_github,
        monkeypatch=monkeypatch,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert len(fake_github.created_prs) == 1
    assert fake_github.created_prs[0][3] == "master"


def test_planned_pr_tracks_branch_with_graphite_on_trunk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When on trunk, plan branch is tracked with trunk as Graphite parent."""
    fake_git = FakeGit(current_branches={tmp_path: "master"}, trunk_branches={tmp_path: "master"})
    fake_graphite = FakeGraphite()
    monkeypatch.setenv("ERK_PLAN_BACKEND", "planned_pr")
    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        claude_installation=FakeClaudeInstallation.for_test(plans={"plan": VALID_PLAN_CONTENT}),
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    branch_name = output["branch_name"]

    # On trunk: branch is created from origin/trunk, so Graphite parent should be trunk
    assert len(fake_graphite.track_branch_calls) == 1
    tracked_call = fake_graphite.track_branch_calls[0]
    assert tracked_call[0] == tmp_path  # repo_root
    assert tracked_call[1] == branch_name  # branch_name
    assert tracked_call[2] == "master"  # parent_branch (trunk used as base)


def test_planned_pr_branch_stacked_on_current_feature_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plan branch is stacked on current feature branch, not trunk."""
    # Current branch is a feature branch, NOT trunk — and pushed to remote
    fake_git = FakeGit(
        current_branches={tmp_path: "feature/my-work"},
        trunk_branches={tmp_path: "master"},
        remote_branches={tmp_path: ["origin/feature/my-work"]},
    )
    fake_graphite = FakeGraphite()
    monkeypatch.setenv("ERK_PLAN_BACKEND", "planned_pr")
    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        claude_installation=FakeClaudeInstallation.for_test(plans={"plan": VALID_PLAN_CONTENT}),
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"

    # Graphite parent should be the current feature branch, NOT trunk
    assert len(fake_graphite.track_branch_calls) == 1
    tracked_call = fake_graphite.track_branch_calls[0]
    assert tracked_call[2] == "feature/my-work"  # parent_branch is current feature branch

    # Trunk should NOT be fetched (branch is based off local feature branch)
    assert ("origin", "master") not in fake_git.fetched_branches


def test_planned_pr_feature_branch_creates_correct_pr_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When on a feature branch pushed to remote, the PR base is the feature branch."""
    fake_git = FakeGit(
        current_branches={tmp_path: "feature/my-work"},
        trunk_branches={tmp_path: "master"},
        remote_branches={tmp_path: ["origin/feature/my-work"]},
    )
    fake_github = FakeGitHub()
    monkeypatch.setenv("ERK_PLAN_BACKEND", "planned_pr")
    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        claude_installation=FakeClaudeInstallation.for_test(plans={"plan": VALID_PLAN_CONTENT}),
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    # PR base should be the feature branch, not trunk
    assert len(fake_github.created_prs) == 1
    assert fake_github.created_prs[0][3] == "feature/my-work"


def test_planned_pr_unpushed_feature_branch_falls_back_to_trunk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When on a feature branch NOT pushed to remote, falls back to trunk as base."""
    fake_git = FakeGit(
        current_branches={tmp_path: "feature/unpushed"},
        trunk_branches={tmp_path: "master"},
        # No remote_branches — branch is not on remote
    )
    fake_github = FakeGitHub()
    monkeypatch.setenv("ERK_PLAN_BACKEND", "planned_pr")
    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        claude_installation=FakeClaudeInstallation.for_test(plans={"plan": VALID_PLAN_CONTENT}),
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    # PR base should be trunk (master), not the unpushed feature branch
    assert len(fake_github.created_prs) == 1
    assert fake_github.created_prs[0][3] == "master"
    # Plan branch should be created from origin/trunk
    plan_branch_creates = [
        (cwd, name, sp, f)
        for cwd, name, sp, f in fake_git.created_branches
        if name.startswith("plnd/")
    ]
    assert len(plan_branch_creates) == 1
    _, _, start_point, _ = plan_branch_creates[0]
    assert start_point == "origin/master"


def test_planned_pr_learn_branch_uses_trunk_as_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When on a learn/ branch, the PR base is trunk (not the learn branch)."""
    fake_git = FakeGit(
        current_branches={tmp_path: "learn/8163"},
        trunk_branches={tmp_path: "master"},
    )
    fake_github = FakeGitHub()
    monkeypatch.setenv("ERK_PLAN_BACKEND", "planned_pr")
    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        claude_installation=FakeClaudeInstallation.for_test(plans={"plan": VALID_PLAN_CONTENT}),
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    # PR base should be trunk (master), not the ephemeral learn branch
    assert len(fake_github.created_prs) == 1
    assert fake_github.created_prs[0][3] == "master"


# --- Title validation rejection tests (planned-PR path) ---

# Plan content with no H1 heading → extract_title_from_plan returns "Untitled Plan"
_UNTITLED_PLAN_CONTENT = (
    "This plan has no heading so extract_title_from_plan"
    ' returns "Untitled Plan".\n\n'
    "- Step 1: Set up the environment\n"
    "- Step 2: Implement the core logic\n"
    "- Step 3: Add tests and documentation\n"
    "- Step 4: More content to pass length validation"
)


_EMOJI_ONLY_TITLE_PLAN = """# 🚀🎉

This plan has an emoji-only title which should fail validation.

- Step 1: Set up the environment
- Step 2: Implement the core logic
- Step 3: Add tests and documentation"""


def test_planned_pr_rejects_untitled_plan_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Planned-PR save rejects plan with fallback title 'Untitled Plan'."""
    ctx = _planned_pr_context(
        tmp_path=tmp_path,
        fake_claude=FakeClaudeInstallation.for_test(plans={"untitled": _UNTITLED_PLAN_CONTENT}),
        monkeypatch=monkeypatch,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 2
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "validation_failed"
    assert "agent_guidance" in output


def test_planned_pr_rejects_emoji_only_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Planned-PR save rejects plan with emoji-only title."""
    ctx = _planned_pr_context(
        tmp_path=tmp_path,
        fake_claude=FakeClaudeInstallation.for_test(plans={"emoji": _EMOJI_ONLY_TITLE_PLAN}),
        monkeypatch=monkeypatch,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 2
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "validation_failed"


def test_planned_pr_rejects_untitled_plan_display(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Planned-PR save shows error message for invalid title in display format."""
    ctx = _planned_pr_context(
        tmp_path=tmp_path,
        fake_claude=FakeClaudeInstallation.for_test(plans={"untitled": _UNTITLED_PLAN_CONTENT}),
        monkeypatch=monkeypatch,
    )
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "display"], obj=ctx)

    assert result.exit_code == 2
    assert "Invalid plan title" in result.output


def test_planned_pr_branch_slug_provided(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When --branch-slug is provided, branch name incorporates that slug."""
    ctx = _planned_pr_context(tmp_path=tmp_path, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--branch-slug", "my-custom-slug"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "my-custom-slug" in output["branch_name"]


def test_planned_pr_objective_from_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--objective flag links plan to objective via branch name, metadata, and ref.json."""
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--branch-slug", "test-slug", "--objective", "456"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    json_line = next(line for line in result.output.strip().splitlines() if line.startswith("{"))
    output = json.loads(json_line)
    assert output["success"] is True
    assert "O456" in output["branch_name"]
    assert output["objective_issue"] == 456
    # ref.json should include objective_id
    ref_json = json.loads(fake_git.branch_commits[0].files[f"{IMPL_CONTEXT_DIR}/ref.json"])
    assert ref_json["objective_id"] == 456


def test_planned_pr_objective_flag_overrides_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--objective flag takes precedence over the session marker."""
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    # Create objective-context marker with value 100
    session_id = "override-session"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    (marker_dir / "objective-context.marker").write_text("100", encoding="utf-8")

    # Pass --objective=200, which should override the marker value of 100
    result = runner.invoke(
        plan_save,
        [
            "--format",
            "json",
            "--session-id",
            session_id,
            "--branch-slug",
            "test-slug",
            "--objective",
            "200",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    json_line = next(line for line in result.output.strip().splitlines() if line.startswith("{"))
    output = json.loads(json_line)
    assert output["success"] is True
    # Flag value (200) should win over marker (100)
    assert output["objective_issue"] == 200
    assert "O200" in output["branch_name"]
    ref_json = json.loads(fake_git.branch_commits[0].files[f"{IMPL_CONTEXT_DIR}/ref.json"])
    assert ref_json["objective_id"] == 200


def test_planned_pr_branch_slug_missing_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When --branch-slug is not provided, exits with error and remediation message."""
    ctx = _planned_pr_context(tmp_path=tmp_path, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json"], obj=ctx)

    assert result.exit_code == 1
    assert "--branch-slug is required" in result.output


def test_planned_pr_includes_session_xml_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Session XML files from --session-xml-dir are committed under sessions/."""
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    xml_dir = tmp_path / "learn"
    xml_dir.mkdir()
    (xml_dir / "planning-abc123.xml").write_text("<session>planning</session>", encoding="utf-8")
    (xml_dir / "impl-def456.xml").write_text("<session>impl</session>", encoding="utf-8")

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--branch-slug", "test-slug", "--session-xml-dir", str(xml_dir)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert len(fake_git.branch_commits) == 1
    committed_files = fake_git.branch_commits[0].files
    assert f"{IMPL_CONTEXT_DIR}/sessions/impl-def456.xml" in committed_files
    assert f"{IMPL_CONTEXT_DIR}/sessions/planning-abc123.xml" in committed_files
    assert committed_files[f"{IMPL_CONTEXT_DIR}/sessions/planning-abc123.xml"] == (
        "<session>planning</session>"
    )
    assert committed_files[f"{IMPL_CONTEXT_DIR}/sessions/impl-def456.xml"] == (
        "<session>impl</session>"
    )


def test_planned_pr_session_xml_dir_only_includes_xml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only .xml files are committed from the session XML directory."""
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    xml_dir = tmp_path / "learn"
    xml_dir.mkdir()
    (xml_dir / "session.xml").write_text("<session/>", encoding="utf-8")
    (xml_dir / "comments.json").write_text("{}", encoding="utf-8")
    (xml_dir / "notes.txt").write_text("notes", encoding="utf-8")

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--branch-slug", "test-slug", "--session-xml-dir", str(xml_dir)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    committed_files = fake_git.branch_commits[0].files
    session_paths = [k for k in committed_files if "sessions/" in k]
    assert len(session_paths) == 1
    assert f"{IMPL_CONTEXT_DIR}/sessions/session.xml" in committed_files


def test_planned_pr_without_session_xml_dir_backward_compat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --session-xml-dir, only plan.md and ref.json are committed."""
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(plan_save, ["--format", "json", "--branch-slug", "test-slug"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    committed_files = fake_git.branch_commits[0].files
    assert len(committed_files) == 2
    assert f"{IMPL_CONTEXT_DIR}/plan.md" in committed_files
    assert f"{IMPL_CONTEXT_DIR}/ref.json" in committed_files


# --- --current-branch flag tests ---


def test_current_branch_skips_branch_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--current-branch uses current branch directly without creating a new one."""
    fake_git = FakeGit(current_branches={tmp_path: "my-feature-branch"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--current-branch"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["branch_name"] == "my-feature-branch"
    # No new branches should be created
    assert len(fake_git.created_branches) == 0


def test_current_branch_does_not_require_branch_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--current-branch does not require --branch-slug."""
    fake_git = FakeGit(current_branches={tmp_path: "my-feature-branch"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    # No --branch-slug provided, but --current-branch should make that OK
    result = runner.invoke(
        plan_save,
        ["--format", "json", "--current-branch"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True


def test_current_branch_sets_base_to_trunk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--current-branch sets the PR base to trunk."""
    fake_git = FakeGit(
        current_branches={tmp_path: "my-feature-branch"},
        trunk_branches={tmp_path: "master"},
    )
    fake_github = FakeGitHub()
    ctx = _planned_pr_context(
        tmp_path=tmp_path,
        fake_git=fake_git,
        fake_github=fake_github,
        monkeypatch=monkeypatch,
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--current-branch"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    # PR base should be trunk
    assert len(fake_github.created_prs) == 1
    assert fake_github.created_prs[0][3] == "master"


def test_current_branch_writes_files_to_working_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--current-branch writes impl-context files to disk and stages them."""
    fake_git = FakeGit(current_branches={tmp_path: "my-feature-branch"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--current-branch"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    # Files should exist on disk
    plan_file = tmp_path / IMPL_CONTEXT_DIR / "plan.md"
    ref_file = tmp_path / IMPL_CONTEXT_DIR / "ref.json"
    assert plan_file.exists(), "plan.md should be written to working tree"
    assert ref_file.exists(), "ref.json should be written to working tree"
    assert "Feature Plan" in plan_file.read_text(encoding="utf-8")
    # Files should be staged
    assert f"{IMPL_CONTEXT_DIR}/plan.md" in fake_git.staged_files
    assert f"{IMPL_CONTEXT_DIR}/ref.json" in fake_git.staged_files


def test_current_branch_creates_current_branch_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--current-branch creates plan-saved-current-branch marker, not regular plan-saved."""
    fake_git = FakeGit(current_branches={tmp_path: "my-feature-branch"})
    ctx = _planned_pr_context(tmp_path=tmp_path, fake_git=fake_git, monkeypatch=monkeypatch)
    runner = CliRunner()
    session_id = "current-branch-session"

    result = runner.invoke(
        plan_save,
        ["--format", "json", "--current-branch", "--session-id", session_id],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    # Current-branch marker should exist
    current_branch_marker = marker_dir / "exit-plan-mode-hook.plan-saved-current-branch.marker"
    assert current_branch_marker.exists(), "plan-saved-current-branch marker should exist"
    # Regular plan-saved marker should NOT exist
    regular_marker = marker_dir / "exit-plan-mode-hook.plan-saved.marker"
    assert not regular_marker.exists(), "regular plan-saved marker should NOT exist"
    # Issue and branch markers should still exist
    assert (marker_dir / "plan-saved-issue.marker").exists()
    assert (marker_dir / "plan-saved-branch.marker").exists()
