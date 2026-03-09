"""Tests for erk launch command."""

from pathlib import Path

from click.testing import CliRunner
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env

from erk.cli.cli import cli
from erk.cli.constants import WORKFLOW_COMMAND_MAP
from erk_shared.fakes.git import FakeGit
from erk_shared.fakes.github import FakeLocalGitHub
from erk_shared.fakes.remote_github import FakeRemoteGitHub
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.gateway.remote_github.types import RemotePRInfo


def _make_fake_remote(
    *,
    prs: dict[int, RemotePRInfo] | None = None,
) -> FakeRemoteGitHub:
    """Create a FakeRemoteGitHub with sensible defaults."""
    return FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-123",
        issues=None,
        issue_comments=None,
        pr_references=None,
        prs=prs,
    )


def _make_remote_pr(
    number: int,
    *,
    head_ref_name: str = "feature-branch",
    base_ref_name: str = "main",
    state: str = "OPEN",
    title: str = "Test PR",
) -> RemotePRInfo:
    """Create a RemotePRInfo for testing."""
    return RemotePRInfo(
        number=number,
        title=title,
        state=state,
        url=f"https://github.com/owner/repo/pull/{number}",
        head_ref_name=head_ref_name,
        base_ref_name=base_ref_name,
        owner="owner",
        repo="repo",
        labels=[],
    )


def _make_pr_info(
    number: int,
    branch: str,
    state: str,
    title: str | None,
) -> PullRequestInfo:
    """Create a PullRequestInfo for branch-inference tests."""
    return PullRequestInfo(
        number=number,
        state=state,
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=False,
        title=title or f"PR #{number}",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )


def _make_pr_details(
    number: int,
    *,
    head_ref_name: str,
    state: str,
    base_ref_name: str,
    title: str | None,
) -> PRDetails:
    """Create a PRDetails for branch-inference tests."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"PR #{number}" if title is None else title,
        body="",
        state=state,
        is_draft=False,
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def test_workflow_launch_unknown_workflow(tmp_path: Path) -> None:
    """Test error when workflow name is not recognized."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        fake_remote = _make_fake_remote()
        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "unknown-workflow"], obj=ctx)

        assert result.exit_code == 2
        assert "Unknown workflow 'unknown-workflow'" in result.output


def test_workflow_launch_pr_rebase_triggers_workflow(tmp_path: Path) -> None:
    """Test pr-rebase workflow trigger via branch inference."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # FakeLocalGitHub for branch inference (get_pr_for_branch)
        pr_info = _make_pr_info(123, "feature-branch", "OPEN", "Add feature")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
            state="OPEN",
            base_ref_name="main",
            title="Add feature",
        )
        github = FakeLocalGitHub(
            prs={"feature-branch": pr_info},
            pr_details={123: pr_details},
        )

        # FakeRemoteGitHub for PR lookup and dispatch
        remote_pr = _make_remote_pr(
            123, head_ref_name="feature-branch", base_ref_name="main", title="Add feature"
        )
        fake_remote = _make_fake_remote(prs={123: remote_pr})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "pr-rebase"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #123" in result.output
        assert "Add feature" in result.output
        assert "Base branch: main" in result.output
        assert "Workflow dispatched" in result.output

        # Verify workflow was dispatched via RemoteGitHub
        assert len(fake_remote.dispatched_workflows) == 1
        dispatched = fake_remote.dispatched_workflows[0]
        assert dispatched.workflow == WORKFLOW_COMMAND_MAP["pr-rebase"]
        assert dispatched.inputs["branch_name"] == "feature-branch"
        assert dispatched.inputs["base_branch"] == "main"
        assert dispatched.inputs["pr_number"] == "123"
        assert dispatched.inputs["squash"] == "true"


def test_workflow_launch_pr_rebase_with_pr_option(tmp_path: Path) -> None:
    """Test pr-rebase with explicit --pr option."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        remote_pr = _make_remote_pr(
            456, head_ref_name="other-branch", base_ref_name="main", title="Other feature"
        )
        fake_remote = _make_fake_remote(prs={456: remote_pr})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "pr-rebase", "--pr", "456"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #456" in result.output

        # Verify workflow used PR's branch, not current branch
        assert len(fake_remote.dispatched_workflows) == 1
        assert fake_remote.dispatched_workflows[0].inputs["branch_name"] == "other-branch"


def test_workflow_launch_pr_rebase_with_no_squash(tmp_path: Path) -> None:
    """Test pr-rebase with --no-squash flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # FakeLocalGitHub for branch inference
        pr_info = _make_pr_info(123, "feature-branch", "OPEN", "Feature")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
            state="OPEN",
            base_ref_name="main",
            title="Feature",
        )
        github = FakeLocalGitHub(
            prs={"feature-branch": pr_info},
            pr_details={123: pr_details},
        )

        remote_pr = _make_remote_pr(123, head_ref_name="feature-branch", title="Feature")
        fake_remote = _make_fake_remote(prs={123: remote_pr})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "pr-rebase", "--no-squash"], obj=ctx)

        assert result.exit_code == 0

        # Verify squash is false
        assert len(fake_remote.dispatched_workflows) == 1
        assert fake_remote.dispatched_workflows[0].inputs["squash"] == "false"


def test_workflow_launch_pr_address_triggers_workflow(tmp_path: Path) -> None:
    """Test pr-address workflow trigger."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        remote_pr = _make_remote_pr(123, head_ref_name="feature-branch", title="Add feature")
        fake_remote = _make_fake_remote(prs={123: remote_pr})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "pr-address", "--pr", "123"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #123" in result.output
        assert "Workflow dispatched" in result.output

        # Verify workflow was dispatched
        assert len(fake_remote.dispatched_workflows) == 1
        dispatched = fake_remote.dispatched_workflows[0]
        assert dispatched.workflow == WORKFLOW_COMMAND_MAP["pr-address"]
        assert dispatched.inputs["pr_number"] == "123"


def test_workflow_launch_pr_address_requires_pr_option(tmp_path: Path) -> None:
    """Test pr-address requires --pr option."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        fake_remote = _make_fake_remote()
        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "pr-address"], obj=ctx)

        assert result.exit_code == 1
        assert "--pr is required for pr-address" in result.output


def test_workflow_launch_learn_triggers_workflow(tmp_path: Path) -> None:
    """Test learn workflow trigger."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        fake_remote = _make_fake_remote()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "learn", "--plan", "123"], obj=ctx)

        assert result.exit_code == 0
        assert "Workflow dispatched" in result.output

        # Verify workflow was dispatched
        assert len(fake_remote.dispatched_workflows) == 1
        dispatched = fake_remote.dispatched_workflows[0]
        assert dispatched.workflow == WORKFLOW_COMMAND_MAP["learn"]
        assert dispatched.inputs["plan_number"] == "123"


def test_workflow_launch_learn_requires_issue_option(tmp_path: Path) -> None:
    """Test learn requires --plan option."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        fake_remote = _make_fake_remote()
        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "learn"], obj=ctx)

        assert result.exit_code == 1
        assert "--plan is required for learn" in result.output


def test_workflow_launch_plan_implement_shows_usage_error(tmp_path: Path) -> None:
    """Test plan-implement suggests using erk pr dispatch instead."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        fake_remote = _make_fake_remote()
        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "plan-implement", "--plan", "123"], obj=ctx)

        assert result.exit_code == 2
        assert "erk pr dispatch" in result.output


def test_workflow_launch_with_model_option(tmp_path: Path) -> None:
    """Test --model option is passed to workflow."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        remote_pr = _make_remote_pr(123, head_ref_name="feature-branch", title="Feature")
        fake_remote = _make_fake_remote(prs={123: remote_pr})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(
            cli,
            ["launch", "pr-address", "--pr", "123", "--model", "claude-opus-4"],
            obj=ctx,
        )

        assert result.exit_code == 0

        # Verify model is passed
        assert len(fake_remote.dispatched_workflows) == 1
        assert fake_remote.dispatched_workflows[0].inputs["model_name"] == "claude-opus-4"


def test_workflow_launch_pr_rewrite_triggers_workflow(tmp_path: Path) -> None:
    """Test pr-rewrite workflow trigger."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        remote_pr = _make_remote_pr(
            123, head_ref_name="feature-branch", base_ref_name="main", title="Add feature"
        )
        fake_remote = _make_fake_remote(prs={123: remote_pr})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "pr-rewrite", "--pr", "123"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #123" in result.output
        assert "Workflow dispatched" in result.output

        # Verify workflow was dispatched
        assert len(fake_remote.dispatched_workflows) == 1
        dispatched = fake_remote.dispatched_workflows[0]
        assert dispatched.workflow == WORKFLOW_COMMAND_MAP["pr-rewrite"]
        assert dispatched.inputs["branch_name"] == "feature-branch"
        assert dispatched.inputs["base_branch"] == "main"
        assert dispatched.inputs["pr_number"] == "123"


def test_workflow_launch_pr_rewrite_requires_pr_option(tmp_path: Path) -> None:
    """Test pr-rewrite requires --pr option."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        fake_remote = _make_fake_remote()
        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "pr-rewrite"], obj=ctx)

        assert result.exit_code == 1
        assert "--pr is required for pr-rewrite" in result.output


def test_workflow_launch_one_shot_triggers_workflow(tmp_path: Path) -> None:
    """Test one-shot workflow trigger with --prompt."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        remote_pr = _make_remote_pr(123, head_ref_name="feature-branch", title="Add feature")
        fake_remote = _make_fake_remote(prs={123: remote_pr})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(
            cli,
            ["launch", "one-shot", "--pr", "123", "--prompt", "fix the auth bug"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "PR #123" in result.output
        assert "Workflow dispatched" in result.output

        # Verify workflow was dispatched with correct inputs
        assert len(fake_remote.dispatched_workflows) == 1
        dispatched = fake_remote.dispatched_workflows[0]
        assert dispatched.workflow == WORKFLOW_COMMAND_MAP["one-shot"]
        assert dispatched.inputs["prompt"] == "fix the auth bug"
        assert dispatched.inputs["branch_name"] == "feature-branch"
        assert dispatched.inputs["pr_number"] == "123"
        assert dispatched.inputs["submitted_by"] == "test-user"


def test_workflow_launch_one_shot_with_file(tmp_path: Path) -> None:
    """Test one-shot workflow trigger with --file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Write prompt file
        prompt_file = env.cwd / "prompt.md"
        prompt_file.write_text("fix the auth bug from file", encoding="utf-8")

        remote_pr = _make_remote_pr(123, head_ref_name="feature-branch", title="Add feature")
        fake_remote = _make_fake_remote(prs={123: remote_pr})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(
            cli,
            ["launch", "one-shot", "--pr", "123", "-f", str(prompt_file)],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "Workflow dispatched" in result.output

        # Verify prompt was read from file
        assert len(fake_remote.dispatched_workflows) == 1
        assert fake_remote.dispatched_workflows[0].inputs["prompt"] == "fix the auth bug from file"


def test_workflow_launch_one_shot_requires_pr(tmp_path: Path) -> None:
    """Test one-shot requires --pr option."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        fake_remote = _make_fake_remote()
        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(
            cli,
            ["launch", "one-shot", "--prompt", "fix something"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "--pr is required for one-shot" in result.output


def test_workflow_launch_one_shot_requires_prompt(tmp_path: Path) -> None:
    """Test one-shot requires --prompt or --file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        fake_remote = _make_fake_remote()
        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(
            cli,
            ["launch", "one-shot", "--pr", "123"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "--prompt or --file is required for one-shot" in result.output


def test_workflow_launch_one_shot_prompt_and_file_exclusive(tmp_path: Path) -> None:
    """Test one-shot rejects both --prompt and --file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Write prompt file
        prompt_file = env.cwd / "prompt.md"
        prompt_file.write_text("file prompt", encoding="utf-8")

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        fake_remote = _make_fake_remote()
        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(
            cli,
            [
                "launch",
                "one-shot",
                "--pr",
                "123",
                "--prompt",
                "inline prompt",
                "-f",
                str(prompt_file),
            ],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "--prompt and --file are mutually exclusive" in result.output


def test_workflow_launch_with_ref_option(tmp_path: Path) -> None:
    """Test --ref option is threaded through to dispatch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        remote_pr = _make_remote_pr(123, head_ref_name="feature-branch", title="Add feature")
        fake_remote = _make_fake_remote(prs={123: remote_pr})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, remote_github=fake_remote)

        result = runner.invoke(
            cli, ["launch", "pr-address", "--pr", "123", "--ref", "custom-branch"], obj=ctx
        )

        assert result.exit_code == 0
        assert len(fake_remote.dispatched_workflows) == 1
        assert fake_remote.dispatched_workflows[0].ref == "custom-branch"


def test_workflow_launch_pr_rebase_closed_pr_fails(tmp_path: Path) -> None:
    """Test error when PR is closed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # FakeLocalGitHub for branch inference
        pr_info = _make_pr_info(111, "closed-branch", "CLOSED", "Closed PR")
        pr_details = _make_pr_details(
            number=111,
            head_ref_name="closed-branch",
            state="CLOSED",
            base_ref_name="main",
            title="Closed PR",
        )
        github = FakeLocalGitHub(
            prs={"closed-branch": pr_info},
            pr_details={111: pr_details},
        )

        remote_pr = _make_remote_pr(111, state="CLOSED", head_ref_name="closed-branch")
        fake_remote = _make_fake_remote(prs={111: remote_pr})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "closed-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=fake_remote)

        result = runner.invoke(cli, ["launch", "pr-rebase"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot rebase CLOSED PR" in result.output
