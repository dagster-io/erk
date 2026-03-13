"""Tests for launch command with --repo flag (no local repo)."""

from pathlib import Path

from click.testing import CliRunner
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.test_utils.test_context import context_for_test

from erk.cli.cli import cli
from erk.cli.constants import WORKFLOW_COMMAND_MAP
from erk_shared.context.types import NoRepoSentinel
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


def _build_remote_context(fake_remote: FakeRemoteGitHub) -> context_for_test:
    """Build ErkContext configured for remote mode testing."""
    return context_for_test(
        repo=NoRepoSentinel(),
        remote_github=fake_remote,
    )


# --- pr-rebase remote ---


def test_pr_rebase_remote_dispatches_workflow() -> None:
    """Test pr-rebase with --repo dispatches via RemoteGitHub."""
    pr = _make_remote_pr(123, head_ref_name="feature-branch", base_ref_name="main", title="Fix")
    fake_remote = _make_fake_remote(prs={123: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["launch", "pr-rebase", "--pr", "123", "--repo", "owner/repo"], obj=ctx
    )

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    assert "PR #123" in result.output
    assert "Base branch: main" in result.output
    assert "Workflow dispatched" in result.output

    assert len(fake_remote.dispatched_workflows) == 1
    dispatched = fake_remote.dispatched_workflows[0]
    assert dispatched.workflow == WORKFLOW_COMMAND_MAP["pr-rebase"]
    assert dispatched.inputs["branch_name"] == "feature-branch"
    assert dispatched.inputs["base_branch"] == "main"
    assert dispatched.inputs["pr_number"] == "123"
    assert dispatched.inputs["squash"] == "true"


def test_pr_rebase_remote_requires_pr_option() -> None:
    """Test pr-rebase with --repo requires --pr."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["launch", "pr-rebase", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "--pr is required for pr-rebase without a local repo" in result.output


def test_pr_rebase_remote_closed_pr_fails() -> None:
    """Test pr-rebase with --repo and closed PR fails."""
    pr = _make_remote_pr(111, state="CLOSED", title="Closed PR")
    fake_remote = _make_fake_remote(prs={111: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["launch", "pr-rebase", "--pr", "111", "--repo", "owner/repo"], obj=ctx
    )

    assert result.exit_code == 1
    assert "Cannot rebase CLOSED PR" in result.output


def test_pr_rebase_remote_not_found() -> None:
    """Test pr-rebase with --repo and non-existent PR fails."""
    fake_remote = _make_fake_remote(prs={})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["launch", "pr-rebase", "--pr", "999", "--repo", "owner/repo"], obj=ctx
    )

    assert result.exit_code == 1
    assert "No pull request found with number #999" in result.output


def test_pr_rebase_remote_no_squash() -> None:
    """Test pr-rebase remote with --no-squash flag."""
    pr = _make_remote_pr(123)
    fake_remote = _make_fake_remote(prs={123: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["launch", "pr-rebase", "--pr", "123", "--repo", "owner/repo", "--no-squash"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert len(fake_remote.dispatched_workflows) == 1
    assert fake_remote.dispatched_workflows[0].inputs["squash"] == "false"


# --- pr-address remote ---


def test_pr_address_remote_dispatches_workflow() -> None:
    """Test pr-address with --repo dispatches via RemoteGitHub."""
    pr = _make_remote_pr(456, title="Address Review")
    fake_remote = _make_fake_remote(prs={456: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["launch", "pr-address", "--pr", "456", "--repo", "owner/repo"], obj=ctx
    )

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    assert "PR #456" in result.output
    assert "Workflow dispatched" in result.output

    assert len(fake_remote.dispatched_workflows) == 1
    dispatched = fake_remote.dispatched_workflows[0]
    assert dispatched.workflow == WORKFLOW_COMMAND_MAP["pr-address"]
    assert dispatched.inputs["pr_number"] == "456"


def test_pr_address_remote_requires_pr() -> None:
    """Test pr-address with --repo requires --pr."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["launch", "pr-address", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "--pr is required for pr-address" in result.output


# --- pr-rewrite remote ---


def test_pr_rewrite_remote_dispatches_workflow() -> None:
    """Test pr-rewrite with --repo dispatches via RemoteGitHub."""
    pr = _make_remote_pr(789, head_ref_name="rewrite-branch", base_ref_name="main", title="Rewrite")
    fake_remote = _make_fake_remote(prs={789: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["launch", "pr-rewrite", "--pr", "789", "--repo", "owner/repo"], obj=ctx
    )

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    assert "PR #789" in result.output
    assert "Base branch: main" in result.output
    assert "Workflow dispatched" in result.output

    assert len(fake_remote.dispatched_workflows) == 1
    dispatched = fake_remote.dispatched_workflows[0]
    assert dispatched.workflow == WORKFLOW_COMMAND_MAP["pr-rewrite"]
    assert dispatched.inputs["branch_name"] == "rewrite-branch"
    assert dispatched.inputs["base_branch"] == "main"
    assert dispatched.inputs["pr_number"] == "789"


def test_pr_rewrite_remote_requires_pr() -> None:
    """Test pr-rewrite with --repo requires --pr."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["launch", "pr-rewrite", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "--pr is required for pr-rewrite" in result.output


# --- learn remote ---


def test_learn_remote_dispatches_workflow() -> None:
    """Test learn with --repo dispatches via RemoteGitHub."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["launch", "learn", "--pr", "100", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    assert "Workflow dispatched" in result.output

    assert len(fake_remote.dispatched_workflows) == 1
    dispatched = fake_remote.dispatched_workflows[0]
    assert dispatched.workflow == WORKFLOW_COMMAND_MAP["learn"]
    assert dispatched.inputs["pr_number"] == "100"


def test_learn_remote_requires_pr() -> None:
    """Test learn with --repo requires --pr."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["launch", "learn", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "--pr is required for learn" in result.output


# --- one-shot remote ---


def test_one_shot_remote_dispatches_workflow() -> None:
    """Test one-shot with --repo dispatches via RemoteGitHub."""
    pr = _make_remote_pr(456, head_ref_name="one-shot-branch", title="One Shot")
    fake_remote = _make_fake_remote(prs={456: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["launch", "one-shot", "--pr", "456", "--prompt", "fix the bug", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    assert "PR #456" in result.output
    assert "Workflow dispatched" in result.output

    assert len(fake_remote.dispatched_workflows) == 1
    dispatched = fake_remote.dispatched_workflows[0]
    assert dispatched.workflow == WORKFLOW_COMMAND_MAP["one-shot"]
    assert dispatched.inputs["prompt"] == "fix the bug"
    assert dispatched.inputs["branch_name"] == "one-shot-branch"
    assert dispatched.inputs["pr_number"] == "456"
    assert dispatched.inputs["submitted_by"] == "test-user"


def test_one_shot_remote_requires_pr() -> None:
    """Test one-shot with --repo requires --pr."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["launch", "one-shot", "--prompt", "fix", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 1
    assert "--pr is required for one-shot" in result.output


def test_one_shot_remote_requires_prompt() -> None:
    """Test one-shot with --repo requires --prompt or --file."""
    pr = _make_remote_pr(456)
    fake_remote = _make_fake_remote(prs={456: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["launch", "one-shot", "--pr", "456", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 1
    assert "--prompt or --file is required for one-shot" in result.output


def test_one_shot_remote_with_file(tmp_path: Path) -> None:
    """Test one-shot with --repo reads prompt from file."""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("fix the auth bug from file", encoding="utf-8")

    pr = _make_remote_pr(456, head_ref_name="file-branch")
    fake_remote = _make_fake_remote(prs={456: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["launch", "one-shot", "--pr", "456", "-f", str(prompt_file), "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    assert len(fake_remote.dispatched_workflows) == 1
    assert fake_remote.dispatched_workflows[0].inputs["prompt"] == "fix the auth bug from file"


# --- model option remote ---


def test_model_option_threaded_in_remote_mode() -> None:
    """Test --model option is passed to workflow inputs in remote mode."""
    pr = _make_remote_pr(123)
    fake_remote = _make_fake_remote(prs={123: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "launch",
            "pr-address",
            "--pr",
            "123",
            "--repo",
            "owner/repo",
            "--model",
            "claude-opus-4",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert len(fake_remote.dispatched_workflows) == 1
    assert fake_remote.dispatched_workflows[0].inputs["model_name"] == "claude-opus-4"


# --- ref option remote ---


def test_ref_option_threaded_in_remote_mode() -> None:
    """Test --ref option is threaded through to dispatch in remote mode."""
    pr = _make_remote_pr(123)
    fake_remote = _make_fake_remote(prs={123: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["launch", "pr-address", "--pr", "123", "--repo", "owner/repo", "--ref", "custom-ref"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert len(fake_remote.dispatched_workflows) == 1
    assert fake_remote.dispatched_workflows[0].ref == "custom-ref"


def test_default_ref_uses_default_branch_in_remote_mode() -> None:
    """Test that remote mode uses default branch when no --ref is given."""
    pr = _make_remote_pr(123)
    fake_remote = _make_fake_remote(prs={123: pr})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["launch", "pr-address", "--pr", "123", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert len(fake_remote.dispatched_workflows) == 1
    assert fake_remote.dispatched_workflows[0].ref == "main"


# --- repo resolution edge cases ---


def test_invalid_repo_format() -> None:
    """Test --repo with invalid format gives helpful error."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["launch", "pr-rebase", "--pr", "123", "--repo", "invalid"], obj=ctx
    )

    assert result.exit_code != 0
    assert "Invalid --repo format" in result.output


# --- plan-implement remote ---


def test_plan_implement_remote_shows_usage_error() -> None:
    """Test plan-implement with --repo gives usage error."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["launch", "plan-implement", "--pr", "123", "--repo", "owner/repo"], obj=ctx
    )

    assert result.exit_code == 2
    assert "erk pr dispatch" in result.output
