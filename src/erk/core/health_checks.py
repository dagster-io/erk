"""Health check implementations for erk doctor command.

This module provides diagnostic checks for erk setup, including
CLI availability, repository configuration, and Claude settings.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from erk.artifacts.artifact_health import (
    ArtifactHealthResult,
    ArtifactStatusType,
    get_artifact_health,
)
from erk.artifacts.detection import is_in_erk_repo
from erk.artifacts.models import ArtifactFileState
from erk.artifacts.state import load_artifact_state
from erk.core.claude_settings import (
    ERK_PERMISSION,
    StatuslineNotConfigured,
    get_repo_claude_settings_path,
    get_statusline_config,
    has_erk_permission,
    has_erk_statusline,
    has_exit_plan_hook,
    read_claude_settings,
)
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk.core.version_check import get_required_version, is_version_mismatch
from erk_shared.extraction.claude_installation import ClaudeInstallation
from erk_shared.gateway.shell.abc import Shell
from erk_shared.github_admin.abc import GitHubAdmin


@dataclass(frozen=True)
class CheckResult:
    """Result of a single health check.

    Attributes:
        name: Name of the check
        passed: Whether the check passed
        message: Human-readable message describing the result
        details: Optional additional details (e.g., version info)
        warning: If True and passed=True, displays ⚠️ instead of ✅
        info: If True and passed=True, displays ℹ️ (informational, not success)
    """

    name: str
    passed: bool
    message: str
    details: str | None = None
    warning: bool = False
    info: bool = False


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


def _get_installed_erk_version() -> str | None:
    """Get installed erk version, or None if not installed."""
    try:
        from importlib.metadata import version

        return version("erk")
    except Exception:
        return None


def check_required_tool_version(repo_root: Path) -> CheckResult:
    """Check that installed erk version matches the required version file.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult indicating:
        - FAIL if version file missing
        - FAIL with warning if versions mismatch
        - PASS if versions match
    """
    required_version = get_required_version(repo_root)
    if required_version is None:
        return CheckResult(
            name="required-version",
            passed=False,
            message="Required version file missing (.erk/required-erk-uv-tool-version)",
            details="Run 'erk init' to create this file",
        )

    installed_version = _get_installed_erk_version()
    if installed_version is None:
        return CheckResult(
            name="required-version",
            passed=False,
            message="Could not determine installed erk version",
        )

    if is_version_mismatch(installed_version, required_version):
        return CheckResult(
            name="required-version",
            passed=False,
            message=f"Version mismatch: installed {installed_version}, required {required_version}",
            details="Run 'uv tool upgrade erk' to update",
        )

    return CheckResult(
        name="required-version",
        passed=True,
        message=f"erk version matches required ({required_version})",
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
            name="github-auth",
            passed=False,
            message="Cannot check auth: gh not installed",
        )

    auth_status = admin.check_auth_status()

    if auth_status.error is not None:
        return CheckResult(
            name="github-auth",
            passed=False,
            message=f"Auth check failed: {auth_status.error}",
        )

    if auth_status.authenticated:
        if auth_status.username:
            return CheckResult(
                name="github-auth",
                passed=True,
                message=f"GitHub authenticated as {auth_status.username}",
            )
        return CheckResult(
            name="github-auth",
            passed=True,
            message="Authenticated to GitHub",
        )
    else:
        return CheckResult(
            name="github-auth",
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
            name="workflow-permissions",
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
            name="workflow-permissions",
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
                name="workflow-permissions",
                passed=True,
                message="Workflows can create PRs",
            )
        else:
            return CheckResult(
                name="workflow-permissions",
                passed=True,  # Info level - always passes
                message="Workflows cannot create PRs",
                details="Run 'erk admin github-pr-setting --enable' to allow",
            )
    except Exception:
        return CheckResult(
            name="workflow-permissions",
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


def check_hooks_disabled(claude_installation: ClaudeInstallation) -> CheckResult:
    """Check if Claude Code hooks are globally disabled.

    Checks global settings for hooks.disabled=true via the ClaudeInstallation gateway.

    Args:
        claude_installation: Gateway for accessing Claude settings

    Returns a warning (not failure) if hooks are disabled, since the user
    may have intentionally disabled them.
    """
    disabled_in: list[str] = []

    # Check global settings via gateway
    settings = claude_installation.read_settings()
    if settings:
        hooks = settings.get("hooks", {})
        if hooks.get("disabled") is True:
            disabled_in.append("settings.json")

    # Check local settings file directly (not yet in gateway)
    local_settings_path = claude_installation.get_local_settings_path()
    if local_settings_path.exists():
        content = local_settings_path.read_text(encoding="utf-8")
        local_settings = json.loads(content)
        hooks = local_settings.get("hooks", {})
        if hooks.get("disabled") is True:
            disabled_in.append("settings.local.json")

    if disabled_in:
        return CheckResult(
            name="claude-hooks",
            passed=True,  # Don't fail, just warn
            warning=True,
            message=f"Hooks disabled in {', '.join(disabled_in)}",
            details="Set hooks.disabled=false or remove the setting to enable hooks",
        )

    return CheckResult(
        name="claude-hooks",
        passed=True,
        message="Hooks enabled (not globally disabled)",
    )


def check_statusline_configured(claude_installation: ClaudeInstallation) -> CheckResult:
    """Check if erk-statusline is configured in global Claude settings.

    This is an info-level check - it always passes, but informs users
    they can configure the erk statusline feature.

    Args:
        claude_installation: Gateway for accessing Claude settings

    Returns:
        CheckResult with info about statusline status
    """
    # Read settings via gateway
    if not claude_installation.settings_exists():
        return CheckResult(
            name="statusline",
            passed=True,
            message="No global Claude settings (statusline not configured)",
            details="Run 'erk init --statusline' to enable erk statusline",
            info=True,
        )

    settings = claude_installation.read_settings()

    if has_erk_statusline(settings):
        return CheckResult(
            name="statusline",
            passed=True,
            message="erk-statusline configured",
        )

    # Check if a different statusline is configured
    statusline_config = get_statusline_config(settings)
    if not isinstance(statusline_config, StatuslineNotConfigured):
        return CheckResult(
            name="statusline",
            passed=True,
            message=f"Different statusline configured: {statusline_config.command}",
            details="Run 'erk init --statusline' to switch to erk statusline",
            info=True,
        )

    return CheckResult(
        name="statusline",
        passed=True,
        message="erk-statusline not configured",
        details="Run 'erk init --statusline' to enable erk statusline",
        info=True,
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


def check_legacy_prompt_hooks(repo_root: Path) -> CheckResult:
    """Check for legacy prompt hook files that should be migrated.

    Checks if .erk/post-implement.md exists (old location) and suggests
    migration to the new .erk/prompt-hooks/ structure.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with migration suggestion if old location found
    """
    old_hook_path = repo_root / ".erk" / "post-implement.md"
    new_hook_path = repo_root / ".erk" / "prompt-hooks" / "post-plan-implement-ci.md"

    # Old location doesn't exist - all good
    if not old_hook_path.exists():
        return CheckResult(
            name="legacy-prompt-hooks",
            passed=True,
            message="No legacy prompt hooks found",
        )

    # Old location exists and new location exists - user hasn't cleaned up
    if new_hook_path.exists():
        return CheckResult(
            name="legacy-prompt-hooks",
            passed=True,
            warning=True,
            message="Legacy prompt hook found alongside new location",
            details=f"Remove old file: rm {old_hook_path.relative_to(repo_root)}",
        )

    # Old location exists, new location doesn't - needs migration
    return CheckResult(
        name="legacy-prompt-hooks",
        passed=True,
        warning=True,
        message="Legacy prompt hook found (needs migration)",
        details=(
            f"Old: {old_hook_path.relative_to(repo_root)}\n"
            f"New: {new_hook_path.relative_to(repo_root)}\n"
            f"Run: mkdir -p .erk/prompt-hooks && "
            f"mv {old_hook_path.relative_to(repo_root)} "
            f"{new_hook_path.relative_to(repo_root)}"
        ),
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
    settings = read_claude_settings(settings_path)
    if settings is None:
        return CheckResult(
            name="claude-erk-permission",
            passed=True,  # Info level - always passes
            message="No .claude/settings.json in repo",
        )

    # Check for permission
    if has_erk_permission(settings):
        return CheckResult(
            name="claude-erk-permission",
            passed=True,
            message=f"erk permission configured ({ERK_PERMISSION})",
        )
    else:
        return CheckResult(
            name="claude-erk-permission",
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

    Raises:
        json.JSONDecodeError: If settings.json contains invalid JSON
    """
    settings_path = repo_root / ".claude" / "settings.json"
    settings = read_claude_settings(settings_path)
    if settings is None:
        return CheckResult(
            name="claude-settings",
            passed=True,
            message="No .claude/settings.json (using defaults)",
        )

    return CheckResult(
        name="claude-settings",
        passed=True,
        message=".claude/settings.json looks valid",
    )


def check_user_prompt_hook(repo_root: Path) -> CheckResult:
    """Check that the UserPromptSubmit hook is configured.

    Verifies that .claude/settings.json contains the erk exec user-prompt-hook
    command for the UserPromptSubmit event.

    Args:
        repo_root: Path to the repository root (where .claude/ should be located)
    """
    settings_path = repo_root / ".claude" / "settings.json"
    if not settings_path.exists():
        return CheckResult(
            name="user-prompt-hook",
            passed=False,
            message="No .claude/settings.json found",
            details="Run 'erk init' to create settings with the hook configured",
        )
    # File exists, so read_claude_settings won't return None
    settings = read_claude_settings(settings_path)
    assert settings is not None  # file existence already checked

    # Look for UserPromptSubmit hooks
    hooks = settings.get("hooks", {})
    user_prompt_hooks = hooks.get("UserPromptSubmit", [])

    if not user_prompt_hooks:
        return CheckResult(
            name="user-prompt-hook",
            passed=False,
            message="No UserPromptSubmit hook configured",
            details="Add 'erk exec user-prompt-hook' hook to .claude/settings.json",
        )

    # Check if the unified hook is present (handles nested matcher structure)
    expected_command = "erk exec user-prompt-hook"
    for hook_entry in user_prompt_hooks:
        if not isinstance(hook_entry, dict):
            continue
        # Handle nested structure: {matcher: ..., hooks: [...]}
        nested_hooks = hook_entry.get("hooks", [])
        if nested_hooks:
            for hook in nested_hooks:
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command", "")
                if expected_command in command:
                    return CheckResult(
                        name="user-prompt-hook",
                        passed=True,
                        message="UserPromptSubmit hook configured",
                    )
        # Handle flat structure: {type: command, command: ...}
        command = hook_entry.get("command", "")
        if expected_command in command:
            return CheckResult(
                name="user-prompt-hook",
                passed=True,
                message="UserPromptSubmit hook configured",
            )

    # Hook section exists but doesn't have the expected command
    return CheckResult(
        name="user-prompt-hook",
        passed=False,
        message="UserPromptSubmit hook missing unified hook script",
        details=f"Expected command containing: {expected_command}",
    )


def check_exit_plan_hook(repo_root: Path) -> CheckResult:
    """Check that the ExitPlanMode hook is configured.

    Verifies that .claude/settings.json contains the erk exec exit-plan-mode-hook
    command for the PreToolUse ExitPlanMode matcher.

    Args:
        repo_root: Path to the repository root (where .claude/ should be located)
    """
    settings_path = repo_root / ".claude" / "settings.json"
    if not settings_path.exists():
        return CheckResult(
            name="exit-plan-hook",
            passed=False,
            message="No .claude/settings.json found",
            details="Run 'erk init' to create settings with the hook configured",
        )
    # File exists, so read_claude_settings won't return None
    settings = read_claude_settings(settings_path)
    assert settings is not None  # file existence already checked

    if has_exit_plan_hook(settings):
        return CheckResult(
            name="exit-plan-hook",
            passed=True,
            message="ExitPlanMode hook configured",
        )

    return CheckResult(
        name="exit-plan-hook",
        passed=False,
        message="ExitPlanMode hook not configured",
        details="Run 'erk init' to add the hook to .claude/settings.json",
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


def _worst_status(statuses: list[ArtifactStatusType]) -> ArtifactStatusType:
    """Determine worst status from a list of statuses.

    Priority: not-installed > locally-modified > changed-upstream > up-to-date
    """
    if "not-installed" in statuses:
        return "not-installed"
    if "locally-modified" in statuses:
        return "locally-modified"
    if "changed-upstream" in statuses:
        return "changed-upstream"
    return "up-to-date"


def _extract_artifact_type(name: str) -> str:
    """Extract artifact type from artifact name.

    Examples:
        skills/dignified-python → skills
        commands/erk/plan-implement.md → commands
        agents/devrun → agents
        workflows/erk-impl.yml → workflows
        actions/setup-claude-erk → actions
        hooks/user-prompt-hook → hooks
    """
    return name.split("/")[0]


def _status_icon(status: ArtifactStatusType) -> str:
    """Get status icon for artifact status."""
    if status == "up-to-date":
        return "✅"
    if status == "locally-modified" or status == "changed-upstream":
        return "⚠️"
    return "❌"


def _status_description(status: ArtifactStatusType, count: int) -> str:
    """Get human-readable status description."""
    if status == "not-installed":
        if count == 1:
            return "not installed"
        return f"{count} not installed"
    if status == "locally-modified":
        if count == 1:
            return "locally modified"
        return f"{count} locally modified"
    if status == "changed-upstream":
        if count == 1:
            return "changed upstream"
        return f"{count} changed upstream"
    return ""


def _build_erk_repo_artifacts_result(result: ArtifactHealthResult) -> CheckResult:
    """Build CheckResult for erk repo case (all artifacts from source)."""
    # Group artifacts by type (count only, all healthy)
    by_type: dict[str, int] = {}
    for artifact in result.artifacts:
        artifact_type = _extract_artifact_type(artifact.name)
        by_type[artifact_type] = by_type.get(artifact_type, 0) + 1

    # Build per-type summary (all ✅)
    type_summaries: list[str] = []
    type_order = ["skills", "commands", "agents", "workflows", "actions", "hooks"]
    for artifact_type in type_order:
        if artifact_type not in by_type:
            continue
        count = by_type[artifact_type]
        type_summaries.append(f"   ✅ {artifact_type} ({count})")

    details = "\n".join(type_summaries)

    return CheckResult(
        name="managed-artifacts",
        passed=True,
        message="Managed artifacts (from source)",
        details=details,
    )


def _build_managed_artifacts_result(result: ArtifactHealthResult) -> CheckResult:
    """Build CheckResult from ArtifactHealthResult."""
    # Group artifacts by type
    by_type: dict[str, list[ArtifactStatusType]] = {}
    for artifact in result.artifacts:
        artifact_type = _extract_artifact_type(artifact.name)
        if artifact_type not in by_type:
            by_type[artifact_type] = []
        by_type[artifact_type].append(artifact.status)

    # Build per-type summary
    type_summaries: list[str] = []
    overall_worst: ArtifactStatusType = "up-to-date"
    has_issues = False

    # Consistent type ordering
    type_order = ["skills", "commands", "agents", "workflows", "actions", "hooks"]
    for artifact_type in type_order:
        if artifact_type not in by_type:
            continue

        statuses = by_type[artifact_type]
        count = len(statuses)
        worst = _worst_status(statuses)

        # Track overall worst for header
        if overall_worst == "up-to-date":
            overall_worst = worst
        elif worst == "not-installed":
            overall_worst = "not-installed"
        elif worst in ("locally-modified", "changed-upstream") and overall_worst not in (
            "not-installed",
        ):
            overall_worst = worst

        icon = _status_icon(worst)
        line = f"   {icon} {artifact_type} ({count})"

        # Add issue description if not up-to-date
        if worst != "up-to-date":
            has_issues = True
            issue_count = sum(1 for s in statuses if s == worst)
            desc = _status_description(worst, issue_count)
            line += f" - {desc}"

        type_summaries.append(line)

    details = "\n".join(type_summaries)

    # Add remediation hint if there are issues
    if overall_worst == "not-installed":
        details += "\n\n   Run 'erk artifact sync' to restore missing artifacts"

    # Determine overall result
    if overall_worst == "not-installed":
        return CheckResult(
            name="managed-artifacts",
            passed=False,
            message="Managed artifacts have issues",
            details=details,
        )
    elif has_issues:
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            warning=True,
            message="Managed artifacts have issues",
            details=details,
        )
    else:
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            message="Managed artifacts healthy",
            details=details,
        )


def check_managed_artifacts(repo_root: Path) -> CheckResult:
    """Check status of erk-managed artifacts.

    Shows a summary of artifact status by type (skills, commands, agents, etc.)
    with per-type counts and status indicators.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with artifact health status
    """
    in_erk_repo = is_in_erk_repo(repo_root)

    # Check for .claude/ directory
    claude_dir = repo_root / ".claude"
    if not claude_dir.exists():
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            message="No .claude/ directory (nothing to check)",
        )

    # Load saved artifact state
    state = load_artifact_state(repo_root)
    saved_files: dict[str, ArtifactFileState] = dict(state.files) if state else {}

    # Get artifact health
    result = get_artifact_health(repo_root, saved_files)

    # Handle skipped cases from get_artifact_health
    if result.skipped_reason == "no-claude-dir":
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            message="No .claude/ directory (nothing to check)",
        )

    if result.skipped_reason == "no-bundled-dir":
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            message="Bundled .claude/ not found (skipping check)",
        )

    # No artifacts to check
    if not result.artifacts:
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            message="No managed artifacts found",
        )

    # In erk repo, show counts without status comparison (all from source)
    if in_erk_repo:
        return _build_erk_repo_artifacts_result(result)

    return _build_managed_artifacts_result(result)


def run_all_checks(ctx: ErkContext) -> list[CheckResult]:
    """Run all health checks and return results.

    Args:
        ctx: ErkContext for repository checks (includes github_admin)

    Returns:
        List of CheckResult objects
    """
    shell = ctx.shell
    admin = ctx.github_admin

    claude_installation = ctx.claude_installation

    results = [
        check_erk_version(),
        check_claude_cli(shell),
        check_graphite_cli(shell),
        check_github_cli(shell),
        check_github_auth(shell, admin),
        check_uv_version(shell),
        check_hooks_disabled(claude_installation),
        check_statusline_configured(claude_installation),
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
        results.append(check_user_prompt_hook(repo_root))
        results.append(check_exit_plan_hook(repo_root))
        results.append(check_gitignore_entries(repo_root))
        results.append(check_required_tool_version(repo_root))
        results.append(check_legacy_prompt_hooks(repo_root))
        # Hook health check
        results.append(check_hook_health(repo_root))
        # GitHub workflow permissions check (requires repo context)
        results.append(check_workflow_permissions(ctx, repo_root, admin))
        # Managed artifacts check (consolidated from orphaned + missing)
        results.append(check_managed_artifacts(repo_root))

        from erk.core.health_checks_dogfooder import run_early_dogfooder_checks

        # Get metadata_dir if we have a RepoContext (for legacy config detection)
        metadata_dir = ctx.repo.repo_dir if isinstance(ctx.repo, RepoContext) else None
        results.extend(run_early_dogfooder_checks(repo_root, metadata_dir))

    return results
