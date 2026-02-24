"""Tests for plan duplicate-check command."""

from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.fakes.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def _make_issue(
    *,
    number: int,
    title: str,
    body: str,
) -> IssueInfo:
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
        author="test",
    )


def _non_interactive_console() -> FakeConsole:
    return FakeConsole(
        is_interactive=False,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=None,
    )


def _make_git_with_commits(
    env_cwd: Path,
    env_git_dir: Path,
    *,
    trunk_commits: list[dict[str, str]] | None = None,
) -> FakeGit:
    """Create FakeGit with recent_commits_by_branch for trunk."""
    recent_by_branch: dict[tuple[Path, str], list[dict[str, str]]] = {}
    if trunk_commits is not None:
        recent_by_branch[(env_cwd, "main")] = trunk_commits

    return FakeGit(
        git_common_dirs={env_cwd: env_git_dir},
        remote_urls={(env_cwd, "origin"): "https://github.com/owner/repo.git"},
        recent_commits_by_branch=recent_by_branch,
    )


def test_no_duplicates_found() -> None:
    """No duplicates and no relevance issues returns exit code 0."""
    executor = FakePromptExecutor(
        simulated_prompt_outputs=[
            '{"duplicates": []}',
            '{"already_implemented": false, "relevant_commits": []}',
        ],
    )
    existing = _make_issue(number=100, title="Refactor auth", body="Restructure auth flow")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={100: existing})
        git = _make_git_with_commits(
            env.cwd,
            env.git_dir,
            trunk_commits=[
                {"sha": "abc1234", "message": "Some commit", "author": "dev", "date": "1 day ago"},
            ],
        )
        ctx = build_workspace_test_context(
            env,
            git=git,
            issues=issues,
            prompt_executor=executor,
            console=_non_interactive_console(),
        )

        result = runner.invoke(
            cli,
            ["plan", "duplicate-check"],
            input="# New Plan\n\nAdd dark mode toggle",
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "Checking against 1 open plan(s):" in result.output
        assert "#100: Refactor auth" in result.output
        assert "Analyzing for semantic duplicates" in result.output
        assert "No duplicates found" in result.output


def test_duplicate_detected() -> None:
    """Detected duplicate returns exit code 1 with match info."""
    llm_output = '{"duplicates": [{"issue_number": 100, "explanation": "Both add dark mode"}]}'
    executor = FakePromptExecutor(
        simulated_prompt_outputs=[
            llm_output,
            '{"already_implemented": false, "relevant_commits": []}',
        ],
    )
    existing = _make_issue(number=100, title="Dark mode support", body="Add dark mode to app")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={100: existing})
        git = _make_git_with_commits(
            env.cwd,
            env.git_dir,
            trunk_commits=[
                {
                    "sha": "abc1234",
                    "message": "Unrelated commit",
                    "author": "dev",
                    "date": "1 day ago",
                },
            ],
        )
        ctx = build_workspace_test_context(
            env,
            git=git,
            issues=issues,
            prompt_executor=executor,
            console=_non_interactive_console(),
        )

        result = runner.invoke(
            cli,
            ["plan", "duplicate-check"],
            input="# New Plan\n\nAdd dark mode",
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "Potential duplicate(s) found" in result.output
        assert '#100: "Dark mode support"' in result.output
        assert "Both add dark mode" in result.output


def test_no_existing_plans() -> None:
    """No existing open plans returns exit code 0 with message."""
    executor = FakePromptExecutor(
        simulated_prompt_outputs=[
            '{"already_implemented": false, "relevant_commits": []}',
        ],
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={})
        git = _make_git_with_commits(
            env.cwd,
            env.git_dir,
            trunk_commits=[
                {"sha": "abc1234", "message": "Some commit", "author": "dev", "date": "1 day ago"},
            ],
        )
        ctx = build_workspace_test_context(
            env,
            git=git,
            issues=issues,
            prompt_executor=executor,
            console=_non_interactive_console(),
        )

        result = runner.invoke(
            cli,
            ["plan", "duplicate-check"],
            input="# New Plan\n\nSome plan",
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "No existing open plans" in result.output


def test_llm_error_graceful_degradation() -> None:
    """LLM failure returns exit code 1 with error message."""
    executor = FakePromptExecutor(
        simulated_prompt_error="LLM unavailable",
    )
    existing = _make_issue(number=100, title="Existing plan", body="body")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={100: existing})
        ctx = build_workspace_test_context(
            env,
            issues=issues,
            prompt_executor=executor,
            console=_non_interactive_console(),
        )

        result = runner.invoke(
            cli,
            ["plan", "duplicate-check"],
            input="# New Plan\n\nSome plan",
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "Duplicate check failed" in result.output


def test_no_input_shows_error() -> None:
    """No file or stdin shows error message."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={})
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["plan", "duplicate-check"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "No input provided" in result.output


def test_already_implemented_detected() -> None:
    """Relevance check finds match, exit 1."""
    executor = FakePromptExecutor(
        simulated_prompt_outputs=[
            '{"duplicates": []}',
            '{"already_implemented": true, "relevant_commits": '
            '[{"sha": "abc1234", "explanation": "Already adds dark mode"}]}',
        ],
    )
    existing = _make_issue(number=100, title="Existing plan", body="body")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={100: existing})
        git = _make_git_with_commits(
            env.cwd,
            env.git_dir,
            trunk_commits=[
                {
                    "sha": "abc1234",
                    "message": "Add dark mode toggle",
                    "author": "dev",
                    "date": "1 day ago",
                }
            ],
        )
        ctx = build_workspace_test_context(
            env,
            git=git,
            issues=issues,
            prompt_executor=executor,
            console=_non_interactive_console(),
        )

        result = runner.invoke(
            cli,
            ["plan", "duplicate-check"],
            input="# New Plan\n\nAdd dark mode",
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "Work may already be implemented" in result.output
        assert "abc1234" in result.output
        assert "Add dark mode toggle" in result.output


def test_no_duplicates_no_relevance_issues() -> None:
    """Both checks pass, exit 0."""
    executor = FakePromptExecutor(
        simulated_prompt_outputs=[
            '{"duplicates": []}',
            '{"already_implemented": false, "relevant_commits": []}',
        ],
    )
    existing = _make_issue(number=100, title="Existing plan", body="body")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={100: existing})
        git = _make_git_with_commits(
            env.cwd,
            env.git_dir,
            trunk_commits=[
                {
                    "sha": "abc1234",
                    "message": "Unrelated commit",
                    "author": "dev",
                    "date": "1 day ago",
                },
            ],
        )
        ctx = build_workspace_test_context(
            env,
            git=git,
            issues=issues,
            prompt_executor=executor,
            console=_non_interactive_console(),
        )

        result = runner.invoke(
            cli,
            ["plan", "duplicate-check"],
            input="# New Plan\n\nAdd user profiles",
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "No duplicates found" in result.output


def test_relevance_error_does_not_block_duplicate_check() -> None:
    """Relevance check fails gracefully, duplicate result still shown."""
    # First call succeeds (duplicate check), second fails (relevance)
    # We use sequential outputs where the first returns duplicates
    # and the second returns a malformed response
    executor = FakePromptExecutor(
        simulated_prompt_outputs=[
            '{"duplicates": []}',
            "not valid json",
        ],
    )
    existing = _make_issue(number=100, title="Existing plan", body="body")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={100: existing})
        git = _make_git_with_commits(
            env.cwd,
            env.git_dir,
            trunk_commits=[
                {"sha": "abc1234", "message": "Some commit", "author": "dev", "date": "1 day ago"},
            ],
        )
        ctx = build_workspace_test_context(
            env,
            git=git,
            issues=issues,
            prompt_executor=executor,
            console=_non_interactive_console(),
        )

        result = runner.invoke(
            cli,
            ["plan", "duplicate-check"],
            input="# New Plan\n\nSome plan",
            obj=ctx,
        )

        # Relevance errors are warnings, not blockers
        assert "Warning:" in result.output or "Relevance check failed" in result.output
        # The command still completes - no duplicates found means success
        assert result.exit_code == 0
