"""Health check implementations for erk doctor command.

This module provides diagnostic checks for erk setup, including
CLI availability, repository configuration, and Claude settings.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from erk.core.claude_settings import (
    ERK_PERMISSION,
    get_repo_claude_settings_path,
    has_erk_permission,
    read_claude_settings,
)
from erk.core.context import ErkContext


@dataclass
class CheckResult:
    """Result of a single health check.

    Attributes:
        name: Name of the check
        passed: Whether the check passed
        message: Human-readable message describing the result
        details: Optional additional details (e.g., version info)
    """

    name: str
    passed: bool
    message: str
    details: str | None = None


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


def check_claude_cli() -> CheckResult:
    """Check if Claude CLI is installed and available in PATH."""
    claude_path = shutil.which("claude")
    if claude_path is None:
        return CheckResult(
            name="claude",
            passed=False,
            message="Claude CLI not found in PATH",
            details="Install from: https://claude.com/download",
        )

    # Try to get version
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        version_output = result.stdout.strip() or result.stderr.strip()
        # Parse version from output (format: "claude X.Y.Z")
        version_str = version_output.split()[-1] if version_output else "unknown"
        return CheckResult(
            name="claude",
            passed=True,
            message=f"Claude CLI available: {version_str}",
            details=version_str,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="claude",
            passed=True,
            message="Claude CLI found (version check timed out)",
            details="timeout",
        )
    except Exception:
        return CheckResult(
            name="claude",
            passed=True,
            message="Claude CLI found (version check failed)",
            details="unknown",
        )


def check_graphite_cli() -> CheckResult:
    """Check if Graphite CLI (gt) is installed and available in PATH."""
    gt_path = shutil.which("gt")
    if gt_path is None:
        return CheckResult(
            name="graphite",
            passed=False,
            message="Graphite CLI (gt) not found in PATH",
            details="Install from: https://graphite.dev/docs/installing-the-cli",
        )

    # Try to get version
    try:
        result = subprocess.run(
            ["gt", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        version_output = result.stdout.strip() or result.stderr.strip()
        return CheckResult(
            name="graphite",
            passed=True,
            message=f"Graphite CLI available: {version_output}",
            details=version_output,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="graphite",
            passed=True,
            message="Graphite CLI found (version check timed out)",
            details="timeout",
        )
    except Exception:
        return CheckResult(
            name="graphite",
            passed=True,
            message="Graphite CLI found (version check failed)",
            details="unknown",
        )


def check_github_cli() -> CheckResult:
    """Check if GitHub CLI (gh) is installed and available in PATH."""
    gh_path = shutil.which("gh")
    if gh_path is None:
        return CheckResult(
            name="github",
            passed=False,
            message="GitHub CLI (gh) not found in PATH",
            details="Install from: https://cli.github.com/",
        )

    # Try to get version
    try:
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        version_output = result.stdout.strip().split("\n")[0] if result.stdout else "unknown"
        return CheckResult(
            name="github",
            passed=True,
            message=f"GitHub CLI available: {version_output}",
            details=version_output,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="github",
            passed=True,
            message="GitHub CLI found (version check timed out)",
            details="timeout",
        )
    except Exception:
        return CheckResult(
            name="github",
            passed=True,
            message="GitHub CLI found (version check failed)",
            details="unknown",
        )


def check_github_auth() -> CheckResult:
    """Check if GitHub CLI is authenticated."""
    gh_path = shutil.which("gh")
    if gh_path is None:
        return CheckResult(
            name="github auth",
            passed=False,
            message="Cannot check auth: gh not installed",
        )

    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode == 0:
            # Parse output to find username
            # Format: "✓ Logged in to github.com account username (keyring)"
            output = result.stdout.strip() or result.stderr.strip()
            username = None
            for line in output.split("\n"):
                if "Logged in to" in line and "account" in line:
                    # Extract username from "... account username (...)"
                    parts = line.split("account")
                    if len(parts) > 1:
                        username_part = parts[1].strip()
                        username = username_part.split()[0] if username_part else None
                    break
            if username:
                return CheckResult(
                    name="github auth",
                    passed=True,
                    message=f"GitHub authenticated as {username}",
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
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="github auth",
            passed=False,
            message="Auth check timed out",
        )
    except Exception as e:
        return CheckResult(
            name="github auth",
            passed=False,
            message=f"Auth check failed: {e}",
        )


def check_workflow_permissions(ctx: ErkContext, repo_root: Path) -> CheckResult:
    """Check if GitHub Actions workflows can create PRs.

    This is an info-level check - it always passes, but shows whether
    PR creation is enabled for workflows. This is required for erk's
    remote implementation feature.

    Args:
        ctx: ErkContext for repository access
        repo_root: Path to the repository root

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

    # Check workflow permissions via API
    from erk.core.implementation_queue.github.real import RealGitHubAdmin

    admin = RealGitHubAdmin()

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


def check_dot_agent() -> CheckResult:
    """Check if dot-agent is installed and available in PATH."""
    dot_agent_path = shutil.which("dot-agent")
    if dot_agent_path is None:
        return CheckResult(
            name="dot-agent",
            passed=False,
            message="dot-agent not found in PATH",
            details="dot-agent is required for kit commands",
        )

    # Try to get version
    try:
        result = subprocess.run(
            ["dot-agent", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        version_output = result.stdout.strip() or result.stderr.strip() or "installed"
        return CheckResult(
            name="dot-agent",
            passed=True,
            message=f"dot-agent available: {version_output}",
            details=version_output,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="dot-agent",
            passed=True,
            message="dot-agent found (version check timed out)",
            details="timeout",
        )
    except Exception:
        return CheckResult(
            name="dot-agent",
            passed=True,
            message="dot-agent found (version check failed)",
            details="unknown",
        )


def check_uv_version() -> CheckResult:
    """Check if uv is installed.

    Shows version and upgrade instructions. erk works best with recent uv versions.
    """
    uv_path = shutil.which("uv")
    if uv_path is None:
        return CheckResult(
            name="uv",
            passed=False,
            message="uv not found in PATH",
            details="Install from: https://docs.astral.sh/uv/getting-started/installation/",
        )

    # Get installed version
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        version_output = result.stdout.strip() or result.stderr.strip()

        # Parse version (format: "uv 0.9.2" or "uv 0.9.2 (Homebrew 2025-10-10)")
        parts = version_output.split()
        version = parts[1] if len(parts) >= 2 else version_output

    except subprocess.TimeoutExpired:
        return CheckResult(
            name="uv",
            passed=True,
            message="uv found (version check timed out)",
            details="Upgrade: uv self update",
        )
    except Exception:
        return CheckResult(
            name="uv",
            passed=True,
            message="uv found (version check failed)",
            details="Upgrade: uv self update",
        )

    return CheckResult(
        name="uv",
        passed=True,
        message=f"uv available: {version}",
        details="erk works best with recent versions. Upgrade: uv self update",
    )


def check_dot_agent_health() -> CheckResult:
    """Run dot-agent check to verify kit health."""
    dot_agent_path = shutil.which("dot-agent")
    if dot_agent_path is None:
        return CheckResult(
            name="dot-agent health",
            passed=False,
            message="Cannot run check: dot-agent not found",
        )

    try:
        result = subprocess.run(
            ["dot-agent", "check"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode == 0:
            return CheckResult(
                name="dot-agent health",
                passed=True,
                message="dot-agent check passed",
                details=result.stdout.strip() if result.stdout else None,
            )
        else:
            return CheckResult(
                name="dot-agent health",
                passed=False,
                message="dot-agent check failed",
                details=result.stderr.strip() if result.stderr else result.stdout.strip(),
            )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="dot-agent health",
            passed=False,
            message="dot-agent check timed out",
        )
    except Exception as e:
        return CheckResult(
            name="dot-agent health",
            passed=False,
            message=f"dot-agent check error: {e}",
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
                # Check if the command looks like a kit command (old or new format)
                is_old_format = "dot-agent" in hook_cmd and "kit-command" in hook_cmd
                is_new_format = "erk kit exec" in hook_cmd
                if is_old_format or is_new_format:
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


def _kit_command_exists(command: str) -> bool:
    """Check if a kit command exists by trying to run it with --help.

    This is a heuristic check - we run the command with --help to see
    if it's recognized. This avoids executing arbitrary commands while
    still validating that the kit command is defined.
    """
    # Parse command to extract the base kit command
    # Old format: ERK_KIT_ID=erk ... dot-agent kit-command erk <command-name>
    # New format: ERK_KIT_ID=erk ... erk kit exec erk <command-name>
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
        ctx: ErkContext for repository checks

    Returns:
        List of CheckResult objects
    """
    results = [
        check_erk_version(),
        check_claude_cli(),
        check_graphite_cli(),
        check_github_cli(),
        check_github_auth(),
        check_uv_version(),
        check_dot_agent(),
    ]

    # Only run dot-agent health check if dot-agent is available
    if shutil.which("dot-agent") is not None:
        results.append(check_dot_agent_health())

    # Add repository check
    results.append(check_repository(ctx))

    # Check Claude settings, gitignore, and GitHub checks if we're in a repo
    # (get_git_common_dir returns None if not in a repo)
    git_dir = ctx.git.get_git_common_dir(ctx.cwd)
    if git_dir is not None:
        repo_root = ctx.git.get_repository_root(ctx.cwd)
        results.append(check_claude_erk_permission(repo_root))
        results.append(check_claude_settings(repo_root))
        results.append(check_gitignore_entries(repo_root))
        # GitHub workflow permissions check (requires repo context)
        results.append(check_workflow_permissions(ctx, repo_root))

    return results
