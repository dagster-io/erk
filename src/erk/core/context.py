"""Application context with dependency injection.

This module provides factory functions for erk CLI context creation.
The unified ErkContext dataclass is defined in erk_shared.context and
re-exported here for backwards compatibility.
"""

from pathlib import Path

import click
import tomlkit

from erk.cli.config import load_config
from erk.core.claude_executor import RealClaudeExecutor
from erk.core.completion import RealCompletion
from erk.core.config_store import RealConfigStore
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
    ConfigStore,
    FakePlanListService,
    PlanListService,
    PlannerRegistry,
    ScriptWriter,
)
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore

# Import erk-specific integrations
from erk_shared.gateway.completion import Completion
from erk_shared.gateway.feedback import InteractiveFeedback, SuppressedFeedback, UserFeedback
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.dry_run import DryRunGraphite
from erk_shared.gateway.graphite.real import RealGraphite
from erk_shared.gateway.shell import Shell
from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.real import RealTime
from erk_shared.gateway.wt_stack.wt_stack import WtStack
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

    from erk.core.config_store import FakeConfigStore
    from erk.core.planner.registry_fake import FakePlannerRegistry
    from erk_shared.extraction.claude_code_session_store import FakeClaudeCodeSessionStore
    from erk_shared.gateway.completion import FakeCompletion
    from erk_shared.gateway.feedback import FakeUserFeedback
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
    return ErkContext(
        git=git,
        github=fake_github,
        github_admin=FakeGitHubAdmin(),
        issues=fake_issues,
        plan_store=GitHubPlanStore(fake_issues),
        graphite=fake_graphite,
        wt_stack=WtStack(git, cwd, fake_graphite),
        shell=FakeShell(),
        claude_executor=FakeClaudeExecutor(),
        completion=FakeCompletion(),
        time=FakeTime(),
        config_store=FakeConfigStore(config=None),
        script_writer=FakeScriptWriter(),
        feedback=FakeUserFeedback(),
        plan_list_service=FakePlanListService(),
        planner_registry=FakePlannerRegistry(),
        session_store=FakeClaudeCodeSessionStore(),
        prompt_executor=FakePromptExecutor(),
        cwd=cwd,
        global_config=None,
        local_config=LoadedConfig(env={}, post_create_commands=[], post_create_shell=None),
        repo=NoRepoSentinel(),
        repo_info=None,
        dry_run=dry_run,
        debug=False,
    )


def context_for_test(
    git: Git | None = None,
    github: GitHub | None = None,
    github_admin: GitHubAdmin | None = None,
    issues: GitHubIssues | None = None,
    plan_store: PlanStore | None = None,
    graphite: Graphite | None = None,
    wt_stack: WtStack | None = None,
    shell: Shell | None = None,
    claude_executor: ClaudeExecutor | None = None,
    completion: Completion | None = None,
    time: Time | None = None,
    config_store: ConfigStore | None = None,
    script_writer: ScriptWriter | None = None,
    feedback: UserFeedback | None = None,
    plan_list_service: PlanListService | None = None,
    planner_registry: PlannerRegistry | None = None,
    session_store: ClaudeCodeSessionStore | None = None,
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
        shell: Optional Shell implementation. If None, creates empty FakeShell.
        completion: Optional Completion implementation.
                       If None, creates empty FakeCompletion.
        config_store: Optional ConfigStore implementation.
                          If None, creates FakeConfigStore with test config.
        script_writer: Optional ScriptWriter implementation.
                      If None, creates empty FakeScriptWriter.
        feedback: Optional UserFeedback implementation.
                    If None, creates FakeUserFeedback.
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

    from erk.core.config_store import FakeConfigStore
    from erk.core.planner.registry_fake import FakePlannerRegistry
    from erk_shared.extraction.claude_code_session_store import FakeClaudeCodeSessionStore
    from erk_shared.gateway.completion import FakeCompletion
    from erk_shared.gateway.feedback import FakeUserFeedback
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

    if graphite is None:
        graphite = FakeGraphite()

    # wt_stack needs git, repo_root, and graphite - resolved after those are set
    # repo_root is determined after repo is resolved, so wt_stack is created later

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

    if feedback is None:
        feedback = FakeUserFeedback()

    if plan_list_service is None:
        # If github and issues were provided, wire them up via RealPlanListService
        # so that tests get realistic behavior when testing plan list functionality
        plan_list_service = RealPlanListService(github, issues)

    if planner_registry is None:
        planner_registry = FakePlannerRegistry()

    if session_store is None:
        session_store = FakeClaudeCodeSessionStore()

    if prompt_executor is None:
        prompt_executor = FakePromptExecutor()

    if global_config is None:
        global_config = GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            github_planning=True,
        )

    if config_store is None:
        config_store = FakeConfigStore(config=global_config)

    if local_config is None:
        local_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)

    if repo is None:
        repo = NoRepoSentinel()

    # Resolve wt_stack now that we have git, graphite, and repo
    if wt_stack is None:
        repo_root = repo.root if not isinstance(repo, NoRepoSentinel) else (cwd or sentinel_path())
        wt_stack = WtStack(git, repo_root, graphite)

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
        wt_stack=wt_stack,
        shell=shell,
        claude_executor=claude_executor,
        completion=completion,
        time=time,
        config_store=config_store,
        script_writer=script_writer,
        feedback=feedback,
        plan_list_service=plan_list_service,
        planner_registry=planner_registry,
        session_store=session_store,
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
        doc["tool"] = tomlkit.table()  # type: ignore[index]

    # Ensure [tool.erk] section exists
    if "erk" not in doc["tool"]:  # type: ignore[operator]
        doc["tool"]["erk"] = tomlkit.table()  # type: ignore[index]

    # Set trunk_branch value
    doc["tool"]["erk"]["trunk_branch"] = trunk  # type: ignore[index]

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
        script: If True, use SuppressedFeedback to suppress diagnostic output
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

    # 2. Create global config store
    config_store = RealConfigStore()

    # 3. Load global config (no deps) - None if not exists (for init command)
    global_config: GlobalConfig | None
    if config_store.exists():
        global_config = config_store.load()
    else:
        # For init command only: config doesn't exist yet
        global_config = None

    # 4. Create integration classes (need git for repo discovery)
    # Create time first so it can be injected into other classes
    time: Time = RealTime()
    git: Git = RealGit()
    graphite: Graphite = RealGraphite()

    # 5. Discover repo (only needs cwd, erk_root, git)
    # If global_config is None, use placeholder path for repo discovery
    erk_root = global_config.erk_root if global_config else Path.home() / "worktrees"
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

    # 7. Create GitHub-related classes (need repo_info)
    github: GitHub = RealGitHub(time, repo_info)
    issues: GitHubIssues = RealGitHubIssues()
    plan_store: PlanStore = GitHubPlanStore(issues)
    plan_list_service: PlanListService = RealPlanListService(github, issues)

    # 8. Load local config (or defaults if no repo)
    if isinstance(repo, NoRepoSentinel):
        local_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
    else:
        # Ensure metadata directories exist (needed for worktrees)
        ensure_erk_metadata_dir(repo)
        # Load config from primary location (.erk/config.toml)
        # Legacy locations are detected by 'erk doctor' only
        local_config = load_config(repo.root)

    # 9. Choose feedback implementation based on mode
    feedback: UserFeedback
    if script:
        feedback = SuppressedFeedback()  # Suppress diagnostics
    else:
        feedback = InteractiveFeedback()  # Show all messages

    # 10. Apply dry-run wrappers if needed
    if dry_run:
        git = DryRunGit(git)
        graphite = DryRunGraphite(graphite)
        github = DryRunGitHub(github)
        issues = DryRunGitHubIssues(issues)

    # 11. Create WtStack (after dry-run wrapping so it uses wrapped git/graphite)
    repo_root = repo.root if not isinstance(repo, NoRepoSentinel) else cwd
    wt_stack = WtStack(git, repo_root, graphite)

    # 12. Create session store and prompt executor
    from erk_shared.extraction.claude_code_session_store import RealClaudeCodeSessionStore

    session_store: ClaudeCodeSessionStore = RealClaudeCodeSessionStore()
    prompt_executor: PromptExecutor = RealPromptExecutor()

    # 13. Create context with all values
    return ErkContext(
        git=git,
        github=github,
        github_admin=RealGitHubAdmin(),
        issues=issues,
        plan_store=plan_store,
        graphite=graphite,
        wt_stack=wt_stack,
        shell=RealShell(),
        claude_executor=RealClaudeExecutor(),
        completion=RealCompletion(),
        time=time,
        config_store=RealConfigStore(),
        script_writer=RealScriptWriter(),
        feedback=feedback,
        plan_list_service=plan_list_service,
        planner_registry=RealPlannerRegistry(),
        session_store=session_store,
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
