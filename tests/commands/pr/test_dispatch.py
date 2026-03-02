"""Tests for erk pr dispatch command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.metadata.core import MetadataBlock, render_metadata_block
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.impl_folder import build_plan_ref_json
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.planned_pr_lifecycle import build_plan_stage_body
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_dispatch_planned_pr_plan_triggers_workflow_with_planned_pr_backend() -> None:
    """Test that dispatching a planned-PR plan triggers workflow with plan_backend=planned_pr.

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
            title="[erk-plan] Test Draft PR Plan",
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
            labels=("erk-plan",),
        )

        fake_gh = FakeGitHub(
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
        _workflow_name, inputs = fake_gh.triggered_workflows[0]
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
        title="[erk-plan] Auto-detect Test",
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
        labels=("erk-plan",),
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
        plan_ref_content = build_plan_ref_json(
            provider="github-draft-pr",
            plan_id="42",
            url="https://github.com/test-owner/test-repo/pull/42",
            labels=("erk-plan",),
            objective_id=None,
            node_ids=None,
        )
        (impl_dir / "plan-ref.json").write_text(plan_ref_content, encoding="utf-8")

        fake_gh = FakeGitHub(
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
        _workflow_name, inputs = fake_gh.triggered_workflows[0]
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
        plan_ref_content = build_plan_ref_json(
            provider="github-draft-pr",
            plan_id="42",
            url="https://github.com/test-owner/test-repo/pull/42",
            labels=("erk-plan",),
            objective_id=None,
            node_ids=None,
        )
        (impl_context_dir / "ref.json").write_text(plan_ref_content, encoding="utf-8")
        (impl_context_dir / "plan.md").write_text("# Test plan\n", encoding="utf-8")

        fake_gh = FakeGitHub(
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
        _workflow_name, inputs = fake_gh.triggered_workflows[0]
        assert inputs["plan_id"] == "42"
        assert "Traceback" not in result.output


def test_dispatch_no_args_no_context_fails() -> None:
    """Test that dispatch with no arguments and no context gives helpful error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        fake_gh = FakeGitHub(
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


def test_dispatch_workflow_not_found_shows_install_hint() -> None:
    """Test that a 404 from trigger_workflow shows workflow install instructions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_branch = "plnd/workflow-not-found"
        pr_42 = _make_pr_42(plan_branch=plan_branch)

        fake_gh = FakeGitHub(
            authenticated=True,
            pr_details={42: pr_42},
            prs_by_branch={plan_branch: pr_42},
            trigger_workflow_error="Failed to trigger workflow 'plan-implement.yml'\nstderr: Not Found (HTTP 404)",
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

        result = runner.invoke(cli, ["pr", "dispatch", "42", "--base", "main"], obj=ctx)

        assert result.exit_code != 0
        assert "not found in this repository" in result.output
        assert "erk init capability add erk-impl-workflow" in result.output
        assert "Traceback" not in result.output


def test_dispatch_workflow_generic_runtime_error() -> None:
    """Test that a generic RuntimeError from trigger_workflow shows the error message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_branch = "plnd/workflow-generic-error"
        pr_42 = _make_pr_42(plan_branch=plan_branch)

        fake_gh = FakeGitHub(
            authenticated=True,
            pr_details={42: pr_42},
            prs_by_branch={plan_branch: pr_42},
            trigger_workflow_error="Timed out after 30s trying to trigger workflow 'plan-implement.yml'",
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

        result = runner.invoke(cli, ["pr", "dispatch", "42", "--base", "main"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to dispatch workflow" in result.output
        assert "Timed out after 30s" in result.output
        assert "Traceback" not in result.output
