"""Application context with dependency injection.

This module provides factory functions for erk CLI context creation.
The unified ErkContext dataclass is defined in erk_shared.context and
re-exported here for backwards compatibility.
"""

import shutil
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, cast

import click
import tomlkit

from erk.cli.config import load_config
from erk.core.claude_executor import RealClaudeExecutor
from erk.core.completion import RealCompletion
from erk.core.implementation_queue.github.real import RealGitHubAdmin
from erk.core.planner.registry_real import RealPlannerRegistry
from erk.core.repo_discovery import discover_repo_or_sentinel, ensure_erk_metadata_dir
from erk.core.script_writer import RealScriptWriter
from erk.core.services.plan_list_service import RealPlanListService
from erk.core.shell import RealShell

# Re-export ErkContext from erk_shared for isinstance() compatibility
# This ensures that both erk CLI and kit commands use the same class identity
from erk_shared.context.context import ErkContext as ErkContext

# Re-export types from erk_shared.context
from erk_shared.context.types import GlobalConfig as GlobalConfig
from erk_shared.context.types import LoadedConfig as LoadedConfig
from erk_shared.context.types import NoRepoSentinel as NoRepoSentinel
from erk_shared.context.types import RepoContext as RepoContext

# Import ABCs and fakes from erk_shared.core
from erk_shared.core import (
    ClaudeExecutor,
    FakePlanListService,
    PlanListService,
    PlannerRegistry,
    ScriptWriter,
)
from erk_shared.extraction.claude_installation import ClaudeInstallation

# Import erk-specific integrations
from erk_shared.gateway.completion import Completion
from erk_shared.gateway.console.abc import Console
from erk_shared.gateway.console.real import InteractiveConsole, ScriptConsole
from erk_shared.gateway.erk_installation.abc import ErkInstallation
from erk_shared.gateway.erk_installation.real import RealErkInstallation
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.disabled import (
    GraphiteDisabled,
    GraphiteDisabledReason,
)
from erk_shared.gateway.graphite.dry_run import DryRunGraphite
from erk_shared.gateway.graphite.real import RealGraphite
from erk_shared.gateway.shell import Shell
from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.real import RealTime
from erk_shared.git.abc import Git
from erk_shared.git.dry_run import DryRunGit
from erk_shared.git.real import RealGit
from erk_shared.github.abc import GitHub
from erk_shared.github.dry_run import DryRunGitHub
from erk_shared.github.issues import DryRunGitHubIssues, GitHubIssues, RealGitHubIssues
from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.real import RealGitHub
from erk_shared.github.types import RepoInfo
from erk_shared.github_admin.abc import GitHubAdmin
from erk_shared.output.output import user_output
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.store import PlanStore
from erk_shared.prompt_executor import PromptExecutor
from erk_shared.prompt_executor.real import RealPromptExecutor


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
    from tests.fakes.claude_executor import FakeClaudeExecutor
    from tests.fakes.script_writer import FakeScriptWriter

    from erk.core.planner.registry_fake import FakePlannerRegistry
    from erk_shared.extraction.claude_installation import FakeClaudeInstallation
    from erk_shared.gateway.completion import FakeCompletion
    from erk_shared.gateway.console.fake import FakeConsole
    from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
    from erk_shared.gateway.graphite.fake import FakeGraphite
    from erk_shared.gateway.shell import FakeShell
    from erk_shared.gateway.time.fake import FakeTime
    from erk_shared.github.fake import FakeGitHub
    from erk_shared.github.issues import FakeGitHubIssues
    from erk_shared.github_admin.fake import FakeGitHubAdmin
    from erk_shared.prompt_executor.fake import FakePromptExecutor

    fake_github = FakeGitHub()
    fake_issues = FakeGitHubIssues()
    fake_graphite = FakeGraphite()
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
        issues=fake_issues,
        plan_store=GitHubPlanStore(fake_issues, fake_time),
        graphite=fake_graphite,
        console=fake_console,
        shell=FakeShell(),
        claude_executor=FakeClaudeExecutor(),
        completion=FakeCompletion(),
        time=fake_time,
        erk_installation=FakeErkInstallation(),
        script_writer=FakeScriptWriter(),
        plan_list_service=FakePlanListService(),
        planner_registry=FakePlannerRegistry(),
        claude_installation=FakeClaudeInstallation.for_test(),
        prompt_executor=FakePromptExecutor(),
        cwd=cwd,
        global_config=None,
        local_config=LoadedConfig.test(),
        repo=NoRepoSentinel(),
        repo_info=None,
        dry_run=dry_run,
        debug=False,
    )


def context_for_test(
    *,
    git: Git | None = None,
    github: GitHub | None = None,
    github_admin: GitHubAdmin | None = None,
    issues: GitHubIssues | None = None,
    plan_store: PlanStore | None = None,
    graphite: Graphite | None = None,
    console: Console | None = None,
    shell: Shell | None = None,
    claude_executor: ClaudeExecutor | None = None,
    completion: Completion | None = None,
    time: Time | None = None,
    erk_installation: ErkInstallation | None = None,
    script_writer: ScriptWriter | None = None,
    plan_list_service: PlanListService | None = None,
    planner_registry: PlannerRegistry | None = None,
    claude_installation: ClaudeInstallation | None = None,
    prompt_executor: PromptExecutor | None = None,
    cwd: Path | None = None,
    global_config: GlobalConfig | None = None,
    local_config: LoadedConfig | None = None,
    repo: RepoContext | NoRepoSentinel | None = None,
    repo_info: RepoInfo | None = None,
    dry_run: bool = False,
    debug: bool = False,
) -> ErkContext:
    """Create test context with optional pre-configured integration classes.

    Provides full control over all context parameters with sensible test defaults
    for any unspecified values. Use this for complex test scenarios that need
    specific configurations for multiple integration classes.

    Args:
        git: Optional Git implementation. If None, creates empty FakeGit.
        github: Optional GitHub implementation. If None, creates empty FakeGitHub.
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
    from tests.fakes.claude_executor import FakeClaudeExecutor
    from tests.fakes.script_writer import FakeScriptWriter
    from tests.test_utils.paths import sentinel_path

    from erk.core.planner.registry_fake import FakePlannerRegistry
    from erk_shared.extraction.claude_installation import FakeClaudeInstallation
    from erk_shared.gateway.completion import FakeCompletion
    from erk_shared.gateway.console.fake import FakeConsole
    from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
    from erk_shared.gateway.graphite.dry_run import DryRunGraphite
    from erk_shared.gateway.graphite.fake import FakeGraphite
    from erk_shared.gateway.shell import FakeShell
    from erk_shared.gateway.time.fake import FakeTime
    from erk_shared.git.fake import FakeGit
    from erk_shared.github.fake import FakeGitHub
    from erk_shared.github.issues import FakeGitHubIssues
    from erk_shared.github_admin.fake import FakeGitHubAdmin
    from erk_shared.prompt_executor.fake import FakePromptExecutor

    if git is None:
        git = FakeGit()

    if github is None:
        github = FakeGitHub()

    if github_admin is None:
        github_admin = FakeGitHubAdmin()

    if issues is None:
        issues = FakeGitHubIssues()

    if plan_store is None:
        # Always compose from issues layer - no separate FakePlanStore
        # This ensures tests use the same composition as production code
        plan_store = GitHubPlanStore(issues)

    # Handle graphite based on global_config.use_graphite to match production behavior
    # When use_graphite=False, use GraphiteDisabled sentinel so that
    # ErkContext.branch_manager returns GitBranchManager
    if graphite is None:
        # Need to check global_config.use_graphite - but it might be None or not set yet
        # If global_config is None, default will be set later with use_graphite=False
        use_graphite_from_config = (
            global_config.use_graphite if global_config is not None else False
        )
        if use_graphite_from_config:
            graphite = FakeGraphite()
        else:
            graphite = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)

    if console is None:
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )

    if shell is None:
        shell = FakeShell()

    if claude_executor is None:
        claude_executor = FakeClaudeExecutor()

    if completion is None:
        completion = FakeCompletion()

    if time is None:
        time = FakeTime()

    if script_writer is None:
        script_writer = FakeScriptWriter()

    if plan_list_service is None:
        # If github and issues were provided, wire them up via RealPlanListService
        # so that tests get realistic behavior when testing plan list functionality
        plan_list_service = RealPlanListService(github, issues)

    if planner_registry is None:
        planner_registry = FakePlannerRegistry()

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
    if dry_run:
        git = DryRunGit(git)
        graphite = DryRunGraphite(graphite)
        github = DryRunGitHub(github)
        issues = DryRunGitHubIssues(issues)

    return ErkContext(
        git=git,
        github=github,
        github_admin=github_admin,
        issues=issues,
        plan_store=plan_store,
        graphite=graphite,
        console=console,
        shell=shell,
        claude_executor=claude_executor,
        completion=completion,
        time=time,
        erk_installation=erk_installation,
        script_writer=script_writer,
        plan_list_service=plan_list_service,
        planner_registry=planner_registry,
        claude_installation=claude_installation,
        prompt_executor=prompt_executor,
        cwd=cwd or sentinel_path(),
        global_config=global_config,
        local_config=local_config,
        repo=repo,
        repo_info=repo_info,
        dry_run=dry_run,
        debug=debug,
    )


def write_trunk_to_pyproject(repo_root: Path, trunk: str, git: Git | None = None) -> None:
    """Write trunk branch configuration to pyproject.toml.

    Creates or updates the [tool.erk] section with trunk_branch setting.
    Preserves existing formatting and comments using tomlkit.

    Args:
        repo_root: Path to the repository root directory
        trunk: Trunk branch name to configure
        git: Optional Git interface for path checking (uses .exists() if None)
    """
    pyproject_path = repo_root / "pyproject.toml"

    # Check existence using git if available (for test compatibility)
    if git is not None:
        path_exists = git.path_exists(pyproject_path)
    else:
        path_exists = pyproject_path.exists()

    # Load existing file or create new document
    if path_exists:
        with pyproject_path.open("r", encoding="utf-8") as f:
            doc = tomlkit.load(f)
    else:
        doc = tomlkit.document()

    # Ensure [tool] section exists
    if "tool" not in doc:
        assert isinstance(doc, MutableMapping), f"Expected MutableMapping, got {type(doc)}"
        cast(dict[str, Any], doc)["tool"] = tomlkit.table()

    # Ensure [tool.erk] section exists
    tool_section = cast(dict[str, Any], doc["tool"])
    if "erk" not in tool_section:
        tool_section["erk"] = tomlkit.table()

    # Set trunk_branch value
    cast(dict[str, Any], tool_section["erk"])["trunk_branch"] = trunk

    # Write back to file
    with pyproject_path.open("w", encoding="utf-8") as f:
        tomlkit.dump(doc, f)


def safe_cwd() -> tuple[Path | None, str | None]:
    """Get current working directory, detecting if it no longer exists.

    Uses LBYL approach: checks if the operation will succeed before attempting it.

    Returns:
        tuple[Path | None, str | None]: (path, error_message)
        - If successful: (Path, None)
        - If directory deleted: (None, error_message)

    Note:
        This is an acceptable use of try/except since we're wrapping a third-party
        API (Path.cwd()) that provides no way to check the condition first.
    """
    try:
        cwd_path = Path.cwd()
        return (cwd_path, None)
    except (FileNotFoundError, OSError):
        return (
            None,
            "Current working directory no longer exists",
        )


def create_context(*, dry_run: bool, script: bool = False, debug: bool = False) -> ErkContext:
    """Create production context with real implementations.

    Called at CLI entry point to create the context for the entire
    command execution.

    Args:
        dry_run: If True, wrap all dependencies with dry-run wrappers that
                 print intended actions without executing them
        script: If True, use ScriptConsole to suppress diagnostic output
                for shell integration mode (default False)
        debug: If True, enable debug mode for error handling (default False)

    Returns:
        ErkContext with real implementations, wrapped in dry-run
        wrappers if dry_run=True

    Example:
        >>> ctx = create_context(dry_run=False, script=False)
        >>> worktrees = ctx.git.list_worktrees(Path("/repo"))
        >>> erk_root = ctx.global_config.erk_root
    """
    # 1. Capture cwd (no deps)
    cwd_result, error_msg = safe_cwd()
    if cwd_result is None:
        assert error_msg is not None
        # Emit clear error and exit
        user_output(click.style("Error: ", fg="red") + error_msg)
        user_output("\nThe directory you're running from has been deleted.")
        user_output("Please change to a valid directory and try again.")
        raise SystemExit(1)

    cwd = cwd_result

    # 2. Create erk installation gateway
    erk_installation = RealErkInstallation()

    # 3. Load global config (no deps) - None if not exists (for init command)
    global_config: GlobalConfig | None
    if erk_installation.config_exists():
        global_config = erk_installation.load_config()
    else:
        # For init command only: config doesn't exist yet
        global_config = None

    # 4. Create integration classes (need git for repo discovery)
    # Create time and console first
    time: Time = RealTime()
    console: Console = ScriptConsole() if script else InteractiveConsole()
    git: Git = RealGit()

    # Create Graphite based on config and availability
    graphite: Graphite
    if global_config is not None and global_config.use_graphite:
        # Config says use Graphite - check if gt is installed
        if shutil.which("gt") is None:
            graphite = GraphiteDisabled(GraphiteDisabledReason.NOT_INSTALLED)
        else:
            graphite = RealGraphite()
    else:
        # Graphite disabled by config (or config doesn't exist yet)
        graphite = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)

    # 5. Discover repo (only needs cwd, erk_root, git)
    # If global_config is None, use placeholder path for repo discovery
    erk_root = global_config.erk_root if global_config else erk_installation.root() / "worktrees"
    repo = discover_repo_or_sentinel(cwd, erk_root, git)

    # 6. Fetch repo_info (if in a repo with origin remote)
    # Note: try-except is acceptable at CLI entry point boundary per LBYL conventions
    repo_info: RepoInfo | None = None
    if not isinstance(repo, NoRepoSentinel):
        try:
            remote_url = git.get_remote_url(repo.root)
            owner, name = parse_git_remote_url(remote_url)
            repo_info = RepoInfo(owner=owner, name=name)
        except ValueError:
            # No origin remote configured - repo_info stays None
            pass

    # 7. Load local config (or defaults if no repo)
    # Loaded early so plans_repo can be used for GitHubIssues
    if isinstance(repo, NoRepoSentinel):
        local_config = LoadedConfig.test()
    else:
        # Ensure metadata directories exist (needed for worktrees)
        ensure_erk_metadata_dir(repo)
        # Load config from primary location (.erk/config.toml)
        # Legacy locations are detected by 'erk doctor' only
        local_config = load_config(repo.root)

    # 8. Create GitHub-related classes (need repo_info, local_config)
    github: GitHub = RealGitHub(time, repo_info)
    # Use plans_repo for cross-repo plan issue management if configured
    issues: GitHubIssues = RealGitHubIssues(target_repo=local_config.plans_repo)
    plan_store: PlanStore = GitHubPlanStore(issues)
    plan_list_service: PlanListService = RealPlanListService(github, issues)

    # 9. Apply dry-run wrappers if needed
    if dry_run:
        git = DryRunGit(git)
        graphite = DryRunGraphite(graphite)
        github = DryRunGitHub(github)
        issues = DryRunGitHubIssues(issues)

    # 10. Create claude installation and prompt executor
    from erk_shared.extraction.claude_installation import RealClaudeInstallation

    real_claude_installation: ClaudeInstallation = RealClaudeInstallation()
    prompt_executor: PromptExecutor = RealPromptExecutor(time)

    # 11. Create context with all values
    return ErkContext(
        git=git,
        github=github,
        github_admin=RealGitHubAdmin(),
        issues=issues,
        plan_store=plan_store,
        graphite=graphite,
        console=console,
        shell=RealShell(),
        claude_executor=RealClaudeExecutor(console=console),
        completion=RealCompletion(),
        time=time,
        erk_installation=erk_installation,
        script_writer=RealScriptWriter(),
        plan_list_service=plan_list_service,
        planner_registry=RealPlannerRegistry(erk_installation.get_planners_config_path()),
        claude_installation=real_claude_installation,
        prompt_executor=prompt_executor,
        cwd=cwd,
        global_config=global_config,
        local_config=local_config,
        repo=repo,
        repo_info=repo_info,
        dry_run=dry_run,
        debug=debug,
    )


def regenerate_context(existing_ctx: ErkContext) -> ErkContext:
    """Regenerate context with fresh cwd.

    Creates a new ErkContext with:
    - Current working directory (Path.cwd())
    - Preserved dry_run state and operation instances

    Use this after mutations like os.chdir() or worktree removal
    to ensure ctx.cwd reflects actual current directory.

    Args:
        existing_ctx: Current context to preserve settings from

    Returns:
        New ErkContext with regenerated state

    Example:
        # After os.chdir() or worktree removal
        ctx = regenerate_context(ctx)
    """
    return create_context(dry_run=existing_ctx.dry_run, debug=existing_ctx.debug)
