"""Tests for erk pr dispatch command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.github.metadata.core import MetadataBlock, render_metadata_block
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.impl_folder import build_plan_ref_json
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.planned_pr_lifecycle import build_plan_stage_body
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.fakes.gateway.graphite import FakeGraphite
from tests.fakes.gateway.time import FakeTime
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_dispatch_planned_pr_plan_triggers_workflow_with_planned_pr_backend() -> None:
    """Test that dispatching a planned-PR plan triggers workflow with pr_backend=planned_pr.

    Planned-PR plans already have a branch and PR. Dispatch should:
    - Validate the PR has the erk-plan label and is OPEN
    - Sync local branch ref to remote and commit impl-context via git plumbing
    - Trigger workflow with plan_backend="planned_pr" in inputs
    - NOT create a new branch or PR
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_branch = "draft-pr-plan-branch"

        # PR body with plan content in production metadata format
        plan_header = render_metadata_block(
            MetadataBlock(
                key="plan-header",
                data={
                    "schema_version": "2",
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "created_by": "testuser",
                    "branch_name": plan_branch,
                },
            )
        )
        pr_body = build_plan_stage_body(
            plan_header,
            "# Plan: Test Draft PR Plan\n\n- Step 1: Do something\n- Step 2: Do something else",
            summary=None,
        )

        pr_42 = PRDetails(
            number=42,
            url="https://github.com/test-owner/test-repo/pull/42",
            title="[erk-pr] Test Draft PR Plan",
            body=pr_body,
            state="OPEN",
            is_draft=True,
            base_ref_name="main",
            head_ref_name=plan_branch,
            is_cross_repository=False,
            mergeable="UNKNOWN",
            merge_state_status="UNKNOWN",
            owner="test-owner",
            repo="test-repo",
            labels=("erk-pr",),
        )

        fake_gh = FakeLocalGitHub(
            authenticated=True,
            polled_run_id="12345",
            pr_details={42: pr_42},
            prs_by_branch={plan_branch: pr_42},
        )
        fake_issues = FakeGitHubIssues()
        fake_time = FakeTime()

        # PlannedPRBackend makes get_provider_name() return "github-draft-pr"
        planned_pr_backend = PlannedPRBackend(fake_gh, fake_issues, time=fake_time)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={env.cwd: ["origin/main", f"origin/{plan_branch}"]},
            repository_roots={env.cwd: env.cwd},
            branch_heads={"main": "abc123", "origin/main": "abc123"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=[],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=fake_gh,
            issues=fake_issues,
            use_graphite=True,
            plan_store=planned_pr_backend,
        )

        result = runner.invoke(cli, ["pr", "dispatch", "42", "--base", "main"], obj=ctx)

        # Verify: workflow was triggered with plan_backend="planned_pr"
        assert len(fake_gh.triggered_workflows) >= 1, (
            f"Expected workflow trigger, got: {fake_gh.triggered_workflows}\n"
            f"Output: {result.output}"
        )
        _workflow_name, inputs, _ref = fake_gh.triggered_workflows[0]
        assert inputs["plan_backend"] == "planned_pr"
        assert inputs["plan_id"] == "42"
        assert inputs["branch_name"] == plan_branch

        # Verify: no new PR was created (planned-PR already exists)
        assert len(fake_gh.created_prs) == 0

        # Verify: expected output messages for git plumbing path
        assert "Syncing branch:" in result.output
        assert "Committing plan to branch..." in result.output
        assert "Workflow dispatched" in result.output

        # Verify: no warnings, dispatch metadata written successfully
        assert "Warning:" not in result.output
        assert "Dispatch metadata written" in result.output

        assert "Traceback" not in result.output


def _make_pr_42(*, plan_branch: str) -> PRDetails:
    """Build a standard PRDetails for plan PR #42 used by auto-detection tests."""
    plan_header = render_metadata_block(
        MetadataBlock(
            key="plan-header",
            data={
                "schema_version": "2",
                "created_at": "2024-01-01T00:00:00+00:00",
                "created_by": "testuser",
                "branch_name": plan_branch,
            },
        )
    )
    pr_body = build_plan_stage_body(
        plan_header,
        "# Plan: Auto-detect Test\n\n- Step 1: Do something",
        summary=None,
    )
    return PRDetails(
        number=42,
        url="https://github.com/test-owner/test-repo/pull/42",
        title="[erk-pr] Auto-detect Test",
        body=pr_body,
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name=plan_branch,
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="test-owner",
        repo="test-repo",
        labels=("erk-pr",),
    )


def test_dispatch_auto_detects_from_impl_folder() -> None:
    """Test auto-detection from branch-scoped .erk/impl-context/ directory."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_branch = "plnd/auto-detect-impl"
        pr_42 = _make_pr_42(plan_branch=plan_branch)

        # Create branch-scoped .erk/impl-context/<branch>/ with plan-ref.json
        from erk_shared.impl_folder import get_impl_dir

        impl_dir = get_impl_dir(env.cwd, branch_name="main")
        impl_dir.mkdir(parents=True, exist_ok=True)
        pr_ref_content = build_plan_ref_json(
            provider="github-draft-pr",
            pr_id="42",
            url="https://github.com/test-owner/test-repo/pull/42",
            labels=("erk-pr",),
            objective_id=None,
            node_ids=None,
        )
        (impl_dir / "plan-ref.json").write_text(pr_ref_content, encoding="utf-8")

        fake_gh = FakeLocalGitHub(
            authenticated=True,
            polled_run_id="12345",
            pr_details={42: pr_42},
            prs_by_branch={plan_branch: pr_42},
        )
        fake_issues = FakeGitHubIssues()
        fake_time = FakeTime()
        planned_pr_backend = PlannedPRBackend(fake_gh, fake_issues, time=fake_time)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={env.cwd: ["origin/main", f"origin/{plan_branch}"]},
            repository_roots={env.cwd: env.cwd},
            branch_heads={"main": "abc123", "origin/main": "abc123"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "main": BranchMetadata(
                    name="main", parent=None, children=[], is_trunk=True, commit_sha=None
                ),
            },
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=fake_gh,
            issues=fake_issues,
            use_graphite=True,
            plan_store=planned_pr_backend,
        )

        # Invoke WITHOUT issue number argument
        result = runner.invoke(cli, ["pr", "dispatch", "--base", "main"], obj=ctx)

        assert "Auto-detected PR #42 from context" in result.output
        assert len(fake_gh.triggered_workflows) >= 1, (
            f"Expected workflow trigger, got: {fake_gh.triggered_workflows}\n"
            f"Output: {result.output}"
        )
        _workflow_name, inputs, _ref = fake_gh.triggered_workflows[0]
        assert inputs["plan_id"] == "42"
        assert "Traceback" not in result.output


def test_dispatch_auto_detects_from_impl_context() -> None:
    """Test auto-detection from branch-scoped .erk/impl-context/<branch>/ directory."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_branch = "plnd/auto-detect-context"
        pr_42 = _make_pr_42(plan_branch=plan_branch)

        # Create branch-scoped .erk/impl-context/main/ with ref.json and plan.md
        # resolve_impl_dir() requires plan.md to exist for discovery (step 3)
        impl_context_dir = env.cwd / ".erk" / "impl-context" / "main"
        impl_context_dir.mkdir(parents=True)
        pr_ref_content = build_plan_ref_json(
            provider="github-draft-pr",
            pr_id="42",
            url="https://github.com/test-owner/test-repo/pull/42",
            labels=("erk-pr",),
            objective_id=None,
            node_ids=None,
        )
        (impl_context_dir / "ref.json").write_text(pr_ref_content, encoding="utf-8")
        (impl_context_dir / "plan.md").write_text("# Test plan\n", encoding="utf-8")

        fake_gh = FakeLocalGitHub(
            authenticated=True,
            polled_run_id="12345",
            pr_details={42: pr_42},
            prs_by_branch={plan_branch: pr_42},
        )
        fake_issues = FakeGitHubIssues()
        fake_time = FakeTime()
        planned_pr_backend = PlannedPRBackend(fake_gh, fake_issues, time=fake_time)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={env.cwd: ["origin/main", f"origin/{plan_branch}"]},
            repository_roots={env.cwd: env.cwd},
            branch_heads={"main": "abc123", "origin/main": "abc123"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "main": BranchMetadata(
                    name="main", parent=None, children=[], is_trunk=True, commit_sha=None
                ),
            },
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=fake_gh,
            issues=fake_issues,
            use_graphite=True,
            plan_store=planned_pr_backend,
        )

        result = runner.invoke(cli, ["pr", "dispatch", "--base", "main"], obj=ctx)

        assert "Auto-detected PR #42 from context" in result.output
        assert len(fake_gh.triggered_workflows) >= 1, (
            f"Expected workflow trigger, got: {fake_gh.triggered_workflows}\n"
            f"Output: {result.output}"
        )
        _workflow_name, inputs, _ref = fake_gh.triggered_workflows[0]
        assert inputs["plan_id"] == "42"
        assert "Traceback" not in result.output


def test_dispatch_no_args_no_context_fails() -> None:
    """Test that dispatch with no arguments and no context gives helpful error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        fake_gh = FakeLocalGitHub(
            authenticated=True,
            # No PRs configured — branch lookup will return PRNotFound
        )
        fake_issues = FakeGitHubIssues()
        fake_time = FakeTime()
        planned_pr_backend = PlannedPRBackend(fake_gh, fake_issues, time=fake_time)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "some-feature-branch"},
            local_branches={env.cwd: ["main", "some-feature-branch"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={env.cwd: ["origin/main"]},
            repository_roots={env.cwd: env.cwd},
            branch_heads={"main": "abc123", "origin/main": "abc123"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "main": BranchMetadata(
                    name="main", parent=None, children=[], is_trunk=True, commit_sha=None
                ),
            },
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=fake_gh,
            issues=fake_issues,
            use_graphite=True,
            plan_store=planned_pr_backend,
        )

        result = runner.invoke(cli, ["pr", "dispatch"], obj=ctx)

        assert result.exit_code != 0
        assert "No plan numbers provided and could not auto-detect" in result.output
        assert "erk pr dispatch <number>" in result.output
        assert "Traceback" not in result.output


def test_dispatch_with_ref_option_threads_ref_to_workflow() -> None:
    """Test that --ref option is threaded through to trigger_workflow."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_branch = "draft-pr-plan-branch"

        plan_header = render_metadata_block(
            MetadataBlock(
                key="plan-header",
                data={
                    "schema_version": "2",
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "created_by": "testuser",
                    "branch_name": plan_branch,
                },
            )
        )
        pr_body = build_plan_stage_body(
            plan_header,
            "# Plan: Test Ref Option\n\n- Step 1: Do something",
            summary=None,
        )

        pr_42 = PRDetails(
            number=42,
            url="https://github.com/test-owner/test-repo/pull/42",
            title="[erk-pr] Test Ref Option",
            body=pr_body,
            state="OPEN",
            is_draft=True,
            base_ref_name="main",
            head_ref_name=plan_branch,
            is_cross_repository=False,
            mergeable="UNKNOWN",
            merge_state_status="UNKNOWN",
            owner="test-owner",
            repo="test-repo",
            labels=("erk-pr",),
        )

        fake_gh = FakeLocalGitHub(
            authenticated=True,
            polled_run_id="12345",
            pr_details={42: pr_42},
            prs_by_branch={plan_branch: pr_42},
        )
        fake_issues = FakeGitHubIssues()
        fake_time = FakeTime()
        planned_pr_backend = PlannedPRBackend(fake_gh, fake_issues, time=fake_time)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={env.cwd: ["origin/main", f"origin/{plan_branch}"]},
            repository_roots={env.cwd: env.cwd},
            branch_heads={"main": "abc123", "origin/main": "abc123"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=[],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=fake_gh,
            issues=fake_issues,
            use_graphite=True,
            plan_store=planned_pr_backend,
        )

        result = runner.invoke(
            cli, ["pr", "dispatch", "42", "--base", "main", "--ref", "custom-branch"], obj=ctx
        )

        assert len(fake_gh.triggered_workflows) >= 1, (
            f"Expected workflow trigger\nOutput: {result.output}"
        )
        _workflow_name, _inputs, ref = fake_gh.triggered_workflows[0]
        assert ref == "custom-branch"


def test_dispatch_skips_create_branch_when_branch_is_checked_out() -> None:
    """Test that dispatch uses reset_hard when branch is checked out in a worktree.

    When the plan branch is already checked out (e.g., user ran erk impl -d which
    checked out the plan branch in the current slot), git refuses 'git branch -f'
    with 'cannot force update the branch used by worktree'. Dispatch should use
    sync_branch_to_sha (which does git reset --hard) instead of update_local_ref
    to keep the working tree in sync.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_branch = "draft-pr-plan-branch"
        pr_42 = _make_pr_42(plan_branch=plan_branch)

        fake_gh = FakeLocalGitHub(
            authenticated=True,
            polled_run_id="12345",
            pr_details={42: pr_42},
            prs_by_branch={plan_branch: pr_42},
        )
        fake_issues = FakeGitHubIssues()
        fake_time = FakeTime()
        planned_pr_backend = PlannedPRBackend(fake_gh, fake_issues, time=fake_time)

        # Simulate: plan branch is checked out in the current worktree
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: plan_branch},
            local_branches={env.cwd: ["main", plan_branch]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={env.cwd: ["origin/main", f"origin/{plan_branch}"]},
            repository_roots={env.cwd: env.cwd},
            branch_heads={
                "main": "abc123",
                "origin/main": "abc123",
                plan_branch: "local789",
                f"origin/{plan_branch}": "remote456",
            },
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=plan_branch, is_root=True),
                ]
            },
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "main": BranchMetadata(
                    name="main", parent=None, children=[], is_trunk=True, commit_sha=None
                ),
            },
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=fake_gh,
            issues=fake_issues,
            use_graphite=True,
            plan_store=planned_pr_backend,
        )

        result = runner.invoke(cli, ["pr", "dispatch", "42", "--base", "main"], obj=ctx)

        # Verify: workflow was triggered successfully
        assert len(fake_gh.triggered_workflows) >= 1, (
            f"Expected workflow trigger\nOutput: {result.output}"
        )
        inputs = fake_gh.triggered_workflows[0][1]
        assert inputs["plan_backend"] == "planned_pr"
        assert inputs["branch_name"] == plan_branch

        # Verify: create_branch was NOT called (branch was checked out)
        assert len(git.created_branches) == 0, (
            f"Expected no create_branch calls, got: {git.created_branches}"
        )

        # Verify: reset_hard was used (not update_local_ref) to keep working tree in sync
        reset_calls = git.branch.reset_hard_calls
        assert any(ref == "remote456" for _, ref in reset_calls), (
            f"Expected reset_hard with remote456, got: {reset_calls}"
        )

        # Verify: update_local_ref was NOT called for the plan branch
        updated_refs = git.branch.updated_refs
        assert not any(branch == plan_branch for _, branch, _ in updated_refs), (
            f"Expected no update_local_ref for {plan_branch}, got: {updated_refs}"
        )

        assert "Traceback" not in result.output


def test_dispatch_rejects_dirty_checked_out_worktree() -> None:
    """Test that dispatch refuses when the checked-out worktree has uncommitted changes."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_branch = "draft-pr-plan-branch"
        pr_42 = _make_pr_42(plan_branch=plan_branch)

        fake_gh = FakeLocalGitHub(
            authenticated=True,
            polled_run_id="12345",
            pr_details={42: pr_42},
            prs_by_branch={plan_branch: pr_42},
        )
        fake_issues = FakeGitHubIssues()
        fake_time = FakeTime()
        planned_pr_backend = PlannedPRBackend(fake_gh, fake_issues, time=fake_time)

        # Simulate: plan branch is checked out with dirty worktree
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: plan_branch},
            local_branches={env.cwd: ["main", plan_branch]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={env.cwd: ["origin/main", f"origin/{plan_branch}"]},
            repository_roots={env.cwd: env.cwd},
            branch_heads={
                "main": "abc123",
                "origin/main": "abc123",
                plan_branch: "local789",
                f"origin/{plan_branch}": "remote456",
            },
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=plan_branch, is_root=True),
                ]
            },
            file_statuses={env.cwd: (["dirty-file.txt"], [], [])},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "main": BranchMetadata(
                    name="main", parent=None, children=[], is_trunk=True, commit_sha=None
                ),
            },
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=fake_gh,
            issues=fake_issues,
            use_graphite=True,
            plan_store=planned_pr_backend,
        )

        result = runner.invoke(cli, ["pr", "dispatch", "42", "--base", "main"], obj=ctx)

        assert result.exit_code != 0
        assert "uncommitted changes" in result.output
        assert "commit or stash" in result.output

        # Verify: no workflow was triggered
        assert len(fake_gh.triggered_workflows) == 0

        assert "Traceback" not in result.output
