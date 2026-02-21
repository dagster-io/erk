"""Tests for erk plan submit command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import MetadataBlock, render_metadata_block
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend
from erk_shared.plan_store.draft_pr_lifecycle import build_plan_stage_body
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_submit_exits_cleanly_when_parent_branch_untracked() -> None:
    """Test that submit fails gracefully when stacking on untracked Graphite branch.

    When stacking a plan on a parent branch that exists locally but isn't tracked
    with Graphite, the command should exit with a friendly error message instead
    of raising an exception.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create an issue with erk-plan label
        issue = IssueInfo(
            number=123,
            title="[erk-plan] Test Plan",
            body="Test plan body",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/123",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            author="testuser",
        )
        issues = FakeGitHubIssues(issues={123: issue})

        # Configure git with the untracked parent branch existing on remote
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "untracked-parent"},
            local_branches={env.cwd: ["main", "untracked-parent"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            # Remote branches must be in format "remote/branch"
            remote_branches={env.cwd: ["origin/main", "origin/untracked-parent"]},
        )

        # Configure Graphite with main tracked but NOT untracked-parent
        # This is the key setup: parent branch exists but isn't tracked by Graphite
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
                # Note: untracked-parent is intentionally NOT in branches dict
                # so is_branch_tracked() returns False for it
            },
        )

        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=github,
            issues=issues,
            use_graphite=True,  # Enable Graphite mode
        )

        # Run the submit command with --base pointing to the untracked branch
        result = runner.invoke(
            cli, ["plan", "submit", "123", "--base", "untracked-parent"], obj=ctx
        )

        # Should exit with code 1 (not an exception traceback)
        assert result.exit_code == 1

        # Should show friendly error message with remediation steps
        assert "not tracked by Graphite" in result.output
        assert "untracked-parent" in result.output
        assert "gt checkout" in result.output
        assert "gt track" in result.output

        # Should NOT show a traceback
        assert "Traceback" not in result.output


def test_submit_succeeds_when_parent_branch_tracked() -> None:
    """Test that submit works when parent branch is tracked by Graphite.

    This is a positive control test to ensure the tracking check doesn't
    break the happy path.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create an issue with erk-plan label
        issue = IssueInfo(
            number=456,
            title="[erk-plan] Test Plan",
            body="Test plan body",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/456",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            author="testuser",
        )
        issues = FakeGitHubIssues(issues={456: issue})

        # Configure git with the tracked parent branch existing on remote
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "tracked-parent"},
            local_branches={env.cwd: ["main", "tracked-parent"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            # Remote branches must be in format "remote/branch"
            remote_branches={env.cwd: ["origin/main", "origin/tracked-parent"]},
            repository_roots={env.cwd: env.cwd},
        )

        # Configure Graphite with tracked-parent tracked
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["tracked-parent"],
                    is_trunk=True,
                    commit_sha=None,
                ),
                "tracked-parent": BranchMetadata(
                    name="tracked-parent",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
            },
        )

        github = FakeGitHub(
            authenticated=True,
            polled_run_id="12345",  # For workflow dispatch polling
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=github,
            issues=issues,
            use_graphite=True,  # Enable Graphite mode
        )

        # Run the submit command with --base pointing to a tracked branch
        result = runner.invoke(cli, ["plan", "submit", "456", "--base", "tracked-parent"], obj=ctx)

        # Should NOT fail with untracked branch error
        assert "not tracked by Graphite" not in result.output


def test_submit_updates_pr_body_with_workflow_run_link() -> None:
    """Test that submit updates the PR body with the workflow run link.

    After triggering the workflow, the submit flow fetches the PR details
    and appends a **Workflow run:** link to the body. This is a best-effort
    operation that logs a warning on failure.

    Uses the "branch exists with PR" code path to skip branch/PR creation
    (which requires filesystem I/O) and go directly to workflow trigger.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Use a known branch name that matches P789-* pattern
        existing_branch = "P789-test-workflow-link-01-01-0000"

        issue = IssueInfo(
            number=789,
            title="[erk-plan] Test Workflow Link",
            body="Test plan body",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/789",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            author="testuser",
        )
        issues = FakeGitHubIssues(issues={789: issue})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
            # Include existing P789- branch so validation finds it
            local_branches={env.cwd: ["main", existing_branch]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            # Branch exists on remote (triggers "branch exists" path)
            remote_branches={env.cwd: ["origin/main", f"origin/{existing_branch}"]},
            repository_roots={env.cwd: env.cwd},
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

        # PR details for PR #42 — used by both get_pr_for_branch() and get_pr()
        pr_42 = PRDetails(
            number=42,
            url="https://github.com/test-owner/test-repo/pull/42",
            title="Test Workflow Link",
            body="Initial PR body",
            state="OPEN",
            is_draft=True,
            base_ref_name="main",
            head_ref_name=existing_branch,
            is_cross_repository=False,
            mergeable="UNKNOWN",
            merge_state_status="UNKNOWN",
            owner="test-owner",
            repo="test-repo",
        )

        github = FakeGitHub(
            authenticated=True,
            polled_run_id="12345",
            # get_pr_for_branch() uses prs_by_branch; get_pr() uses pr_details
            prs_by_branch={existing_branch: pr_42},
            pr_details={42: pr_42},
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=github,
            issues=issues,
            use_graphite=True,
            # Confirm reuse of existing branch when prompted
            confirm_responses=[True],
        )

        result = runner.invoke(cli, ["plan", "submit", "789", "--base", "main"], obj=ctx)

        # Verify the submit reached the workflow trigger
        assert "Skipping branch/PR creation" in result.output

        # Verify the PR body was updated with workflow run link
        # FakeGitHub.trigger_workflow returns run_id="1234567890"
        # _build_workflow_run_url constructs: https://github.com/test-owner/test-repo/actions/runs/1234567890
        workflow_link_updates = [
            (pr_num, body)
            for pr_num, body in github.updated_pr_bodies
            if "**Workflow run:**" in body and "actions/runs/" in body
        ]
        assert len(workflow_link_updates) >= 1, (
            f"Expected at least one PR body update with workflow run link, "
            f"got updated_pr_bodies: {github.updated_pr_bodies}"
        )

        # Verify the workflow URL format and correct PR number
        pr_num, updated_body = workflow_link_updates[0]
        assert pr_num == 42
        assert "https://github.com/test-owner/test-repo/actions/runs/1234567890" in updated_body

        assert "Traceback" not in result.output


def test_submit_draft_pr_plan_triggers_workflow_with_draft_pr_backend() -> None:
    """Test that submitting a draft-PR plan triggers workflow with plan_backend=draft_pr.

    Draft-PR plans already have a branch and PR. Submit should:
    - Validate the PR has the erk-plan label and is OPEN
    - Fetch and checkout the existing branch
    - Create .worker-impl/ with provider="github-draft-pr"
    - Trigger workflow with plan_backend="draft_pr" in inputs
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

        # DraftPRPlanBackend makes get_provider_name() return "github-draft-pr"
        draft_pr_backend = DraftPRPlanBackend(fake_gh, fake_issues, time=fake_time)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={env.cwd: ["origin/main", f"origin/{plan_branch}"]},
            repository_roots={env.cwd: env.cwd},
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
            plan_store=draft_pr_backend,
        )

        result = runner.invoke(cli, ["plan", "submit", "42", "--base", "main"], obj=ctx)

        # Verify: workflow was triggered with plan_backend="draft_pr"
        assert len(fake_gh.triggered_workflows) >= 1, (
            f"Expected workflow trigger, got: {fake_gh.triggered_workflows}\n"
            f"Output: {result.output}"
        )
        _workflow_name, inputs = fake_gh.triggered_workflows[0]
        assert inputs["plan_backend"] == "draft_pr"
        assert inputs["plan_id"] == "42"
        assert inputs["branch_name"] == plan_branch

        # Verify: no new PR was created (draft-PR already exists)
        assert len(fake_gh.created_prs) == 0

        # Verify: expected output messages
        assert "Checking out existing plan branch" in result.output
        assert "Creating .worker-impl/ folder" in result.output
        assert "Workflow triggered" in result.output

        # Verify: no warnings, dispatch metadata written successfully
        assert "Warning:" not in result.output
        assert "Dispatch metadata written" in result.output

        assert "Traceback" not in result.output


def test_submit_draft_pr_plan_cleans_up_stale_worker_impl_folder() -> None:
    """Test that _submit_draft_pr_plan cleans up stale .worker-impl/ before creating new one.

    When a previous submission failed and left behind a .worker-impl/ folder,
    the draft-PR submit path should remove it before creating the new one.
    This tests the cleanup logic at submit.py:440-443.
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
            "# Plan: Test Draft PR Cleanup\n\n- Step 1: Do something\n- Step 2: Do something else",
        )

        pr_42 = PRDetails(
            number=42,
            url="https://github.com/test-owner/test-repo/pull/42",
            title="[erk-plan] Test Draft PR Cleanup",
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

        draft_pr_backend = DraftPRPlanBackend(fake_gh, fake_issues, time=fake_time)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={env.cwd: ["origin/main", f"origin/{plan_branch}"]},
            repository_roots={env.cwd: env.cwd},
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

        # Pre-create a stale .worker-impl/ folder (simulating a prior failed submission)
        stale_worker_impl = env.cwd / ".worker-impl"
        stale_worker_impl.mkdir()
        stale_marker = stale_worker_impl / "stale-marker.txt"
        stale_marker.write_text("leftover from previous run")

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=fake_gh,
            issues=fake_issues,
            use_graphite=True,
            plan_store=draft_pr_backend,
        )

        result = runner.invoke(cli, ["plan", "submit", "42", "--base", "main"], obj=ctx)

        # Verify cleanup message was printed
        assert "Cleaning up previous .worker-impl/ folder" in result.output

        # Verify stale marker file no longer exists
        assert not stale_marker.exists()

        # Verify new .worker-impl/ was created with correct files
        worker_impl = env.cwd / ".worker-impl"
        assert (worker_impl / "plan.md").exists()
        assert (worker_impl / "plan-ref.json").exists()

        # Verify plan-ref.json has correct provider
        plan_ref = json.loads((worker_impl / "plan-ref.json").read_text())
        assert plan_ref["provider"] == "github-draft-pr"

        # Verify: no warnings, dispatch metadata written successfully
        assert "Warning:" not in result.output
        assert "Dispatch metadata written" in result.output

        assert "Traceback" not in result.output


def test_submit_issue_plan_cleans_up_stale_worker_impl_folder() -> None:
    """Test that _create_branch_and_pr cleans up stale .worker-impl/ before creating new one.

    When a previous submission failed and left behind a .worker-impl/ folder,
    the issue-based submit path should remove it before creating the new one.
    This tests the cleanup logic at submit.py:713-716.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        issue = IssueInfo(
            number=42,
            title="[erk-plan] Test Issue Cleanup",
            body="Test plan body for cleanup test",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/42",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={env.cwd: ["origin/main"]},
            repository_roots={env.cwd: env.cwd},
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

        fake_gh = FakeGitHub(
            authenticated=True,
            polled_run_id="12345",
        )

        # Pre-create a stale .worker-impl/ folder (simulating a prior failed submission)
        stale_worker_impl = env.cwd / ".worker-impl"
        stale_worker_impl.mkdir()
        stale_marker = stale_worker_impl / "stale-marker.txt"
        stale_marker.write_text("leftover from previous run")

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=fake_gh,
            issues=fake_issues,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["plan", "submit", "42", "--base", "main"], obj=ctx)

        # Verify cleanup message was printed
        assert "Cleaning up previous .worker-impl/ folder" in result.output

        # Verify stale marker file no longer exists
        assert not stale_marker.exists()

        # Verify new .worker-impl/ was created with correct files
        worker_impl = env.cwd / ".worker-impl"
        assert (worker_impl / "plan.md").exists()
        assert (worker_impl / "plan-ref.json").exists()

        # Verify plan-ref.json has correct provider
        plan_ref = json.loads((worker_impl / "plan-ref.json").read_text())
        assert plan_ref["provider"] == "github"

        assert "Traceback" not in result.output
