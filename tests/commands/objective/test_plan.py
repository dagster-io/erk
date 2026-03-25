"""Tests for objective plan command.

Note: The plan command uses AgentLauncher.launch_interactive() which
replaces the process. These tests verify behavior up to (but not including)
the process replacement, using FakeAgentLauncher to track calls.
"""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig, InteractiveAgentConfig
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.fakes.gateway.agent_launcher import FakeAgentLauncher
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import format_plan_header_body_for_test
from tests.test_utils.test_context import context_for_test


def test_plan_shows_error_when_claude_not_installed() -> None:
    """Test implement shows error when Claude CLI is not installed."""
    runner = CliRunner()

    launcher = FakeAgentLauncher(
        launch_error="Claude CLI not found\nInstall from: https://claude.com/download"
    )
    ctx = context_for_test(agent_launcher=launcher)

    result = runner.invoke(cli, ["objective", "plan", "123"], obj=ctx)

    assert result.exit_code == 1
    assert "Claude CLI not found" in result.output


def test_plan_launches_claude_with_issue_number() -> None:
    """Test implement launches Claude with the correct command for issue number.

    The implement command uses plan mode since it's for creating implementation plans.
    """
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "plan", "3679"], obj=ctx)

    # FakeAgentLauncher.launch_interactive raises SystemExit(0), which CliRunner catches
    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.command == "/erk:objective-plan 3679"
    assert fake_launcher.last_call.config.permission_mode == "plan"
    assert fake_launcher.last_call.config.allow_dangerous is False
    assert fake_launcher.last_call.config.dangerous is False


def test_plan_launches_claude_with_url() -> None:
    """Test implement launches Claude with the correct command for GitHub URL."""
    runner = CliRunner()
    url = "https://github.com/owner/repo/issues/3679"
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "plan", url], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.command == f"/erk:objective-plan {url}"
    assert fake_launcher.last_call.config.permission_mode == "plan"


def test_plan_requires_issue_ref_or_next() -> None:
    """Test implement requires ISSUE_REF unless --next is used."""
    runner = CliRunner()

    result = runner.invoke(cli, ["objective", "plan"])

    assert result.exit_code == 1
    assert "ISSUE_REF is required unless --next" in result.output


def test_plan_respects_allow_dangerous_config() -> None:
    """Test that allow_dangerous from config is passed to agent launcher.

    When the user has allow_dangerous = true in their ~/.erk/config.toml,
    the config object passed to the launcher should have allow_dangerous=True.
    """
    runner = CliRunner()

    # Create a context with allow_dangerous enabled in interactive_claude config
    ic_config = InteractiveAgentConfig(
        backend="claude",
        model=None,
        verbose=False,
        permission_mode="edits",
        dangerous=False,
        allow_dangerous=True,
    )
    global_config = GlobalConfig.test(
        erk_root=Path("/tmp/erk"),
        interactive_agent=ic_config,
    )
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(global_config=global_config, agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "plan", "123"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    # Should include allow_dangerous from config
    # and use plan mode (overridden from default acceptEdits)
    assert fake_launcher.last_call.config.allow_dangerous is True
    assert fake_launcher.last_call.config.permission_mode == "plan"
    assert fake_launcher.last_call.command == "/erk:objective-plan 123"


def test_plan_with_dangerous_flag() -> None:
    """Test that -d/--dangerous flag enables allow_dangerous in launcher config."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "plan", "-d", "123"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    # Should include allow_dangerous from -d flag
    assert fake_launcher.last_call.config.allow_dangerous is True
    assert fake_launcher.last_call.config.permission_mode == "plan"
    assert fake_launcher.last_call.command == "/erk:objective-plan 123"


def test_plan_without_dangerous_flag() -> None:
    """Test that without -d flag, allow_dangerous is not enabled."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "plan", "123"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    # Should NOT include allow_dangerous
    assert fake_launcher.last_call.config.allow_dangerous is False
    assert fake_launcher.last_call.config.permission_mode == "plan"
    assert fake_launcher.last_call.command == "/erk:objective-plan 123"


def test_plan_with_node_flag() -> None:
    """Test that --node flag pre-marks as planning and launches inner command."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        objective_issue = _make_objective_issue(42, OBJECTIVE_BODY)
        issues = FakeGitHubIssues(
            issues={42: objective_issue},
        )
        fake_launcher = FakeAgentLauncher()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True, issues_gateway=issues)
        remote = FakeRemoteGitHub(
            authenticated_user="testuser",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={42: objective_issue},
            issue_comments=None,
        )
        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
            agent_launcher=fake_launcher,
            remote_github=remote,
        )

        result = runner.invoke(
            cli,
            ["objective", "plan", "42", "--node", "1.1"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert fake_launcher.launch_called
        assert fake_launcher.last_call is not None
        # Should launch inner command instead of outer
        assert fake_launcher.last_call.command == "/erk:system:objective-plan-node 42 --node 1.1"
        # Should have pre-marked the node as planning via RemoteGitHub API
        objective_body_updates = [
            update for update in remote.updated_issue_bodies if update.number == 42
        ]
        assert len(objective_body_updates) == 1
        assert "planning" in objective_body_updates[0].body


def test_plan_next_and_node_mutually_exclusive() -> None:
    """Test --next and --node are mutually exclusive."""
    runner = CliRunner()

    result = runner.invoke(cli, ["objective", "plan", "42", "--next", "--node", "2.1"])

    assert result.exit_code == 1
    assert "--next and --node are mutually exclusive" in result.output


NOW = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

OBJECTIVE_BODY = """# Objective: Add caching

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml

schema_version: '2'
steps:
  - id: '1.1'
    description: Setup infra
    status: pending
    plan: null
    pr: null
  - id: '1.2'
    description: Add tests
    status: pending
    plan: null
    pr: null

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Foundation

| Node | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | pending | - | - |
| 1.2 | Add tests | pending | - | - |
"""

OBJECTIVE_ALL_DONE_BODY = """# Objective: Done

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml

schema_version: '2'
steps:
  - id: '1.1'
    description: Setup infra
    status: done
    plan: null
    pr: '#100'

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Foundation

| Node | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | done | - | #100 |
"""


def _make_objective_issue(number: int, body: str) -> IssueInfo:
    return IssueInfo(
        number=number,
        title="Add caching",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=NOW,
        updated_at=NOW,
        author="testuser",
    )


def _make_plan_issue(number: int, *, objective_issue: int) -> IssueInfo:
    """Create a plan issue with objective metadata."""
    body = format_plan_header_body_for_test(objective_issue=objective_issue)
    return IssueInfo(
        number=number,
        title="Plan: Setup infra",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-pr"],
        assignees=[],
        created_at=NOW,
        updated_at=NOW,
        author="testuser",
    )


def test_plan_next_with_issue_ref() -> None:
    """Test --next with explicit ISSUE_REF resolves next pending node and pre-marks."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(
            issues={42: _make_objective_issue(42, OBJECTIVE_BODY)},
        )
        fake_launcher = FakeAgentLauncher()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True, issues_gateway=issues)
        objective_issue = _make_objective_issue(42, OBJECTIVE_BODY)
        remote = FakeRemoteGitHub(
            authenticated_user="testuser",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={42: objective_issue},
            issue_comments=None,
        )
        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
            agent_launcher=fake_launcher,
            remote_github=remote,
        )

        result = runner.invoke(
            cli,
            ["objective", "plan", "42", "--next"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert fake_launcher.launch_called
        assert fake_launcher.last_call is not None
        # Should launch inner command instead of outer
        assert fake_launcher.last_call.command == "/erk:system:objective-plan-node 42 --node 1.1"
        assert "Next node: 1.1: Setup infra" in result.output
        # Should have pre-marked the node as planning via RemoteGitHub API
        objective_body_updates = [
            update for update in remote.updated_issue_bodies if update.number == 42
        ]
        assert len(objective_body_updates) == 1
        assert "planning" in objective_body_updates[0].body


def test_plan_without_node_launches_outer_command() -> None:
    """Test that without --node, the outer command is launched for interactive selection."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "plan", "42"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    # Without --node, should launch outer command for interactive flow
    assert fake_launcher.last_call.command == "/erk:objective-plan 42"


def test_mark_node_planning_updates_body() -> None:
    """Test _mark_node_planning updates the objective body with planning status."""
    from erk.cli.commands.objective.plan_cmd import _mark_node_planning

    objective_issue = _make_objective_issue(42, OBJECTIVE_BODY)
    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues={42: objective_issue},
        issue_comments=None,
    )

    _mark_node_planning(
        remote,
        owner="owner",
        repo="repo",
        issue_number=42,
        node_id="1.1",
    )

    # Should have updated the issue body
    objective_body_updates = [
        update for update in remote.updated_issue_bodies if update.number == 42
    ]
    assert len(objective_body_updates) == 1
    assert "planning" in objective_body_updates[0].body


def test_mark_node_planning_silent_on_missing_issue() -> None:
    """Test _mark_node_planning silently handles missing issues."""
    from erk.cli.commands.objective.plan_cmd import _mark_node_planning

    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues={},
        issue_comments=None,
    )

    # Should not raise — silently returns
    _mark_node_planning(
        remote,
        owner="owner",
        repo="repo",
        issue_number=999,
        node_id="1.1",
    )

    assert len(remote.updated_issue_bodies) == 0


def test_mark_node_planning_silent_on_unknown_node() -> None:
    """Test _mark_node_planning silently handles unknown node IDs."""
    from erk.cli.commands.objective.plan_cmd import _mark_node_planning

    objective_issue = _make_objective_issue(42, OBJECTIVE_BODY)
    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues={42: objective_issue},
        issue_comments=None,
    )

    # Node 9.9 doesn't exist in the roadmap
    _mark_node_planning(
        remote,
        owner="owner",
        repo="repo",
        issue_number=42,
        node_id="9.9",
    )

    # Should not have updated the body since node wasn't found
    assert len(remote.updated_issue_bodies) == 0


def test_plan_next_fails_on_branch_without_objective() -> None:
    """Test --next without ISSUE_REF fails when branch doesn't encode objective."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Plan issue #100 linked to objective #42
        plan_issue = _make_plan_issue(100, objective_issue=42)
        objective_issue = _make_objective_issue(42, OBJECTIVE_BODY)
        issues = FakeGitHubIssues(
            issues={100: plan_issue, 42: objective_issue},
        )

        fake_launcher = FakeAgentLauncher()
        # plnd/ branch without O-prefix — cannot resolve objective from branch name
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "plnd/setup-infra-01-15-1200"},
        )
        github = FakeLocalGitHub(authenticated=True, issues_gateway=issues)
        ctx = build_workspace_test_context(
            env, git=git, github=github, issues=issues, agent_launcher=fake_launcher
        )

        result = runner.invoke(
            cli,
            ["objective", "plan", "--next"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "not linked to an objective" in result.output


def test_plan_next_no_pending_nodes() -> None:
    """Test --next with all-done objective errors."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        objective_issue = _make_objective_issue(42, OBJECTIVE_ALL_DONE_BODY)
        issues = FakeGitHubIssues(
            issues={42: objective_issue},
        )
        fake_launcher = FakeAgentLauncher()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True, issues_gateway=issues)
        remote = FakeRemoteGitHub(
            authenticated_user="testuser",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={42: objective_issue},
            issue_comments=None,
        )
        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
            agent_launcher=fake_launcher,
            remote_github=remote,
        )

        result = runner.invoke(
            cli,
            ["objective", "plan", "42", "--next"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "no pending unblocked nodes" in result.output


def test_plan_next_branch_not_linked() -> None:
    """Test --next without ISSUE_REF on unlinked branch errors."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(issues={})
        fake_launcher = FakeAgentLauncher()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "random-branch"},
        )
        github = FakeLocalGitHub(authenticated=True, issues_gateway=issues)
        ctx = build_workspace_test_context(
            env, git=git, github=github, issues=issues, agent_launcher=fake_launcher
        )

        result = runner.invoke(
            cli,
            ["objective", "plan", "--next"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "not linked to an objective" in result.output
