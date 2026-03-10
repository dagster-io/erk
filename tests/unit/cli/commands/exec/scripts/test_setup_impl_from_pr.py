"""Tests for erk exec setup-impl-from-pr command."""

import json
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.setup_impl_from_pr import (
    _get_current_branch,
    create_impl_context_from_pr,
    setup_impl_from_pr,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.remote_ops.types import PullRebaseError
from erk_shared.impl_folder import get_impl_dir, save_plan_ref
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.graphite import FakeGraphite
from tests.fakes.gateway.time import FakeTime
from tests.fakes.tests.shared_context import context_for_test

BRANCH = "test/branch"
"""Test branch name used across tests."""


class TestGetCurrentBranch:
    """Tests for the _get_current_branch helper function."""

    def test_returns_branch_name(self, tmp_path: Path) -> None:
        """Returns current branch name when on a branch."""
        git = FakeGit(current_branches={tmp_path: "feature-branch"})
        result = _get_current_branch(git, tmp_path)
        assert result == "feature-branch"

    def test_raises_on_detached_head(self, tmp_path: Path) -> None:
        """Raises ClickException when in detached HEAD state."""
        git = FakeGit(current_branches={tmp_path: None})
        with pytest.raises(click.ClickException) as exc_info:
            _get_current_branch(git, tmp_path)
        assert "detached HEAD" in str(exc_info.value)


class TestSetupImplFromPrValidation:
    """Tests for validation in setup-impl-from-pr command."""

    def test_missing_issue_shows_error(self, tmp_path: Path) -> None:
        """Command fails gracefully when issue cannot be found."""
        runner = CliRunner()

        # Create a minimal context
        ctx = ErkContext.for_test(cwd=tmp_path)

        # The command requires a GitHub issue that doesn't exist
        # This test verifies the error handling for missing issues
        result = runner.invoke(
            setup_impl_from_pr,
            ["999999"],  # Non-existent issue number
            obj=ctx,
            catch_exceptions=False,
        )

        # Command should fail with exit code 1
        # (actual behavior depends on whether we're mocking GitHub or not)
        # For this unit test, we're primarily testing the CLI interface
        assert result.exit_code != 0 or "error" in result.output.lower()


class TestSetupImplFromPrNoImplFlag:
    """Tests for --no-impl flag in setup-impl-from-pr command."""

    def test_no_impl_flag_is_accepted(self, tmp_path: Path) -> None:
        """Verify --no-impl flag is accepted by the CLI.

        Note: Full integration testing of --no-impl behavior requires
        refactoring the command to use DI for GitHubIssues. This test
        just verifies the flag is accepted without syntax errors.
        """
        runner = CliRunner()

        # Create a minimal context
        ctx = ErkContext.for_test(cwd=tmp_path)

        # The command will fail because it can't reach GitHub,
        # but we verify the flag is accepted without a click.UsageError
        result = runner.invoke(
            setup_impl_from_pr,
            ["42", "--no-impl"],
            obj=ctx,
        )

        # Verify no usage error (flag was accepted)
        assert "Usage:" not in result.output, "--no-impl flag should be accepted"
        assert "Error: No such option:" not in result.output, "--no-impl should be a valid option"

        # The command should fail due to GitHub access, not CLI parsing
        # (exit code 1 is expected when GitHub fails)
        assert result.exit_code == 1


# =============================================================================
# Planned-PR plan branch teleport tests
# =============================================================================


def _make_planned_pr_backend(
    tmp_path: Path,
    plan_branch: str,
) -> tuple[PlannedPRBackend, int]:
    """Create a PlannedPRBackend with one plan, returning (backend, pr_number).

    Unlike _make_planned_pr_context, this does not create a full ErkContext,
    allowing the caller to build their own context (e.g., without github).
    """
    fake_github = FakeLocalGitHub()
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())
    plan_result = backend.create_plan(
        repo_root=tmp_path,
        title="My Plan",
        content="# Plan\n\nImplement something.",
        labels=("erk-pr",),
        metadata={"branch_name": plan_branch},
        summary=None,
    )
    pr_number = int(plan_result.pr_id)
    return backend, pr_number


def _make_planned_pr_context(
    tmp_path: Path,
    plan_branch: str,
    *,
    fake_git: FakeGit | None = None,
    fake_graphite: FakeGraphite | None = None,
) -> tuple[ErkContext, int]:
    """Create an ErkContext configured for planned-PR plan backend with shared FakeLocalGitHub.

    The FakeLocalGitHub is shared between the PlannedPRBackend and the context,
    so that both plan_backend.get_provider_name() and github.get_pr() work.

    Returns (context, pr_number).
    """
    fake_github = FakeLocalGitHub()
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())
    plan_result = backend.create_plan(
        repo_root=tmp_path,
        title="My Plan",
        content="# Plan\n\nImplement something.",
        labels=("erk-pr",),
        metadata={"branch_name": plan_branch},
        summary=None,
    )
    pr_number = int(plan_result.pr_id)

    if fake_git is None:
        fake_git = FakeGit(current_branches={tmp_path: "master"})
    if fake_graphite is None:
        fake_graphite = FakeGraphite()

    ctx = context_for_test(
        github=fake_github,
        git=fake_git,
        graphite=fake_graphite,
        cwd=tmp_path,
        repo_root=tmp_path,
        plan_store=backend,
    )
    return ctx, pr_number


def test_planned_pr_plan_uses_plan_branch_name(tmp_path: Path) -> None:
    """Planned-PR plan with branch_name checks out the plan branch and teleports from remote."""
    plan_branch = "my-plan-branch-02-19"
    fake_git = FakeGit(
        current_branches={tmp_path: "master"},
        local_branches={tmp_path: [plan_branch]},
    )
    ctx, pr_number = _make_planned_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_pr,
        [str(pr_number), "--no-impl"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Fetch was called for the plan branch
    assert fake_git.fetched_branches == [("origin", plan_branch)]

    # Branch was checked out
    assert (tmp_path, plan_branch) in fake_git.checked_out_branches

    # Pull-rebase was called to sync with remote
    assert fake_git.pull_rebase_calls == [(tmp_path, "origin", plan_branch)]

    # Output contains the plan branch name
    output_lines = result.output.strip().split("\n")
    json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
    output = json.loads(json_line)
    assert output["success"] is True
    assert output["branch"] == plan_branch


def test_planned_pr_plan_already_on_plan_branch(tmp_path: Path) -> None:
    """Already on the plan branch — no checkout needed, just fetch and pull-rebase."""
    plan_branch = "my-plan-branch-02-19"
    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},  # Already on the plan branch
    )
    ctx, pr_number = _make_planned_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_pr,
        [str(pr_number), "--no-impl"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Fetch was called
    assert fake_git.fetched_branches == [("origin", plan_branch)]

    # No checkout (already on the plan branch)
    assert all(b != plan_branch for _, b in fake_git.checked_out_branches)

    # Pull-rebase was called to sync
    assert fake_git.pull_rebase_calls == [(tmp_path, "origin", plan_branch)]

    assert f"Already on plan branch '{plan_branch}'" in result.output


def test_planned_pr_plan_skips_checkout_when_impl_exists(tmp_path: Path) -> None:
    """When .impl/ already has a matching plan_id, skip branch switching.

    In CI, the workflow checks out an implementation branch and pre-populates
    .impl/ with plan-ref.json. setup-impl-from-pr should detect this and
    stay on the current branch instead of switching to the plan branch.
    """
    plan_branch = "plan-my-feature-02-19"
    ci_branch = "P100-my-feature-impl-02-19-1430"
    backend, pr_number = _make_planned_pr_backend(tmp_path, plan_branch)

    fake_git = FakeGit(
        current_branches={tmp_path: ci_branch},
        local_branches={tmp_path: [ci_branch]},
    )
    fake_graphite = FakeGraphite()

    # Pre-create branch-scoped impl dir with matching plan_id (simulating CI setup).
    impl_dir = get_impl_dir(tmp_path, branch_name=ci_branch)
    impl_dir.mkdir(parents=True)
    save_plan_ref(
        impl_dir,
        provider="github",
        plan_id=str(pr_number),
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}",
        labels=("erk-pr",),
        objective_id=None,
        node_ids=None,
    )

    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        cwd=tmp_path,
        repo_root=tmp_path,
        plan_store=backend,
    )

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_pr,
        [str(pr_number)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # No fetch or checkout should have happened — we skipped branch setup entirely
    assert len(fake_git.fetched_branches) == 0
    assert len(fake_git.checked_out_branches) == 0
    assert len(fake_git.pull_rebase_calls) == 0

    # Output should indicate we skipped branch setup
    assert f"Found existing impl dir for plan #{pr_number}, skipping branch setup" in result.output

    # JSON output should have the CI branch, not the plan branch
    output_lines = result.output.strip().split("\n")
    json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
    output = json.loads(json_line)
    assert output["success"] is True
    assert output["branch"] == ci_branch  # Stayed on CI branch, not plan branch


def test_planned_pr_plan_sync_failure_reports_error(tmp_path: Path) -> None:
    """Pull-rebase failure exits with code 1 and reports error JSON."""
    plan_branch = "my-plan-branch-02-19"
    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},  # Already on the plan branch
        pull_rebase_error=PullRebaseError(message="Rebase conflict"),
    )
    ctx, pr_number = _make_planned_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_pr,
        [str(pr_number), "--no-impl"],
        obj=ctx,
    )

    assert result.exit_code == 1

    # Error JSON is present in output
    json_lines = [line for line in result.output.strip().split("\n") if line.startswith("{")]
    assert json_lines, "Expected JSON error output in command output"
    error_data = json.loads(json_lines[0])
    assert error_data["success"] is False
    assert error_data["error"] == "pull_rebase_failed"
    assert "Rebase conflict" in error_data["message"]


# =============================================================================
# Planned-PR plan: .erk/impl-context/ local file reading
# =============================================================================


def test_planned_pr_reads_from_impl_context_when_present(tmp_path: Path) -> None:
    """Planned-PR plan reads plan content from .erk/impl-context/ after checkout."""
    plan_branch = "plan-test-local-read-02-20"
    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},
    )
    ctx, pr_number = _make_planned_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    # Create .erk/impl-context/ with plan content (simulates committed files on branch)
    impl_context_dir = tmp_path / IMPL_CONTEXT_DIR
    impl_context_dir.mkdir(parents=True)
    (impl_context_dir / "plan.md").write_text(
        "# Local Plan\n\nFrom impl-context.", encoding="utf-8"
    )
    (impl_context_dir / "ref.json").write_text(
        json.dumps({"provider": "github-draft-pr", "title": "Local Plan", "objective_id": 42}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_pr,
        [str(pr_number)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Impl folder was created with local plan content (not PR body content)
    impl_plan = tmp_path / ".erk" / "impl-context" / plan_branch / "plan.md"
    assert impl_plan.exists()
    assert "Local Plan" in impl_plan.read_text(encoding="utf-8")
    assert "From impl-context" in impl_plan.read_text(encoding="utf-8")

    # .erk/impl-context/ is NOT deleted here — Step 2d in plan-implement.md
    # handles git rm + commit + push after setup_impl_from_pr completes
    assert impl_context_dir.exists()

    # Output JSON has correct metadata
    output_lines = result.output.strip().split("\n")
    json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
    output = json.loads(json_line)
    assert output["success"] is True
    assert output["pr_title"] == "Local Plan"


def test_planned_pr_reads_objective_id_from_ref_json(tmp_path: Path) -> None:
    """objective_id from ref.json is passed to save_plan_ref."""
    plan_branch = "plan-test-objective-02-20"
    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},
    )
    ctx, pr_number = _make_planned_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    # Create .erk/impl-context/ with objective_id
    impl_context_dir = tmp_path / IMPL_CONTEXT_DIR
    impl_context_dir.mkdir(parents=True)
    (impl_context_dir / "plan.md").write_text("# Plan with objective", encoding="utf-8")
    (impl_context_dir / "ref.json").write_text(
        json.dumps({"provider": "github-draft-pr", "title": "Plan", "objective_id": 99}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_pr,
        [str(pr_number)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify ref.json in branch-scoped impl dir has the objective_id
    plan_ref_path = tmp_path / ".erk" / "impl-context" / plan_branch / "ref.json"
    assert plan_ref_path.exists()
    plan_ref = json.loads(plan_ref_path.read_text(encoding="utf-8"))
    assert plan_ref["objective_id"] == 99
    assert plan_ref["provider"] == "github-draft-pr"


def test_planned_pr_falls_back_to_pr_body_when_no_impl_context(tmp_path: Path) -> None:
    """When .erk/impl-context/ doesn't exist, extract plan from PR body."""
    plan_branch = "plan-test-fallback-02-20"
    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},
    )
    ctx, pr_number = _make_planned_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    # No .erk/impl-context/ directory — triggers fallback to PR body extraction

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_pr,
        [str(pr_number)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Impl folder was created with plan content extracted from PR body
    impl_plan = tmp_path / ".erk" / "impl-context" / plan_branch / "plan.md"
    assert impl_plan.exists()
    # The PR body was created via _make_planned_pr_context with content
    # "# Plan\n\nImplement something."
    assert "Plan" in impl_plan.read_text(encoding="utf-8")
    assert "Implement something" in impl_plan.read_text(encoding="utf-8")


# =============================================================================
# Direct tests for create_impl_context_from_pr()
# =============================================================================


def _invoke_create_impl_context(
    tmp_path: Path,
    plan_branch: str,
    *,
    impl_context_files: dict[str, str] | None = None,
) -> tuple[dict[str, str | int | bool | None], Path]:
    """Helper to invoke create_impl_context_from_pr() with a fake context.

    Returns (result_dict, impl_path).
    """
    fake_github = FakeLocalGitHub()
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())
    plan_result = backend.create_plan(
        repo_root=tmp_path,
        title="Test Plan Title",
        content="# Plan\n\nDo the thing.",
        labels=("erk-pr",),
        metadata={"branch_name": plan_branch},
        summary=None,
    )
    pr_number = int(plan_result.pr_id)

    fake_git = FakeGit(current_branches={tmp_path: plan_branch})
    ctx = context_for_test(
        github=fake_github,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
        plan_store=backend,
    )

    if impl_context_files is not None:
        impl_context_dir = tmp_path / IMPL_CONTEXT_DIR
        impl_context_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in impl_context_files.items():
            (impl_context_dir / filename).write_text(content, encoding="utf-8")

    # create_impl_context_from_pr expects a click.Context with obj set
    runner = CliRunner()
    result_holder: list[dict[str, str | int | bool | None]] = []

    @click.command()
    @click.pass_context
    def _wrapper(click_ctx: click.Context) -> None:
        result = create_impl_context_from_pr(
            click_ctx,
            pr_number=pr_number,
            cwd=tmp_path,
            branch_name=plan_branch,
        )
        result_holder.append(result)

    invoke_result = runner.invoke(_wrapper, obj=ctx, catch_exceptions=False)
    assert invoke_result.exit_code == 0, f"Wrapper failed: {invoke_result.output}"
    impl_path = get_impl_dir(tmp_path, branch_name=plan_branch)
    return result_holder[0], impl_path


def test_create_impl_context_pr_not_found(tmp_path: Path) -> None:
    """create_impl_context_from_pr exits 1 when PR does not exist."""
    fake_github = FakeLocalGitHub()
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())
    fake_git = FakeGit(current_branches={tmp_path: "some-branch"})
    ctx = context_for_test(
        github=fake_github,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
        plan_store=backend,
    )

    runner = CliRunner()

    @click.command()
    @click.pass_context
    def _wrapper(click_ctx: click.Context) -> None:
        create_impl_context_from_pr(
            click_ctx,
            pr_number=9999,
            cwd=tmp_path,
            branch_name="some-branch",
        )

    result = runner.invoke(_wrapper, obj=ctx)
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_create_impl_context_ref_json_non_int_objective_id(tmp_path: Path) -> None:
    """Non-int objective_id in ref.json is ignored (stays None)."""
    result, impl_path = _invoke_create_impl_context(
        tmp_path,
        "plan-test-branch",
        impl_context_files={
            "plan.md": "# Plan\n\nContent.",
            "ref.json": json.dumps({"objective_id": "not-an-int", "title": "Good Title"}),
        },
    )
    assert result["success"] is True
    # objective_id was not an int, so ref.json should have null objective_id
    ref_data = json.loads((impl_path / "ref.json").read_text(encoding="utf-8"))
    assert ref_data["objective_id"] is None


def test_create_impl_context_ref_json_non_string_title(tmp_path: Path) -> None:
    """Non-string title in ref.json falls back to PR title."""
    result, _ = _invoke_create_impl_context(
        tmp_path,
        "plan-test-branch",
        impl_context_files={
            "plan.md": "# Plan\n\nContent.",
            "ref.json": json.dumps({"title": 12345}),
        },
    )
    assert result["success"] is True
    # Non-string title falls back to PR title
    assert result["pr_title"] == "Test Plan Title"


def test_create_impl_context_ref_json_non_list_node_ids(tmp_path: Path) -> None:
    """Non-list node_ids in ref.json is ignored (stays None)."""
    result, impl_path = _invoke_create_impl_context(
        tmp_path,
        "plan-test-branch",
        impl_context_files={
            "plan.md": "# Plan\n\nContent.",
            "ref.json": json.dumps({"node_ids": "not-a-list"}),
        },
    )
    assert result["success"] is True
    ref_data = json.loads((impl_path / "ref.json").read_text(encoding="utf-8"))
    assert ref_data.get("node_ids") is None


def test_create_impl_context_ref_json_missing_fields(tmp_path: Path) -> None:
    """ref.json with no relevant fields uses defaults."""
    result, impl_path = _invoke_create_impl_context(
        tmp_path,
        "plan-test-branch",
        impl_context_files={
            "plan.md": "# Plan\n\nContent.",
            "ref.json": json.dumps({"unrelated_key": "value"}),
        },
    )
    assert result["success"] is True
    assert result["pr_title"] == "Test Plan Title"  # Falls back to PR title
    ref_data = json.loads((impl_path / "ref.json").read_text(encoding="utf-8"))
    assert ref_data["objective_id"] is None
    assert ref_data.get("node_ids") is None


def test_create_impl_context_valid_ref_json(tmp_path: Path) -> None:
    """ref.json with valid fields extracts all metadata correctly."""
    result, impl_path = _invoke_create_impl_context(
        tmp_path,
        "plan-test-branch",
        impl_context_files={
            "plan.md": "# Plan\n\nContent.",
            "ref.json": json.dumps(
                {
                    "objective_id": 42,
                    "title": "Custom Title",
                    "node_ids": ["node-1", "node-2"],
                }
            ),
        },
    )
    assert result["success"] is True
    assert result["pr_title"] == "Custom Title"
    ref_data = json.loads((impl_path / "ref.json").read_text(encoding="utf-8"))
    assert ref_data["objective_id"] == 42
    assert ref_data["node_ids"] == ["node-1", "node-2"]


def test_planned_pr_pr_not_found_reports_error(tmp_path: Path) -> None:
    """When the PR doesn't exist, report an error."""
    # Create a PlannedPRBackend but don't create any PR
    fake_github = FakeLocalGitHub()
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())

    fake_git = FakeGit(current_branches={tmp_path: "master"})

    ctx = context_for_test(
        github=fake_github,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
        plan_store=backend,
    )

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_pr,
        ["9999"],
        obj=ctx,
    )

    assert result.exit_code == 1
    json_lines = [line for line in result.output.strip().split("\n") if line.startswith("{")]
    assert json_lines
    error_data = json.loads(json_lines[0])
    assert error_data["success"] is False
    assert "not found" in error_data["message"].lower()
