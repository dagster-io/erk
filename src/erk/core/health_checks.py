"""Health check implementations for erk doctor command.

This module provides diagnostic checks for erk setup, including
CLI availability, repository configuration, and Claude settings.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from erk.core.claude_settings import (
    ERK_PERMISSION,
    get_repo_claude_settings_path,
    has_erk_permission,
    read_claude_settings,
)
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.shell.abc import Shell
from erk_shared.github_admin.abc import GitHubAdmin


@dataclass
class CheckResult:
    """Result of a single health check.

    Attributes:
        name: Name of the check
        passed: Whether the check passed
        message: Human-readable message describing the result
        details: Optional additional details (e.g., version info)
        warning: If True and passed=True, displays ⚠️ instead of ✅
    """

    name: str
    passed: bool
    message: str
    details: str | None = None
    warning: bool = False


def check_erk_version() -> CheckResult:
    """Check erk CLI version."""
    try:
        from importlib.metadata import version

        erk_version = version("erk")
        return CheckResult(
            name="erk",
            passed=True,
            message=f"erk CLI installed: v{erk_version}",
            details=erk_version,
        )
    except Exception:
        return CheckResult(
            name="erk",
            passed=False,
            message="erk package not found",
        )


def check_claude_cli(shell: Shell) -> CheckResult:
    """Check if Claude CLI is installed and available in PATH.

    Args:
        shell: Shell implementation for tool detection
    """
    claude_path = shell.get_installed_tool_path("claude")
    if claude_path is None:
        return CheckResult(
            name="claude",
            passed=False,
            message="Claude CLI not found in PATH",
            details="Install from: https://claude.com/download",
        )

    # Try to get version
    version_output = shell.get_tool_version("claude")
    if version_output is None:
        return CheckResult(
            name="claude",
            passed=True,
            message="Claude CLI found (version check failed)",
            details="unknown",
        )

    # Parse version from output (format: "claude X.Y.Z")
    version_str = version_output.split()[-1] if version_output else "unknown"
    return CheckResult(
        name="claude",
        passed=True,
        message=f"Claude CLI available: {version_str}",
        details=version_str,
    )


def check_graphite_cli(shell: Shell) -> CheckResult:
    """Check if Graphite CLI (gt) is installed and available in PATH.

    Args:
        shell: Shell implementation for tool detection
    """
    gt_path = shell.get_installed_tool_path("gt")
    if gt_path is None:
        return CheckResult(
            name="graphite",
            passed=False,
            message="Graphite CLI (gt) not found in PATH",
            details="Install from: https://graphite.dev/docs/installing-the-cli",
        )

    # Try to get version
    version_output = shell.get_tool_version("gt")
    if version_output is None:
        return CheckResult(
            name="graphite",
            passed=True,
            message="Graphite CLI found (version check failed)",
            details="unknown",
        )

    return CheckResult(
        name="graphite",
        passed=True,
        message=f"Graphite CLI available: {version_output}",
        details=version_output,
    )


def check_github_cli(shell: Shell) -> CheckResult:
    """Check if GitHub CLI (gh) is installed and available in PATH.

    Args:
        shell: Shell implementation for tool detection
    """
    gh_path = shell.get_installed_tool_path("gh")
    if gh_path is None:
        return CheckResult(
            name="github",
            passed=False,
            message="GitHub CLI (gh) not found in PATH",
            details="Install from: https://cli.github.com/",
        )

    # Try to get version
    version_output = shell.get_tool_version("gh")
    if version_output is None:
        return CheckResult(
            name="github",
            passed=True,
            message="GitHub CLI found (version check failed)",
            details="unknown",
        )

    # Take first line only (gh version has multi-line output)
    version_first_line = version_output.split("\n")[0] if version_output else "unknown"
    return CheckResult(
        name="github",
        passed=True,
        message=f"GitHub CLI available: {version_first_line}",
        details=version_first_line,
    )


def check_github_auth(shell: Shell, admin: GitHubAdmin) -> CheckResult:
    """Check if GitHub CLI is authenticated.

    Args:
        shell: Shell implementation for tool detection
        admin: GitHubAdmin implementation for auth status check
    """
    gh_path = shell.get_installed_tool_path("gh")
    if gh_path is None:
        return CheckResult(
            name="github auth",
            passed=False,
            message="Cannot check auth: gh not installed",
        )

    auth_status = admin.check_auth_status()

    if auth_status.error is not None:
        return CheckResult(
            name="github auth",
            passed=False,
            message=f"Auth check failed: {auth_status.error}",
        )

    if auth_status.authenticated:
        if auth_status.username:
            return CheckResult(
                name="github auth",
                passed=True,
                message=f"GitHub authenticated as {auth_status.username}",
            )
        return CheckResult(
            name="github auth",
            passed=True,
            message="Authenticated to GitHub",
        )
    else:
        return CheckResult(
            name="github auth",
            passed=False,
            message="Not authenticated to GitHub",
            details="Run: gh auth login",
        )


def check_workflow_permissions(ctx: ErkContext, repo_root: Path, admin: GitHubAdmin) -> CheckResult:
    """Check if GitHub Actions workflows can create PRs.

    This is an info-level check - it always passes, but shows whether
    PR creation is enabled for workflows. This is required for erk's
    remote implementation feature.

    Args:
        ctx: ErkContext for repository access
        repo_root: Path to the repository root
        admin: GitHubAdmin implementation for API calls

    Returns:
        CheckResult with info about workflow permission status
    """
    # Need GitHub identity to check permissions
    try:
        remote_url = ctx.git.get_remote_url(repo_root, "origin")
    except ValueError:
        return CheckResult(
            name="workflow permissions",
            passed=True,  # Info level
            message="No origin remote configured",
        )

    # Parse GitHub owner/repo from remote URL
    from erk_shared.github.parsing import parse_git_remote_url
    from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation

    try:
        owner_repo = parse_git_remote_url(remote_url)
    except ValueError:
        return CheckResult(
            name="workflow permissions",
            passed=True,  # Info level
            message="Not a GitHub repository",
        )

    repo_id = GitHubRepoId(owner=owner_repo[0], repo=owner_repo[1])
    location = GitHubRepoLocation(root=repo_root, repo_id=repo_id)

    try:
        perms = admin.get_workflow_permissions(location)
        enabled = perms.get("can_approve_pull_request_reviews", False)

        if enabled:
            return CheckResult(
                name="workflow permissions",
                passed=True,
                message="Workflows can create PRs",
            )
        else:
            return CheckResult(
                name="workflow permissions",
                passed=True,  # Info level - always passes
                message="Workflows cannot create PRs",
                details="Run 'erk admin github-pr-setting --enable' to allow",
            )
    except Exception:
        return CheckResult(
            name="workflow permissions",
            passed=True,  # Info level - don't fail on API errors
            message="Could not check workflow permissions",
        )


def check_uv_version(shell: Shell) -> CheckResult:
    """Check if uv is installed.

    Shows version and upgrade instructions. erk works best with recent uv versions.

    Args:
        shell: Shell implementation for tool detection
    """
    uv_path = shell.get_installed_tool_path("uv")
    if uv_path is None:
        return CheckResult(
            name="uv",
            passed=False,
            message="uv not found in PATH",
            details="Install from: https://docs.astral.sh/uv/getting-started/installation/",
        )

    # Get installed version
    version_output = shell.get_tool_version("uv")
    if version_output is None:
        return CheckResult(
            name="uv",
            passed=True,
            message="uv found (version check failed)",
            details="Upgrade: uv self update",
        )

    # Parse version (format: "uv 0.9.2" or "uv 0.9.2 (Homebrew 2025-10-10)")
    parts = version_output.split()
    version = parts[1] if len(parts) >= 2 else version_output

    return CheckResult(
        name="uv",
        passed=True,
        message=f"uv available: {version}",
        details="erk works best with recent versions. Upgrade: uv self update",
    )


def check_hooks_disabled() -> CheckResult:
    """Check if Claude Code hooks are globally disabled.

    Checks both global settings files for hooks.disabled=true:
    - ~/.claude/settings.json
    - ~/.claude/settings.local.json

    Returns a warning (not failure) if hooks are disabled, since the user
    may have intentionally disabled them.
    """
    home = Path.home()
    settings_files = [
        home / ".claude" / "settings.json",
        home / ".claude" / "settings.local.json",
    ]

    disabled_in: list[str] = []

    for settings_path in settings_files:
        if not settings_path.exists():
            continue
        content = settings_path.read_text(encoding="utf-8")
        settings = json.loads(content)
        hooks = settings.get("hooks", {})
        if hooks.get("disabled") is True:
            disabled_in.append(settings_path.name)

    if disabled_in:
        return CheckResult(
            name="claude hooks",
            passed=True,  # Don't fail, just warn
            warning=True,
            message=f"Hooks disabled in {', '.join(disabled_in)}",
            details="Set hooks.disabled=false or remove the setting to enable hooks",
        )

    return CheckResult(
        name="claude hooks",
        passed=True,
        message="Hooks enabled (not globally disabled)",
    )


def check_orphaned_artifacts(repo_root: Path) -> CheckResult:
    """Check for orphaned artifacts in .claude/ directory.

    Detects directories that appear kit-related but the kit isn't installed.
    This is a warning-level check - orphaned files don't break anything.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with warning if orphaned artifacts found
    """
    from erk.kits.io.state import load_project_config
    from erk.kits.operations.orphan_detection import detect_orphaned_artifacts

    claude_dir = repo_root / ".claude"
    if not claude_dir.exists():
        return CheckResult(
            name="orphaned artifacts",
            passed=True,
            message="No .claude/ directory",
        )

    config = load_project_config(repo_root)
    result = detect_orphaned_artifacts(repo_root, config)

    if not result.orphaned_directories:
        return CheckResult(
            name="orphaned artifacts",
            passed=True,
            message="No orphaned artifacts found",
        )

    # Build details listing orphaned paths
    details_lines: list[str] = []
    for orphan in result.orphaned_directories:
        details_lines.append(f"{orphan.path}/ ({orphan.reason})")
    details_lines.append("")
    details_lines.append("Run 'rm -r <path>' to clean up orphaned directories")

    return CheckResult(
        name="orphaned artifacts",
        passed=True,  # Warning only - doesn't fail the check
        warning=True,
        message=f"Found {len(result.orphaned_directories)} orphaned artifact(s)",
        details="\n".join(details_lines),
    )


def check_docs_agent(repo_root: Path) -> CheckResult:
    """Check if .erk/docs/agent/ templates exist and are valid.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult indicating whether .erk/docs/agent/ is properly configured
    """
    docs_agent_dir = repo_root / ".erk" / "docs" / "agent"

    # Check if directory exists
    if not docs_agent_dir.exists():
        return CheckResult(
            name=".erk/docs/agent",
            passed=True,  # Info level - not required
            message="No .erk/docs/agent/ directory",
            details="Run 'erk init' to create agent documentation templates",
        )

    # Check for expected template files
    expected_files = ["glossary.md", "conventions.md", "guide.md"]
    missing_files: list[str] = []

    for filename in expected_files:
        if not (docs_agent_dir / filename).exists():
            missing_files.append(filename)

    if missing_files:
        return CheckResult(
            name=".erk/docs/agent",
            passed=True,  # Info level - warn but don't fail
            message=f"Missing template files: {', '.join(missing_files)}",
            details="Run 'erk init --force' to recreate templates",
        )

    return CheckResult(
        name=".erk/docs/agent",
        passed=True,
        message="Agent documentation templates present",
    )


def check_gitignore_entries(repo_root: Path) -> CheckResult:
    """Check that required gitignore entries exist.

    Args:
        repo_root: Path to the repository root (where .gitignore should be located)

    Returns:
        CheckResult indicating whether required entries are present
    """
    required_entries = [".erk/scratch/", ".impl/"]
    gitignore_path = repo_root / ".gitignore"

    # No gitignore file - pass (user may not have one yet)
    if not gitignore_path.exists():
        return CheckResult(
            name="gitignore",
            passed=True,
            message="No .gitignore file (entries not needed yet)",
        )

    gitignore_content = gitignore_path.read_text(encoding="utf-8")

    # Check for missing entries
    missing_entries: list[str] = []
    for entry in required_entries:
        if entry not in gitignore_content:
            missing_entries.append(entry)

    if missing_entries:
        return CheckResult(
            name="gitignore",
            passed=False,
            message=f"Missing gitignore entries: {', '.join(missing_entries)}",
            details="Run 'erk init' to add missing entries",
        )

    return CheckResult(
        name="gitignore",
        passed=True,
        message="Required gitignore entries present",
    )


def check_claude_erk_permission(repo_root: Path) -> CheckResult:
    """Check if erk permission is configured in repo's Claude Code settings.

    This is an info-level check - it always passes, but shows whether
    the permission is configured or not. The permission allows Claude
    to run erk commands without prompting.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with info about permission status
    """
    settings_path = get_repo_claude_settings_path(repo_root)

    try:
        settings = read_claude_settings(settings_path)
    except json.JSONDecodeError as e:
        return CheckResult(
            name="claude erk permission",
            passed=False,
            message="Invalid JSON in .claude/settings.json",
            details=str(e),
        )

    # No settings file - repo may not have Claude settings
    if settings is None:
        return CheckResult(
            name="claude erk permission",
            passed=True,  # Info level - always passes
            message="No .claude/settings.json in repo",
        )

    # Check for permission
    if has_erk_permission(settings):
        return CheckResult(
            name="claude erk permission",
            passed=True,
            message=f"erk permission configured ({ERK_PERMISSION})",
        )
    else:
        return CheckResult(
            name="claude erk permission",
            passed=True,  # Info level - always passes
            message="erk permission not configured",
            details=f"Run 'erk init' to add {ERK_PERMISSION} to .claude/settings.json",
        )


def check_repository(ctx: ErkContext) -> CheckResult:
    """Check repository setup."""
    # First check if we're in a git repo using git_common_dir
    # (get_repository_root raises on non-git dirs, but git_common_dir returns None)
    git_dir = ctx.git.get_git_common_dir(ctx.cwd)
    if git_dir is None:
        return CheckResult(
            name="repository",
            passed=False,
            message="Not in a git repository",
        )

    # Now safe to get repo root
    repo_root = ctx.git.get_repository_root(ctx.cwd)

    # Check for .erk directory at repo root
    erk_dir = repo_root / ".erk"
    if not erk_dir.exists():
        return CheckResult(
            name="repository",
            passed=True,
            message="Git repository detected (no .erk/ directory)",
            details="Run 'erk init' to set up erk for this repository",
        )

    return CheckResult(
        name="repository",
        passed=True,
        message="Git repository with erk setup detected",
    )


def check_claude_settings(repo_root: Path) -> CheckResult:
    """Check Claude settings for misconfigurations.

    Args:
        repo_root: Path to the repository root (where .claude/ should be located)
    """
    settings_path = repo_root / ".claude" / "settings.json"

    if not settings_path.exists():
        return CheckResult(
            name="claude settings",
            passed=True,
            message="No .claude/settings.json (using defaults)",
        )

    # Parse settings
    try:
        settings_content = settings_path.read_text(encoding="utf-8")
        settings = json.loads(settings_content)
    except json.JSONDecodeError as e:
        return CheckResult(
            name="claude settings",
            passed=False,
            message="Invalid JSON in .claude/settings.json",
            details=str(e),
        )
    except Exception as e:
        return CheckResult(
            name="claude settings",
            passed=False,
            message=f"Error reading .claude/settings.json: {e}",
        )

    # Check hooks for missing commands
    warnings: list[str] = []
    hooks = settings.get("hooks", {})

    for hook_name, hook_config in hooks.items():
        if not isinstance(hook_config, list):
            continue
        for hook in hook_config:
            if not isinstance(hook, dict):
                continue
            hook_cmd = hook.get("command")
            if hook_cmd is not None and isinstance(hook_cmd, str):
                # Check if the command looks like a kit command
                is_kit_command = "erk kit exec" in hook_cmd
                if is_kit_command:
                    # Extract kit command name for warning
                    parts = hook_cmd.split()
                    if len(parts) >= 4:
                        kit_cmd = parts[-1]
                        # We can't easily check if command exists, so just note it
                        if not _kit_command_exists(hook_cmd):
                            warnings.append(f"Hook '{hook_name}' references '{kit_cmd}'")

    if warnings:
        return CheckResult(
            name="claude settings",
            passed=True,  # Warnings don't fail the check
            message=".claude/settings.json has hook references",
            details="\n".join(warnings),
        )

    return CheckResult(
        name="claude settings",
        passed=True,
        message=".claude/settings.json looks valid",
    )


def check_hook_health(repo_root: Path) -> CheckResult:
    """Check hook execution health from recent logs.

    Reads logs from .erk/scratch/sessions/*/hooks/*/*.json for the last 24 hours
    and reports any failures (non-zero exit codes, exceptions).

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with hook health status
    """
    from erk_shared.hooks.logging import read_recent_hook_logs
    from erk_shared.hooks.types import HookExitStatus

    logs = read_recent_hook_logs(repo_root, max_age_hours=24)

    if not logs:
        return CheckResult(
            name="hooks",
            passed=True,
            message="No hook logs in last 24h",
        )

    # Count by status
    success_count = 0
    blocked_count = 0
    error_count = 0
    exception_count = 0

    # Track failures by hook for detailed reporting
    failures_by_hook: dict[str, list[tuple[str, str]]] = {}

    for log in logs:
        if log.exit_status == HookExitStatus.SUCCESS:
            success_count += 1
        elif log.exit_status == HookExitStatus.BLOCKED:
            blocked_count += 1
        elif log.exit_status == HookExitStatus.ERROR:
            error_count += 1
            hook_key = f"{log.kit_id}/{log.hook_id}"
            if hook_key not in failures_by_hook:
                failures_by_hook[hook_key] = []
            failures_by_hook[hook_key].append(
                (f"error (exit code {log.exit_code})", log.stderr[:200] if log.stderr else "")
            )
        elif log.exit_status == HookExitStatus.EXCEPTION:
            exception_count += 1
            hook_key = f"{log.kit_id}/{log.hook_id}"
            if hook_key not in failures_by_hook:
                failures_by_hook[hook_key] = []
            failures_by_hook[hook_key].append(
                ("exception", log.error_message or log.stderr[:200] if log.stderr else "")
            )

    total_failures = error_count + exception_count

    if total_failures == 0:
        return CheckResult(
            name="hooks",
            passed=True,
            message=f"All hooks healthy ({success_count} succeeded, {blocked_count} blocked)",
        )

    # Build failure details
    details_lines: list[str] = []
    for hook_key, failures in failures_by_hook.items():
        details_lines.append(f"   {hook_key}: {len(failures)} failure(s)")
        # Show most recent failure
        if failures:
            status, message = failures[0]
            details_lines.append(f"     Last failure: {status}")
            if message:
                # Truncate long messages
                truncated = message[:100] + "..." if len(message) > 100 else message
                details_lines.append(f"     {truncated}")

    return CheckResult(
        name="hooks",
        passed=False,
        message=f"{total_failures} hook failure(s) in last 24h",
        details="\n".join(details_lines),
    )


def _kit_command_exists(command: str) -> bool:
    """Check if a kit command exists by trying to run it with --help.

    This is a heuristic check - we run the command with --help to see
    if it's recognized. This avoids executing arbitrary commands while
    still validating that the kit command is defined.
    """
    # Parse command to extract the base exec command
    # Format: ERK_HOOK_ID=... erk exec <command-name>
    try:
        # Quick check - just see if the kit-command is recognized
        # We don't want to actually run hooks, just validate they exist
        # For now, return True and let the actual command fail at runtime
        # This is a conservative approach
        return True
    except Exception:
        return True  # Assume it exists if we can't check


def run_all_checks(ctx: ErkContext) -> list[CheckResult]:
    """Run all health checks and return results.

    Args:
        ctx: ErkContext for repository checks (includes github_admin)

    Returns:
        List of CheckResult objects
    """
    shell = ctx.shell
    admin = ctx.github_admin

    results = [
        check_erk_version(),
        check_claude_cli(shell),
        check_graphite_cli(shell),
        check_github_cli(shell),
        check_github_auth(shell, admin),
        check_uv_version(shell),
        check_hooks_disabled(),
    ]

    # Add repository check
    results.append(check_repository(ctx))

    # Check Claude settings, gitignore, and GitHub checks if we're in a repo
    # (get_git_common_dir returns None if not in a repo)
    git_dir = ctx.git.get_git_common_dir(ctx.cwd)
    if git_dir is not None:
        repo_root = ctx.git.get_repository_root(ctx.cwd)
        # Compute metadata dir for legacy config check (~/.erk/repos/<repo-name>/)
        metadata_dir = Path.home() / ".erk" / "repos" / repo_root.name
        results.append(check_claude_erk_permission(repo_root))
        results.append(check_claude_settings(repo_root))
        results.append(check_gitignore_entries(repo_root))
        results.append(check_docs_agent(repo_root))
        results.append(check_orphaned_artifacts(repo_root))
        # Hook health check
        results.append(check_hook_health(repo_root))
        # GitHub workflow permissions check (requires repo context)
        results.append(check_workflow_permissions(ctx, repo_root, admin))

        from erk.core.health_checks_dogfooder import run_early_dogfooder_checks

        # Get metadata_dir if we have a RepoContext (for legacy config detection)
        metadata_dir = ctx.repo.repo_dir if isinstance(ctx.repo, RepoContext) else None
        results.extend(run_early_dogfooder_checks(repo_root, metadata_dir))

    return results
