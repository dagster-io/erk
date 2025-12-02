"""Application context with dependency injection."""

from dataclasses import dataclass
from pathlib import Path

import click
import tomlkit
from erk_shared.git.abc import Git
from erk_shared.git.dry_run import DryRunGit
from erk_shared.git.real import RealGit
from erk_shared.github.abc import GitHub
from erk_shared.github.dry_run import DryRunGitHub
from erk_shared.github.issue_link_branches import IssueLinkBranches
from erk_shared.github.issue_link_branches_dry_run import DryRunIssueLinkBranches
from erk_shared.github.issue_link_branches_real import RealIssueLinkBranches
from erk_shared.github.issues import DryRunGitHubIssues, GitHubIssues, RealGitHubIssues
from erk_shared.github.real import RealGitHub
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.dry_run import DryRunGraphite
from erk_shared.integrations.graphite.real import RealGraphite
from erk_shared.integrations.time.abc import Time
from erk_shared.integrations.time.real import RealTime
from erk_shared.output.output import user_output
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.store import PlanStore

from erk.cli.config import LoadedConfig, load_config
from erk.core.claude_executor import ClaudeExecutor, RealClaudeExecutor
from erk.core.completion import Completion, RealCompletion
from erk.core.config_store import (
    ConfigStore,
    GlobalConfig,
    RealConfigStore,
)
from erk.core.planner.registry_abc import PlannerRegistry
from erk.core.planner.registry_real import RealPlannerRegistry
from erk.core.repo_discovery import (
    NoRepoSentinel,
    RepoContext,
    discover_repo_or_sentinel,
    ensure_erk_metadata_dir,
)
from erk.core.script_writer import RealScriptWriter, ScriptWriter
from erk.core.services.plan_list_service import PlanListService
from erk.core.shell import RealShell, Shell
from erk.core.user_feedback import InteractiveFeedback, SuppressedFeedback, UserFeedback


@dataclass(frozen=True)
class ErkContext:
    """Immutable context holding all dependencies for erk operations.

    Created at CLI entry point and threaded through the application.
    Frozen to prevent accidental modification at runtime.

    Note: global_config may be None only during init command before config is created.
    All other commands should have a valid GlobalConfig.
    """

    git: Git
    github: GitHub
    issues: GitHubIssues
    issue_link_branches: IssueLinkBranches
    plan_store: PlanStore
    graphite: Graphite
    shell: Shell
    claude_executor: ClaudeExecutor
    completion: Completion
    time: Time
    config_store: ConfigStore
    script_writer: ScriptWriter
    feedback: UserFeedback
    plan_list_service: PlanListService
    planner_registry: PlannerRegistry
    cwd: Path  # Current working directory at CLI invocation
    global_config: GlobalConfig | None
    local_config: LoadedConfig
    repo: RepoContext | NoRepoSentinel
    dry_run: bool

    @property
    def trunk_branch(self) -> str | None:
        """Get the trunk branch name from git detection.

        Returns None if not in a repository, otherwise uses git to detect trunk.
        """
        if isinstance(self.repo, NoRepoSentinel):
            return None
        return self.git.get_trunk_branch(self.repo.root)

    @staticmethod
    def minimal(git: Git, cwd: Path, dry_run: bool = False) -> "ErkContext":
        """Create minimal context with only git configured, rest are test defaults.

        Useful for simple tests that only need git operations. Other integration
        classes are initialized with their standard test defaults (fake implementations).

        Args:
            git: The Git implementation (usually FakeGit with test configuration)
            cwd: Current working directory path for the context
            dry_run: Whether to enable dry-run mode (default False)

        Returns:
            ErkContext with git configured and other dependencies using test defaults

        Example:
            Before (7 lines):
            >>> from erk_shared.git.fake import FakeGit
            >>> from erk_shared.github.fake import FakeGitHub
            >>> from erk_shared.integrations.graphite.fake import FakeGraphite
            >>> from tests.fakes.shell import FakeShell
            >>> ctx = ErkContext(
            ...     git=git,
            ...     github=FakeGitHub(),
            ...     graphite=FakeGraphite(),
            ...     shell=FakeShell(),
            ...     cwd=cwd,
            ...     global_config=None,
            ...     local_config=LoadedConfig(
            ...         env={}, post_create_commands=[], post_create_shell=None
            ...     ),
            ...     repo=NoRepoSentinel(),
            ...     dry_run=False,
            ...     trunk_branch=None,
            ... )

            After (1 line):
            >>> ctx = ErkContext.minimal(git, cwd)

        Note:
            For more complex test setup with custom configs or multiple integration classes,
            use ErkContext.for_test() instead.
        """
        from erk_shared.github.fake import FakeGitHub
        from erk_shared.github.issues import FakeGitHubIssues
        from erk_shared.integrations.graphite.fake import FakeGraphite
        from erk_shared.integrations.time.fake import FakeTime
        from erk_shared.plan_store.fake import FakePlanStore
        from tests.fakes.claude_executor import FakeClaudeExecutor
        from tests.fakes.completion import FakeCompletion
        from tests.fakes.issue_link_branches import FakeIssueLinkBranches
        from tests.fakes.script_writer import FakeScriptWriter
        from tests.fakes.shell import FakeShell
        from tests.fakes.user_feedback import FakeUserFeedback

        from erk.core.config_store import FakeConfigStore
        from erk.core.planner.registry_fake import FakePlannerRegistry

        fake_github = FakeGitHub()
        fake_issues = FakeGitHubIssues()
        fake_issue_link_branches = FakeIssueLinkBranches()
        return ErkContext(
            git=git,
            github=fake_github,
            issues=fake_issues,
            issue_link_branches=fake_issue_link_branches,
            plan_store=FakePlanStore(),
            graphite=FakeGraphite(),
            shell=FakeShell(),
            claude_executor=FakeClaudeExecutor(),
            completion=FakeCompletion(),
            time=FakeTime(),
            config_store=FakeConfigStore(config=None),
            script_writer=FakeScriptWriter(),
            feedback=FakeUserFeedback(),
            plan_list_service=PlanListService(fake_github, fake_issues),
            planner_registry=FakePlannerRegistry(),
            cwd=cwd,
            global_config=None,
            local_config=LoadedConfig(env={}, post_create_commands=[], post_create_shell=None),
            repo=NoRepoSentinel(),
            dry_run=dry_run,
        )

    @staticmethod
    def for_test(
        git: Git | None = None,
        github: GitHub | None = None,
        issues: GitHubIssues | None = None,
        issue_link_branches: IssueLinkBranches | None = None,
        plan_store: PlanStore | None = None,
        graphite: Graphite | None = None,
        shell: Shell | None = None,
        claude_executor: ClaudeExecutor | None = None,
        completion: Completion | None = None,
        time: Time | None = None,
        config_store: ConfigStore | None = None,
        script_writer: ScriptWriter | None = None,
        feedback: UserFeedback | None = None,
        plan_list_service: PlanListService | None = None,
        planner_registry: PlannerRegistry | None = None,
        cwd: Path | None = None,
        global_config: GlobalConfig | None = None,
        local_config: LoadedConfig | None = None,
        repo: RepoContext | NoRepoSentinel | None = None,
        dry_run: bool = False,
    ) -> "ErkContext":
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
            cwd: Optional current working directory. If None, uses Path("/test/default/cwd").
            global_config: Optional GlobalConfig. If None, uses test defaults.
            local_config: Optional LoadedConfig. If None, uses empty defaults.
            repo: Optional RepoContext or NoRepoSentinel. If None, uses NoRepoSentinel().
            dry_run: Whether to enable dry-run mode (default False).

        Returns:
            ErkContext configured with provided values and test defaults

        Example:
            Simple case (use .minimal() instead):
            >>> git = FakeGit(default_branches={Path("/repo"): "main"})
            >>> ctx = ErkContext.for_test(git=git)

            Complex case with multiple integration classes:
            >>> git = FakeGit(default_branches={Path("/repo"): "main"})
            >>> github = FakeGitHub(prs={123: PR(...)})
            >>> graphite = FakeGraphite(stack_info={"feature": StackInfo(...)})
            >>> ctx = ErkContext.for_test(
            ...     git=git,
            ...     github=github,
            ...     graphite=graphite,
            ... )

        Note:
            For simple cases that only need git, use ErkContext.minimal()
            which is more concise.
        """
        from erk_shared.git.fake import FakeGit
        from erk_shared.github.fake import FakeGitHub
        from erk_shared.github.issues import FakeGitHubIssues
        from erk_shared.integrations.graphite.fake import FakeGraphite
        from erk_shared.integrations.time.fake import FakeTime
        from erk_shared.plan_store.fake import FakePlanStore
        from tests.fakes.claude_executor import FakeClaudeExecutor
        from tests.fakes.completion import FakeCompletion
        from tests.fakes.issue_link_branches import FakeIssueLinkBranches
        from tests.fakes.script_writer import FakeScriptWriter
        from tests.fakes.shell import FakeShell
        from tests.fakes.user_feedback import FakeUserFeedback
        from tests.test_utils.paths import sentinel_path

        from erk.core.config_store import FakeConfigStore
        from erk.core.planner.registry_fake import FakePlannerRegistry

        if git is None:
            git = FakeGit()

        if github is None:
            github = FakeGitHub()

        if issues is None:
            issues = FakeGitHubIssues()

        if issue_link_branches is None:
            issue_link_branches = FakeIssueLinkBranches()

        if plan_store is None:
            plan_store = FakePlanStore()

        if graphite is None:
            graphite = FakeGraphite()

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
            plan_list_service = PlanListService(github, issues)

        if planner_registry is None:
            planner_registry = FakePlannerRegistry()

        if global_config is None:
            global_config = GlobalConfig(
                erk_root=Path("/test/erks"),
                use_graphite=False,
                shell_setup_complete=False,
                show_pr_info=True,
            )

        if config_store is None:
            config_store = FakeConfigStore(config=global_config)

        if local_config is None:
            local_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)

        if repo is None:
            repo = NoRepoSentinel()

        # Apply dry-run wrappers if needed (matching production behavior)
        if dry_run:
            git = DryRunGit(git)
            graphite = DryRunGraphite(graphite)
            github = DryRunGitHub(github)
            issues = DryRunGitHubIssues(issues)
            issue_link_branches = DryRunIssueLinkBranches(issue_link_branches)

        return ErkContext(
            git=git,
            github=github,
            issues=issues,
            issue_link_branches=issue_link_branches,
            plan_store=plan_store,
            graphite=graphite,
            shell=shell,
            claude_executor=claude_executor,
            completion=completion,
            time=time,
            config_store=config_store,
            script_writer=script_writer,
            feedback=feedback,
            plan_list_service=plan_list_service,
            planner_registry=planner_registry,
            cwd=cwd or sentinel_path(),
            global_config=global_config,
            local_config=local_config,
            repo=repo,
            dry_run=dry_run,
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


def create_context(*, dry_run: bool, script: bool = False) -> ErkContext:
    """Create production context with real implementations.

    Called at CLI entry point to create the context for the entire
    command execution.

    Args:
        dry_run: If True, wrap all dependencies with dry-run wrappers that
                 print intended actions without executing them
        script: If True, use SuppressedFeedback to suppress diagnostic output
                for shell integration mode (default False)

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
    github: GitHub = RealGitHub(time)
    issues: GitHubIssues = RealGitHubIssues()
    issue_link_branches: IssueLinkBranches = RealIssueLinkBranches()
    plan_store: PlanStore = GitHubPlanStore(issues)
    plan_list_service: PlanListService = PlanListService(github, issues)

    # 5. Discover repo (only needs cwd, erk_root, git)
    # If global_config is None, use placeholder path for repo discovery
    erk_root = global_config.erk_root if global_config else Path.home() / "worktrees"
    repo = discover_repo_or_sentinel(cwd, erk_root, git)

    # 6. Load local config (or defaults if no repo)
    if isinstance(repo, NoRepoSentinel):
        local_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
    else:
        repo_dir = ensure_erk_metadata_dir(repo)
        local_config = load_config(repo_dir)

    # 7. Choose feedback implementation based on mode
    feedback: UserFeedback
    if script:
        feedback = SuppressedFeedback()  # Suppress diagnostics
    else:
        feedback = InteractiveFeedback()  # Show all messages

    # 8. Apply dry-run wrappers if needed
    if dry_run:
        git = DryRunGit(git)
        graphite = DryRunGraphite(graphite)
        github = DryRunGitHub(github)
        issues = DryRunGitHubIssues(issues)
        issue_link_branches = DryRunIssueLinkBranches(issue_link_branches)

    # 9. Create context with all values
    return ErkContext(
        git=git,
        github=github,
        issues=issues,
        issue_link_branches=issue_link_branches,
        plan_store=plan_store,
        graphite=graphite,
        shell=RealShell(),
        claude_executor=RealClaudeExecutor(),
        completion=RealCompletion(),
        time=time,
        config_store=RealConfigStore(),
        script_writer=RealScriptWriter(),
        feedback=feedback,
        plan_list_service=plan_list_service,
        planner_registry=RealPlannerRegistry(),
        cwd=cwd,
        global_config=global_config,
        local_config=local_config,
        repo=repo,
        dry_run=dry_run,
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
    return create_context(dry_run=existing_ctx.dry_run)
