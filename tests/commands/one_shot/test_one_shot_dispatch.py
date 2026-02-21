"""Tests for one-shot dispatch shared logic."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.one_shot_dispatch import (
    OneShotDispatchParams,
    dispatch_one_shot,
)
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_dispatch_happy_path() -> None:
    """Test dispatch creates skeleton issue, branch with P<N>- prefix, PR, and triggers workflow."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

        params = OneShotDispatchParams(
            prompt="fix the import in config.py",
            model=None,
            extra_workflow_inputs={},
        )

        result = dispatch_one_shot(ctx, params=params, dry_run=False)

        assert result is not None
        # Branch should have P<N>- prefix (skeleton issue created first)
        assert result.branch_name.startswith("P1-")

        # Verify skeleton plan issue was created
        assert len(issues.created_issues) == 1
        title, _body, labels = issues.created_issues[0]
        assert "[erk-plan]" in title
        assert "erk-plan" in labels

        # Verify branch was created
        assert len(git.created_branches) == 1
        assert git.created_branches[0][2] == "main"  # start_point is trunk

        # Verify .worker-impl/prompt.md was staged and committed
        assert len(git.commits) == 1
        assert git.commits[0].staged_files == (".worker-impl/prompt.md",)

        # Verify .worker-impl/prompt.md was written to disk
        prompt_file = env.cwd / ".worker-impl" / "prompt.md"
        assert prompt_file.exists()
        assert prompt_file.read_text(encoding="utf-8") == "fix the import in config.py\n"

        # Verify push to remote
        assert len(git.pushed_branches) == 1

        # Verify PR was created with closing reference
        assert len(github.created_prs) == 1
        _branch, _title, pr_body, base, draft = github.created_prs[0]
        assert draft is True
        assert base == "main"
        assert "Closes #1" in pr_body

        # Verify workflow was triggered with plan_issue_number and plan_backend
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == "one-shot.yml"
        assert inputs["prompt"] == "fix the import in config.py"
        assert inputs["plan_issue_number"] == "1"
        assert inputs["plan_backend"] == "github"

        # Verify PR body was updated with workflow run link and closing reference
        assert len(github.updated_pr_bodies) == 1
        _pr_num, updated_body = github.updated_pr_bodies[0]
        assert "**Workflow run:**" in updated_body
        assert "https://github.com/owner/repo/actions/runs/" in updated_body
        assert "Closes #1" in updated_body

        # Verify dispatch metadata was written to plan issue
        issue_info = issues.get_issue(env.cwd, 1)
        assert not isinstance(issue_info, IssueNotFound)
        assert "last_dispatched_run_id" in issue_info.body
        assert "last_dispatched_node_id" in issue_info.body
        assert "last_dispatched_at" in issue_info.body

        # Verify we're back on original branch
        assert git.branch.get_current_branch(env.cwd) == "main"


def test_dispatch_with_extra_inputs() -> None:
    """Test extra_workflow_inputs in workflow trigger and skeleton links to objective."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

        params = OneShotDispatchParams(
            prompt="implement step 1.1",
            model=None,
            extra_workflow_inputs={
                "objective_issue": "42",
                "node_id": "1.1",
            },
        )

        result = dispatch_one_shot(ctx, params=params, dry_run=False)

        assert result is not None
        # Branch should have P<N>- prefix
        assert result.branch_name.startswith("P1-")

        # Verify extra inputs are in workflow trigger
        _workflow, inputs = github.triggered_workflows[0]
        assert inputs["objective_issue"] == "42"
        assert inputs["node_id"] == "1.1"
        assert inputs["prompt"] == "implement step 1.1"
        assert inputs["plan_issue_number"] == "1"


def test_dispatch_dry_run() -> None:
    """Test dispatch_one_shot dry_run outputs info without mutations."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        # Invoke via CLI to capture user_output via CliRunner
        result = runner.invoke(
            cli,
            ["one-shot", "add type hints", "--dry-run", "-m", "opus"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Dry-run mode:" in result.output
        assert "add type hints" in result.output

        # Verify no mutations occurred (skeleton issue NOT created in dry-run)
        assert len(git.created_branches) == 0
        assert len(git.pushed_branches) == 0
        assert len(github.created_prs) == 0
        assert len(github.triggered_workflows) == 0


def test_dispatch_restores_branch_on_error() -> None:
    """Test that original branch is restored even if push fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            push_to_remote_error=PushError(message="network error"),
        )
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "fix the import in config.py"],
            obj=ctx,
        )

        # Verify command failed
        assert result.exit_code != 0

        # Verify we're back on original branch despite error
        assert git.branch.get_current_branch(env.cwd) == "main"


def test_dispatch_creates_skeleton_plan_issue() -> None:
    """Test that skeleton plan issue is created with correct content and metadata."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

        params = OneShotDispatchParams(
            prompt="add user authentication",
            model=None,
            extra_workflow_inputs={},
        )

        dispatch_one_shot(ctx, params=params, dry_run=False)

        # Verify skeleton issue was created with expected content
        assert len(issues.created_issues) == 1
        title, _body, labels = issues.created_issues[0]
        assert "[erk-plan]" in title
        assert "erk-plan" in labels

        # Verify plan comment was added (create_plan_issue adds plan as comment)
        # Plus queued event comment from dispatch
        assert len(issues.added_comments) == 2
        issue_number, comment_body, _comment_id = issues.added_comments[0]
        assert issue_number == 1
        assert "One-shot" in comment_body
        assert "add user authentication" in comment_body

        # Verify queued event comment
        issue_number, queued_body, _comment_id = issues.added_comments[1]
        assert issue_number == 1
        assert "One-Shot Dispatched" in queued_body
        assert "add user authentication" in queued_body


def test_dispatch_posts_queued_event_comment() -> None:
    """Test dispatch posts a queued event comment with workflow run URL and prompt."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

        params = OneShotDispatchParams(
            prompt="refactor the auth module",
            model=None,
            extra_workflow_inputs={},
        )

        dispatch_one_shot(ctx, params=params, dry_run=False)

        # create_plan_issue adds 1 comment, dispatch adds queued event comment
        assert len(issues.added_comments) == 2

        # The queued event comment is the last one
        issue_number, comment_body, _comment_id = issues.added_comments[-1]
        assert issue_number == 1
        assert "One-Shot Dispatched" in comment_body
        assert "refactor the auth module" in comment_body
        assert "**Workflow run:**" in comment_body
        assert "https://github.com/owner/repo/actions/runs/" in comment_body


def test_dispatch_writes_metadata_to_plan_issue() -> None:
    """Test that dispatch writes run_id, node_id, and timestamp metadata to the plan issue."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides={"ERK_PLAN_BACKEND": "github"}) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

        params = OneShotDispatchParams(
            prompt="add logging to api routes",
            model=None,
            extra_workflow_inputs={},
        )

        dispatch_one_shot(ctx, params=params, dry_run=False)

        # Read the plan issue and verify dispatch metadata was written
        issue_info = issues.get_issue(env.cwd, 1)
        assert not isinstance(issue_info, IssueNotFound)
        assert "last_dispatched_run_id: '1234567890'" in issue_info.body
        assert "last_dispatched_node_id: WFR_fake_node_id_1234567890" in issue_info.body
        assert "last_dispatched_at:" in issue_info.body


def test_dispatch_draft_pr_lifecycle() -> None:
    """Test full draft_pr dispatch: no skeleton issue, plan/ branch, PR with metadata block.

    In draft_pr mode, the draft PR IS the plan entity. The dispatch should:
    - NOT create a skeleton issue
    - Use plan/ branch naming
    - Create a draft PR with plan-header metadata block
    - Set plan_issue_number = pr_number for downstream code
    - Write dispatch metadata to the PR (the plan entity)
    - Post queued event comment to the PR
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        # Explicitly use DraftPRPlanBackend so ctx.plan_backend.get_provider_name()
        # returns "github-draft-pr" and dispatch takes the draft_pr path.
        plan_store = DraftPRPlanBackend(github, issues, time=FakeTime())

        ctx = build_workspace_test_context(
            env, git=git, github=github, issues=issues, plan_store=plan_store
        )

        params = OneShotDispatchParams(
            prompt="fix the import in config.py",
            model=None,
            extra_workflow_inputs={},
        )

        result = dispatch_one_shot(ctx, params=params, dry_run=False)

        assert result is not None

        # No skeleton issue created — draft_pr skips issue creation
        assert len(issues.created_issues) == 0

        # Branch uses plan/ prefix (not P<N>-)
        assert result.branch_name.startswith("plan/")
        assert not result.branch_name.startswith("P")

        # PR created with plan-header metadata block
        assert len(github.created_prs) == 1
        _branch, _title, pr_body, base, draft = github.created_prs[0]
        assert draft is True
        assert base == "main"
        assert "plan-header" in pr_body
        assert "lifecycle_stage: prompted" in pr_body
        assert "fix the import in config.py" in pr_body

        # No Closes #N in PR body (self-referential for draft_pr)
        assert "Closes #" not in pr_body

        # erk-plan label added to PR
        pr_number = result.pr_number
        assert (pr_number, "erk-plan") in github.added_labels

        # Workflow inputs include plan_issue_number = pr_number and plan_backend
        assert len(github.triggered_workflows) == 1
        _workflow, inputs = github.triggered_workflows[0]
        assert inputs["plan_issue_number"] == str(pr_number)
        assert inputs["plan_backend"] == "draft_pr"

        # Dispatch metadata written to the PR (the plan entity).
        # The PR body is updated with footer, then dispatch metadata written
        # via plan_backend.update_metadata targeting the PR number.
        # updated_pr_bodies includes: (1) footer update, (2) dispatch metadata update
        assert len(github.updated_pr_bodies) >= 2
        # The dispatch metadata update should contain last_dispatched_run_id
        last_body = github.updated_pr_bodies[-1][1]
        assert "last_dispatched_run_id" in last_body

        # Queued event comment is best-effort. In real GitHub, PRs are issues
        # and add_comment works on PR numbers. In the fake, PRs and issues are
        # separate, so the comment may fail. This is acceptable — dispatch
        # metadata is the critical operation.


def test_dispatch_long_prompt_truncates_workflow_input() -> None:
    """Test that long prompts are truncated in workflow input but committed in full."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

        long_prompt = "x" * 1000

        params = OneShotDispatchParams(
            prompt=long_prompt,
            model=None,
            extra_workflow_inputs={},
        )

        result = dispatch_one_shot(ctx, params=params, dry_run=False)

        assert result is not None

        # Verify workflow input was truncated
        _workflow, inputs = github.triggered_workflows[0]
        assert len(inputs["prompt"]) < len(long_prompt)
        assert inputs["prompt"].endswith("... (full prompt committed to .worker-impl/prompt.md)")

        # Verify full prompt was committed to .worker-impl/prompt.md
        prompt_file = env.cwd / ".worker-impl" / "prompt.md"
        assert prompt_file.exists()
        content = prompt_file.read_text(encoding="utf-8")
        assert content == long_prompt + "\n"

        # Verify the file was staged
        assert git.commits[0].staged_files == (".worker-impl/prompt.md",)
