"""Test context factories for creating ErkContext instances.

This module provides factory functions for creating test contexts with fake
implementations. These were moved here from src/erk/core/context.py to keep
fake imports out of production code.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from erk.artifacts.paths import ErkPackageInfo
from erk.core.services.objective_list_service import RealObjectiveListService
from erk_shared.context.context import ErkContext
from erk_shared.context.types import GlobalConfig, LoadedConfig, NoRepoSentinel, RepoContext
from erk_shared.core.objective_list_service import ObjectiveListService
from erk_shared.core.plan_list_service import PlanListService
from erk_shared.core.prompt_executor import PromptExecutor
from erk_shared.core.script_writer import ScriptWriter
from erk_shared.gateway.agent_docs.abc import AgentDocs
from erk_shared.gateway.agent_launcher.abc import AgentLauncher
from erk_shared.gateway.claude_installation.abc import ClaudeInstallation
from erk_shared.gateway.cmux.abc import Cmux
from erk_shared.gateway.codespace.abc import Codespace
from erk_shared.gateway.codespace_registry.abc import CodespaceRegistry
from erk_shared.gateway.completion.abc import Completion
from erk_shared.gateway.console.abc import Console
from erk_shared.gateway.erk_installation.abc import ErkInstallation
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.dry_run import DryRunGit
from erk_shared.gateway.github.abc import LocalGitHub
from erk_shared.gateway.github.dry_run import DryRunLocalGitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.types import RepoInfo
from erk_shared.gateway.github_admin.abc import GitHubAdmin
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.branch_ops.abc import GraphiteBranchOps
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.shell.abc import Shell
from erk_shared.gateway.time.abc import Time
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.fakes.gateway.core import FakeObjectiveListService, FakePlanListService

if TYPE_CHECKING:
    from erk_shared.core.health_check_runner import HealthCheckRunner


def minimal_context(git: Git, cwd: Path, dry_run: bool = False) -> ErkContext:
    """Create minimal context with only git configured, rest are test defaults.

    Useful for simple tests that only need git operations. Other integration
    classes are initialized with their standard test defaults (fake implementations).

    Args:
        git: The Git implementation (usually FakeGit with test configuration)
        cwd: Current working directory path for the context
        dry_run: Whether to enable dry-run mode (default False)

    Returns:
        ErkContext with git configured and other dependencies using test defaults

    Note:
        For more complex test setup with custom configs or multiple integration classes,
        use context_for_test() instead.
    """
    from tests.fakes.gateway.agent_docs import FakeAgentDocs
    from tests.fakes.gateway.agent_launcher import FakeAgentLauncher
    from tests.fakes.gateway.claude_installation import FakeClaudeInstallation
    from tests.fakes.gateway.cmux import FakeCmux
    from tests.fakes.gateway.codespace import FakeCodespace
    from tests.fakes.gateway.codespace_registry import FakeCodespaceRegistry
    from tests.fakes.gateway.completion import FakeCompletion
    from tests.fakes.gateway.console import FakeConsole
    from tests.fakes.gateway.erk_installation import FakeErkInstallation
    from tests.fakes.gateway.github import FakeLocalGitHub
    from tests.fakes.gateway.github_admin import FakeGitHubAdmin
    from tests.fakes.gateway.github_issues import FakeGitHubIssues
    from tests.fakes.gateway.graphite import FakeGraphite
    from tests.fakes.gateway.graphite_branch_ops import FakeGraphiteBranchOps
    from tests.fakes.gateway.http import FakeHttpClient
    from tests.fakes.gateway.shell import FakeShell
    from tests.fakes.gateway.time import FakeTime
    from tests.fakes.tests.prompt_executor import FakePromptExecutor
    from tests.fakes.tests.script_writer import FakeScriptWriter

    fake_issues = FakeGitHubIssues()
    fake_github = FakeLocalGitHub(issues_gateway=fake_issues)
    fake_graphite = FakeGraphite()
    fake_graphite_branch_ops = FakeGraphiteBranchOps()
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    fake_console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=None,
    )
    fake_time = FakeTime()

    return ErkContext(
        git=git,
        github=fake_github,
        github_admin=FakeGitHubAdmin(),
        plan_store=PlannedPRBackend(fake_github, fake_issues, time=fake_time),
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        console=fake_console,
        shell=FakeShell(),
        codespace=fake_codespace,
        cmux=FakeCmux(workspace_ref="fake-ws"),
        agent_launcher=FakeAgentLauncher(),
        agent_docs=FakeAgentDocs(files={}, has_docs_dir=True),
        completion=FakeCompletion(),
        time=fake_time,
        erk_installation=FakeErkInstallation(),
        script_writer=FakeScriptWriter(),
        plan_list_service=FakePlanListService(),
        objective_list_service=FakeObjectiveListService(data=None),
        codespace_registry=FakeCodespaceRegistry(),
        claude_installation=FakeClaudeInstallation.for_test(),
        prompt_executor=FakePromptExecutor(),
        cwd=cwd,
        global_config=None,
        local_config=LoadedConfig.test(),
        repo=NoRepoSentinel(),
        repo_info=None,
        http_client=FakeHttpClient(),
        dry_run=dry_run,
        debug=False,
    )


def context_for_test(
    *,
    git: Git | None = None,
    github: LocalGitHub | None = None,
    github_admin: GitHubAdmin | None = None,
    issues: GitHubIssues | None = None,
    plan_store: PlanBackend | None = None,
    graphite: Graphite | None = None,
    console: Console | None = None,
    shell: Shell | None = None,
    codespace: Codespace | None = None,
    cmux: Cmux | None = None,
    agent_launcher: AgentLauncher | None = None,
    agent_docs: AgentDocs | None = None,
    completion: Completion | None = None,
    time: Time | None = None,
    erk_installation: ErkInstallation | None = None,
    script_writer: ScriptWriter | None = None,
    plan_list_service: PlanListService | None = None,
    objective_list_service: ObjectiveListService | None = None,
    codespace_registry: CodespaceRegistry | None = None,
    claude_installation: ClaudeInstallation | None = None,
    prompt_executor: PromptExecutor | None = None,
    cwd: Path | None = None,
    global_config: GlobalConfig | None = None,
    local_config: LoadedConfig | None = None,
    repo: RepoContext | NoRepoSentinel | None = None,
    repo_info: RepoInfo | None = None,
    package_info: ErkPackageInfo | None = None,
    remote_github: RemoteGitHub | None = None,
    health_check_runner: HealthCheckRunner | None = None,
    dry_run: bool = False,
    debug: bool = False,
) -> ErkContext:
    """Create test context with optional pre-configured integration classes.

    Provides full control over all context parameters with sensible test defaults
    for any unspecified values. Use this for complex test scenarios that need
    specific configurations for multiple integration classes.

    Args:
        git: Optional Git implementation. If None, creates empty FakeGit.
        github: Optional GitHub implementation. If None, creates empty FakeLocalGitHub.
        issues: Optional GitHubIssues implementation.
                   If None, creates empty FakeGitHubIssues.
        graphite: Optional Graphite implementation.
                     If None, creates empty FakeGraphite.
        console: Optional Console implementation. If None, creates FakeConsole.
        shell: Optional Shell implementation. If None, creates empty FakeShell.
        completion: Optional Completion implementation.
                       If None, creates empty FakeCompletion.
        erk_installation: Optional ErkInstallation implementation.
                          If None, creates FakeErkInstallation with test config.
        script_writer: Optional ScriptWriter implementation.
                      If None, creates empty FakeScriptWriter.
        prompt_executor: Optional PromptExecutor. If None, creates FakePromptExecutor.
        cwd: Optional current working directory. If None, uses sentinel_path().
        global_config: Optional GlobalConfig. If None, uses test defaults.
        local_config: Optional LoadedConfig. If None, uses empty defaults.
        repo: Optional RepoContext or NoRepoSentinel. If None, uses NoRepoSentinel().
        repo_info: Optional RepoInfo. If None, stays None.
        dry_run: Whether to enable dry-run mode (default False).
        debug: Whether to enable debug mode (default False).

    Returns:
        ErkContext configured with provided values and test defaults
    """
    from erk_shared.gateway.graphite.branch_ops.dry_run import DryRunGraphiteBranchOps
    from erk_shared.gateway.graphite.dry_run import DryRunGraphite
    from tests.fakes.gateway.agent_launcher import FakeAgentLauncher
    from tests.fakes.gateway.claude_installation import FakeClaudeInstallation
    from tests.fakes.gateway.cmux import FakeCmux
    from tests.fakes.gateway.codespace import FakeCodespace
    from tests.fakes.gateway.codespace_registry import FakeCodespaceRegistry
    from tests.fakes.gateway.completion import FakeCompletion
    from tests.fakes.gateway.console import FakeConsole
    from tests.fakes.gateway.erk_installation import FakeErkInstallation
    from tests.fakes.gateway.git import FakeGit
    from tests.fakes.gateway.github import FakeLocalGitHub
    from tests.fakes.gateway.github_admin import FakeGitHubAdmin
    from tests.fakes.gateway.github_issues import FakeGitHubIssues
    from tests.fakes.gateway.graphite import FakeGraphite
    from tests.fakes.gateway.graphite_branch_ops import FakeGraphiteBranchOps
    from tests.fakes.gateway.http import FakeHttpClient
    from tests.fakes.gateway.shell import FakeShell
    from tests.fakes.gateway.time import FakeTime
    from tests.fakes.tests.prompt_executor import FakePromptExecutor
    from tests.fakes.tests.script_writer import FakeScriptWriter
    from tests.test_utils.paths import sentinel_path

    if git is None:
        git = FakeGit()

    # Track whether issues was explicitly passed (for composition logic below)
    issues_explicitly_passed = issues is not None

    # Create issues first since it's composed into github
    if issues is None:
        issues = FakeGitHubIssues()

    # Compose github with issues
    # If github is provided without issues_gateway, use github as-is (it has its own issues)
    # Only inject issues if caller explicitly passed BOTH github and issues
    if github is None:
        github = FakeLocalGitHub(issues_gateway=issues)
    elif isinstance(github, FakeLocalGitHub) and issues_explicitly_passed:
        # Caller passed both github and issues separately - inject issues
        # into the existing FakeLocalGitHub instance to preserve test references
        github._issues_gateway = issues

    if github_admin is None:
        github_admin = FakeGitHubAdmin()

    if plan_store is None:
        plan_store = PlannedPRBackend(github, issues, time=FakeTime())

    # Handle graphite based on global_config.use_graphite to match production behavior
    # When use_graphite=False, use GraphiteDisabled sentinel so that
    # ErkContext.branch_manager returns GitBranchManager
    graphite_branch_ops: GraphiteBranchOps | None = None
    if graphite is None:
        # Need to check global_config.use_graphite - but it might be None or not set yet
        # If global_config is None, default will be set later with use_graphite=False
        use_graphite_from_config = (
            global_config.use_graphite if global_config is not None else False
        )
        if use_graphite_from_config:
            graphite = FakeGraphite()
            graphite_branch_ops = graphite.create_linked_branch_ops()
        else:
            graphite = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)
    elif isinstance(graphite, FakeGraphite):
        # Graphite is enabled and is a fake - create linked branch ops
        graphite_branch_ops = graphite.create_linked_branch_ops()
    elif not isinstance(graphite, GraphiteDisabled):
        # Graphite is enabled but not a fake - create unlinked branch ops
        graphite_branch_ops = FakeGraphiteBranchOps()

    if console is None:
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )

    if shell is None:
        shell = FakeShell()

    if codespace is None:
        codespace = FakeCodespace(
            run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
        )

    if cmux is None:
        cmux = FakeCmux(workspace_ref="fake-ws")

    if agent_launcher is None:
        agent_launcher = FakeAgentLauncher()

    if agent_docs is None:
        from tests.fakes.gateway.agent_docs import FakeAgentDocs

        agent_docs = FakeAgentDocs(files={}, has_docs_dir=True)

    if completion is None:
        completion = FakeCompletion()

    if time is None:
        time = FakeTime()

    if script_writer is None:
        script_writer = FakeScriptWriter()

    if plan_list_service is None:
        plan_list_service = FakePlanListService()

    if objective_list_service is None:
        objective_list_service = RealObjectiveListService(github, time=time)

    if codespace_registry is None:
        codespace_registry = FakeCodespaceRegistry()

    if claude_installation is None:
        claude_installation = FakeClaudeInstallation.for_test()

    if prompt_executor is None:
        prompt_executor = FakePromptExecutor()

    if global_config is None:
        global_config = GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=False,
            shell_setup_complete=False,
            github_planning=True,
        )

    if erk_installation is None:
        erk_installation = FakeErkInstallation(config=global_config)

    if local_config is None:
        local_config = LoadedConfig.test()

    if repo is None:
        repo = NoRepoSentinel()

    # Apply dry-run wrappers if needed (matching production behavior)
    # Note: DryRunLocalGitHub composes DryRunGitHubIssues internally for github.issues
    if dry_run:
        git = DryRunGit(git)
        graphite = DryRunGraphite(graphite)
        if graphite_branch_ops is not None:
            graphite_branch_ops = DryRunGraphiteBranchOps(graphite_branch_ops)
        github = DryRunLocalGitHub(github)

    return ErkContext(
        git=git,
        github=github,
        github_admin=github_admin,
        plan_store=plan_store,
        graphite=graphite,
        graphite_branch_ops=graphite_branch_ops,
        console=console,
        shell=shell,
        codespace=codespace,
        cmux=cmux,
        agent_launcher=agent_launcher,
        agent_docs=agent_docs,
        completion=completion,
        time=time,
        erk_installation=erk_installation,
        script_writer=script_writer,
        plan_list_service=plan_list_service,
        objective_list_service=objective_list_service,
        codespace_registry=codespace_registry,
        claude_installation=claude_installation,
        prompt_executor=prompt_executor,
        cwd=cwd or sentinel_path(),
        global_config=global_config,
        local_config=local_config,
        repo=repo,
        repo_info=repo_info,
        package_info=package_info,
        health_check_runner=health_check_runner,
        http_client=FakeHttpClient(),
        remote_github=remote_github,
        dry_run=dry_run,
        debug=debug,
    )
