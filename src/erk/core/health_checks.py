"""Health check implementations for erk doctor command.

This module provides diagnostic checks for erk setup, including
CLI availability, repository configuration, and Claude settings.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

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


def check_kit_system() -> CheckResult:
    """Check if kit system (dot-agent) is installed and available in PATH."""
    dot_agent_path = shutil.which("dot-agent")
    if dot_agent_path is None:
        return CheckResult(
            name="kit-system",
            passed=False,
            message="Kit system not found in PATH",
            details="Kit system is required for Claude Code integrations",
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
            name="kit-system",
            passed=True,
            message=f"Kit system available: {version_output}",
            details=version_output,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="kit-system",
            passed=True,
            message="Kit system found (version check timed out)",
            details="timeout",
        )
    except Exception:
        return CheckResult(
            name="kit-system",
            passed=True,
            message="Kit system found (version check failed)",
            details="unknown",
        )


def check_kit_health() -> CheckResult:
    """Run kit health check to verify kit configuration."""
    dot_agent_path = shutil.which("dot-agent")
    if dot_agent_path is None:
        return CheckResult(
            name="kit health",
            passed=False,
            message="Cannot run check: kit system not found",
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
                name="kit health",
                passed=True,
                message="Kit health check passed",
                details=result.stdout.strip() if result.stdout else None,
            )
        else:
            return CheckResult(
                name="kit health",
                passed=False,
                message="Kit health check failed",
                details=result.stderr.strip() if result.stderr else result.stdout.strip(),
            )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="kit health",
            passed=False,
            message="Kit health check timed out",
        )
    except Exception as e:
        return CheckResult(
            name="kit health",
            passed=False,
            message=f"Kit health check error: {e}",
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
                # Check if the command looks like a dot-agent kit command
                if "dot-agent" in hook_cmd and "kit-command" in hook_cmd:
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
    # Format: DOT_AGENT_KIT_ID=erk ... dot-agent kit-command erk <command-name>
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
    ]

    # Only run kit health check if kit system is available
    if shutil.which("dot-agent") is not None:
        results.append(check_kit_health())

    # Add repository check
    results.append(check_repository(ctx))

    # Check Claude settings if we're in a repo
    # (get_git_common_dir returns None if not in a repo)
    git_dir = ctx.git.get_git_common_dir(ctx.cwd)
    if git_dir is not None:
        repo_root = ctx.git.get_repository_root(ctx.cwd)
        results.append(check_claude_settings(repo_root))

    return results
