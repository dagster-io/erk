"""Application context with dependency injection.

This module provides factory functions for erk CLI context creation.
The unified ErkContext dataclass is defined in erk_shared.context and
re-exported here for backwards compatibility.
"""

from __future__ import annotations

import shutil
from collections.abc import MutableMapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click
import tomlkit

# Re-export types from erk_shared.context and erk.artifacts.paths
from erk.artifacts.paths import ErkPackageInfo as ErkPackageInfo
from erk.cli.config import load_config, load_local_config, merge_configs_with_local
from erk.core.anthropic_prompt_executor import AnthropicApiPromptExecutor
from erk.core.codex_prompt_executor import CodexCliPromptExecutor
from erk.core.completion import RealCompletion
from erk.core.fallback_prompt_executor import FallbackPromptExecutor
from erk.core.prompt_executor import ClaudeCliPromptExecutor
from erk.core.repo_discovery import discover_repo_or_sentinel, ensure_erk_metadata_dir
from erk.core.script_writer import RealScriptWriter
from erk.core.services.objective_list_service import RealObjectiveListService
from erk.core.services.plan_list_service import PlannedPRPlanListService
from erk.core.shell import RealShell

# Re-export ErkContext from erk_shared for isinstance() compatibility
# This ensures that both erk CLI and kit commands use the same class identity
from erk_shared.context.context import ErkContext as ErkContext
from erk_shared.context.types import GlobalConfig as GlobalConfig
from erk_shared.context.types import LoadedConfig as LoadedConfig
from erk_shared.context.types import NoRepoSentinel as NoRepoSentinel
from erk_shared.context.types import RepoContext as RepoContext
from erk_shared.core.objective_list_service import ObjectiveListService
from erk_shared.core.plan_list_service import PlanListService
from erk_shared.core.prompt_executor import PromptExecutor
from erk_shared.gateway.agent_docs.abc import AgentDocs
from erk_shared.gateway.agent_docs.real import RealAgentDocs
from erk_shared.gateway.agent_launcher.abc import AgentLauncher
from erk_shared.gateway.claude_installation.abc import ClaudeInstallation
from erk_shared.gateway.cmux.real import RealCmux
from erk_shared.gateway.codespace.real import RealCodespace
from erk_shared.gateway.codespace_registry.real import RealCodespaceRegistry
from erk_shared.gateway.console.abc import Console
from erk_shared.gateway.console.real import InteractiveConsole, ScriptConsole
from erk_shared.gateway.erk_installation.real import RealErkInstallation
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.dry_run import DryRunGit
from erk_shared.gateway.git.real import RealGit
from erk_shared.gateway.github.abc import LocalGitHub
from erk_shared.gateway.github.dry_run import DryRunLocalGitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.issues.real import RealGitHubIssues
from erk_shared.gateway.github.parsing import parse_git_remote_url
from erk_shared.gateway.github.real import RealLocalGitHub
from erk_shared.gateway.github.types import RepoInfo
from erk_shared.gateway.github_admin.real import RealGitHubAdmin
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.branch_ops.abc import GraphiteBranchOps
from erk_shared.gateway.graphite.branch_ops.dry_run import DryRunGraphiteBranchOps
from erk_shared.gateway.graphite.branch_ops.real import RealGraphiteBranchOps
from erk_shared.gateway.graphite.disabled import (
    GraphiteDisabled,
    GraphiteDisabledReason,
)
from erk_shared.gateway.graphite.dry_run import DryRunGraphite
from erk_shared.gateway.graphite.real import RealGraphite
from erk_shared.gateway.http.abc import HttpClient
from erk_shared.gateway.http.auth import fetch_github_token_or_none
from erk_shared.gateway.http.real import RealHttpClient
from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.real import RealTime
from erk_shared.output.output import user_output
from erk_shared.plan_store.backend import ManagedPrBackend
from erk_shared.plan_store.planned_pr import GitHubManagedPrBackend

if TYPE_CHECKING:
    pass


def create_prompt_executor(
    *,
    global_config: GlobalConfig | None,
    console: Console,
) -> PromptExecutor:
    """Select prompt executor based on global configuration.

    Returns CodexCliPromptExecutor when backend is "codex", otherwise
    ClaudeCliPromptExecutor (the default).

    Args:
        global_config: Global configuration, or None if not yet initialized.
        console: Console gateway for TTY detection.

    Returns:
        PromptExecutor implementation matching the configured backend.
    """
    if global_config is not None and global_config.interactive_agent.backend == "codex":
        return CodexCliPromptExecutor(console=console)
    return ClaudeCliPromptExecutor(console=console)


def select_prompt_executor(
    *,
    cli_executor: PromptExecutor,
    global_config: GlobalConfig | None,
) -> PromptExecutor:
    """Wrap cli_executor with FallbackPromptExecutor when API fast path is enabled."""
    if global_config is not None and global_config.anthropic_api_fast_path:
        return FallbackPromptExecutor(
            api_executor=AnthropicApiPromptExecutor(),
            cli_executor=cli_executor,
        )
    return cli_executor


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
        path_exists = git.worktree.path_exists(pyproject_path)
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
        >>> worktrees = ctx.git.worktree.list_worktrees(Path("/repo"))
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
    git: Git = RealGit(time)

    # Create Graphite based on config and availability
    graphite: Graphite
    graphite_branch_ops: GraphiteBranchOps | None = None
    if global_config is not None and global_config.use_graphite:
        # Config says use Graphite - check if gt is installed
        if shutil.which("gt") is None:
            graphite = GraphiteDisabled(GraphiteDisabledReason.NOT_INSTALLED)
        else:
            graphite = RealGraphite()
            graphite_branch_ops = RealGraphiteBranchOps()
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
            remote_url = git.remote.get_remote_url(repo.root, "origin")
            owner, name = parse_git_remote_url(remote_url)
            repo_info = RepoInfo(owner=owner, name=name)
        except ValueError:
            # No origin remote configured - repo_info stays None
            pass

    # 6b. Create HTTP client for GitHub API (needs token from gh auth)
    # No repo guard needed — HttpClient only requires a GitHub token
    http_client: HttpClient | None = None
    token = fetch_github_token_or_none()
    if token is not None:
        http_client = RealHttpClient(token=token, base_url="https://api.github.com")

    # 7. Load local config (or defaults if no repo)
    # Loaded early so plans_repo can be used for GitHubIssues
    if isinstance(repo, NoRepoSentinel):
        local_config = LoadedConfig.test()
    else:
        # Ensure metadata directories exist (needed for worktrees)
        ensure_erk_metadata_dir(repo)
        # Load config from primary location (.erk/config.toml)
        # Legacy locations are detected by 'erk doctor' only
        # Use main_repo_root so config is shared across all worktrees
        main_root = repo.main_repo_root or repo.root
        repo_config = load_config(main_root)
        # Load per-user local config (.erk/config.local.toml) and merge
        user_local_config = load_local_config(main_root)
        local_config = merge_configs_with_local(
            base_config=repo_config,
            local_config=user_local_config,
        )

    # 8. Create GitHub-related classes (need repo_info, local_config)
    # Create issues first, then compose into github
    # Use plans_repo for cross-repo plan management if configured
    issues: GitHubIssues = RealGitHubIssues(target_repo=local_config.github_repo, time=time)
    github: LocalGitHub = RealLocalGitHub(time, repo_info, issues=issues)

    plan_store: ManagedPrBackend = GitHubManagedPrBackend(github, issues, time=RealTime())
    plan_list_service: PlanListService = PlannedPRPlanListService(github, time=time)

    # Objectives use GitHub issues (not draft PRs)
    objective_list_service: ObjectiveListService = RealObjectiveListService(github, time=time)

    # 9. Apply dry-run wrappers if needed
    # Note: DryRunLocalGitHub composes DryRunGitHubIssues internally,
    # but we still wrap issues separately for ctx.issues backward compatibility
    # Note: DryRunLocalGitHub composes DryRunGitHubIssues internally for github.issues
    if dry_run:
        git = DryRunGit(git)
        graphite = DryRunGraphite(graphite)
        if graphite_branch_ops is not None:
            graphite_branch_ops = DryRunGraphiteBranchOps(graphite_branch_ops)
        github = DryRunLocalGitHub(github)

    # 10. Create prompt executor (optionally API-first via FallbackPromptExecutor)
    cli_executor = create_prompt_executor(
        global_config=global_config,
        console=console,
    )
    prompt_executor = select_prompt_executor(
        cli_executor=cli_executor,
        global_config=global_config,
    )

    # 11. Create claude installation and agent launcher
    from erk_shared.gateway.agent_docs.dry_run import DryRunAgentDocs
    from erk_shared.gateway.agent_launcher.real import RealAgentLauncher
    from erk_shared.gateway.claude_installation.real import RealClaudeInstallation

    real_claude_installation: ClaudeInstallation = RealClaudeInstallation()
    real_agent_launcher: AgentLauncher = RealAgentLauncher()
    real_agent_docs: AgentDocs = RealAgentDocs()
    if dry_run:
        real_agent_docs = DryRunAgentDocs(real_agent_docs)

    # 12. Create package info
    package_info = ErkPackageInfo.from_project_dir(cwd)

    # 13. Create health check runner
    # Inline import: importing erk.core.health_checks.runner triggers the
    # health_checks package __init__.py which imports individual check modules
    # that depend on erk.core.context — causing a circular import at module level.
    from erk.core.health_checks.runner import RealHealthCheckRunner

    health_check_runner = RealHealthCheckRunner()

    # 14. Create context with all values
    return ErkContext(
        git=git,
        github=github,
        github_admin=RealGitHubAdmin(),
        plan_store=plan_store,
        graphite=graphite,
        graphite_branch_ops=graphite_branch_ops,
        console=console,
        shell=RealShell(),
        codespace=RealCodespace(),
        cmux=RealCmux(),
        agent_launcher=real_agent_launcher,
        agent_docs=real_agent_docs,
        completion=RealCompletion(),
        time=time,
        erk_installation=erk_installation,
        script_writer=RealScriptWriter(),
        plan_list_service=plan_list_service,
        objective_list_service=objective_list_service,
        codespace_registry=RealCodespaceRegistry.from_config_path(
            erk_installation.get_codespaces_config_path()
        ),
        claude_installation=real_claude_installation,
        prompt_executor=prompt_executor,
        cwd=cwd,
        global_config=global_config,
        local_config=local_config,
        repo=repo,
        repo_info=repo_info,
        package_info=package_info,
        health_check_runner=health_check_runner,
        http_client=http_client,
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
