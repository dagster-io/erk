"""Tests for pr duplicate-check command."""

from datetime import datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.core.plan_list_service import PlanListData
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.gateway.console import FakeConsole
from tests.fakes.gateway.core import FakePlanListService
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.fakes.tests.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import create_pr_backend_with_plans


def _make_plan(
    *,
    pr_identifier: str,
    title: str,
    body: str,
) -> Plan:
    return Plan(
        pr_identifier=pr_identifier,
        title=title,
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{pr_identifier}",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
        metadata={},
        objective_id=None,
    )


def _make_plan_list_service(plans: list[Plan]) -> FakePlanListService:
    """Create a FakePlanListService from a list of Plan objects."""
    return FakePlanListService(
        data=PlanListData(plans=plans, pr_linkages={}, workflow_runs={}),
    )


def _non_interactive_console() -> FakeConsole:
    return FakeConsole(
        is_interactive=False,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=None,
    )


def test_no_duplicates_found() -> None:
    """No duplicates returns exit code 0 with success message."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"duplicates": []}',
    )
    existing = _make_plan(
        pr_identifier="100", title="[erk-pr] Refactor auth", body="Restructure auth flow"
    )
    plan_store, _ = create_pr_backend_with_plans({"100": existing})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(
            env,
            prompt_executor=executor,
            console=_non_interactive_console(),
            plan_store=plan_store,
            plan_list_service=_make_plan_list_service([existing]),
        )

        result = runner.invoke(
            cli,
            ["pr", "duplicate-check"],
            input="# New Plan\n\nAdd dark mode toggle",
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "No duplicates found" in result.output


def test_duplicate_detected() -> None:
    """Detected duplicate returns exit code 1 with match info."""
    llm_output = '{"duplicates": [{"plan_id": "100", "explanation": "Both add dark mode"}]}'
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    existing = _make_plan(
        pr_identifier="100", title="[erk-pr] Dark mode support", body="Add dark mode to app"
    )
    plan_store, _ = create_pr_backend_with_plans({"100": existing})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(
            env,
            prompt_executor=executor,
            console=_non_interactive_console(),
            plan_store=plan_store,
            plan_list_service=_make_plan_list_service([existing]),
        )

        result = runner.invoke(
            cli,
            ["pr", "duplicate-check"],
            input="# New Plan\n\nAdd dark mode",
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "Potential duplicate(s) found" in result.output
        assert '#100: "[erk-pr] Dark mode support"' in result.output
        assert "Both add dark mode" in result.output


def test_no_existing_plans() -> None:
    """No existing open PRs returns exit code 0 with message."""
    executor = FakePromptExecutor()
    plan_store, _ = create_pr_backend_with_plans({})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(
            env,
            prompt_executor=executor,
            console=_non_interactive_console(),
            plan_store=plan_store,
            plan_list_service=_make_plan_list_service([]),
        )

        result = runner.invoke(
            cli,
            ["pr", "duplicate-check"],
            input="# New Plan\n\nSome plan",
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "No existing open PRs" in result.output
        # Should not have called LLM
        assert len(executor.prompt_calls) == 0


def test_llm_error_graceful_degradation() -> None:
    """LLM failure returns exit code 1 with error message."""
    executor = FakePromptExecutor(
        simulated_prompt_error="LLM unavailable",
    )
    existing = _make_plan(pr_identifier="100", title="[erk-pr] Existing plan", body="body")
    plan_store, _ = create_pr_backend_with_plans({"100": existing})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(
            env,
            prompt_executor=executor,
            console=_non_interactive_console(),
            plan_store=plan_store,
            plan_list_service=_make_plan_list_service([existing]),
        )

        result = runner.invoke(
            cli,
            ["pr", "duplicate-check"],
            input="# New Plan\n\nSome plan",
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "Duplicate check failed" in result.output


def test_no_input_shows_error() -> None:
    """No file or stdin shows error message."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env)

        result = runner.invoke(
            cli,
            ["pr", "duplicate-check"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "No input provided" in result.output


def test_plan_flag_fetches_and_excludes_self() -> None:
    """--plan fetches the plan body and excludes it from comparison set."""
    llm_output = '{"duplicates": []}'
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    plan_100 = _make_plan(pr_identifier="100", title="[erk-pr] Plan A", body="body A")
    plan_200 = _make_plan(pr_identifier="200", title="[erk-pr] Plan B", body="body B for checking")
    plan_store, _ = create_pr_backend_with_plans({"100": plan_100, "200": plan_200})

    issue_200 = IssueInfo(
        number=200,
        title="Plan B",
        body="body B for checking",
        state="OPEN",
        url="https://github.com/owner/repo/issues/200",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
        author="test-user",
    )
    fake_remote = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues={200: issue_200},
        issue_comments=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(
            env,
            prompt_executor=executor,
            console=_non_interactive_console(),
            plan_store=plan_store,
            plan_list_service=_make_plan_list_service([plan_100, plan_200]),
            remote_github=fake_remote,
        )

        result = runner.invoke(
            cli,
            ["pr", "duplicate-check", "--plan", "200"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "No duplicates found" in result.output
        # Verify the LLM was called (plan 100 exists as comparison)
        assert len(executor.prompt_calls) == 1
        prompt_text = executor.prompt_calls[0][0]
        # Plan 200's body should be in the NEW PLAN section
        assert "body B for checking" in prompt_text
        # Plan 200 should NOT appear in EXISTING PLANS (excluded self)
        assert "#200" not in prompt_text
        # Plan 100 should appear in EXISTING PLANS
        assert "#100" in prompt_text


def test_progress_reporting_lists_plans() -> None:
    """Output lists each plan being compared and shows analyzing message."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"duplicates": []}',
    )
    plan_100 = _make_plan(pr_identifier="100", title="[erk-pr] Refactor auth", body="body A")
    plan_200 = _make_plan(pr_identifier="200", title="[erk-pr] Add dark mode", body="body B")
    plan_store, _ = create_pr_backend_with_plans({"100": plan_100, "200": plan_200})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(
            env,
            prompt_executor=executor,
            console=_non_interactive_console(),
            plan_store=plan_store,
            plan_list_service=_make_plan_list_service([plan_100, plan_200]),
        )

        result = runner.invoke(
            cli,
            ["pr", "duplicate-check"],
            input="# New Plan\n\nSome plan",
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "Checking against 2 open PR(s):" in result.output
        assert "#100: [erk-pr] Refactor auth" in result.output
        assert "#200: [erk-pr] Add dark mode" in result.output
        assert "Analyzing for semantic duplicates..." in result.output


def test_plan_flag_not_found() -> None:
    """--plan with nonexistent plan ID returns exit code 1 with error."""
    plan_store, _ = create_pr_backend_with_plans({})
    fake_remote = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues={},
        issue_comments=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(
            env,
            console=_non_interactive_console(),
            plan_store=plan_store,
            plan_list_service=_make_plan_list_service([]),
            remote_github=fake_remote,
        )

        result = runner.invoke(
            cli,
            ["pr", "duplicate-check", "--plan", "999"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "not found" in result.output


def test_plan_and_file_mutually_exclusive() -> None:
    """Using both --plan and --file produces an error."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env)

        # Create a temp file for --file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Plan\n\nSome content")
            temp_path = f.name

        result = runner.invoke(
            cli,
            ["pr", "duplicate-check", "--plan", "100", "--file", temp_path],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "Cannot use both" in result.output
