"""Check for deprecated config options in .erk/config.toml.

This is a temporary check for early dogfooders. Delete this file once
all users have updated their config options.
"""

from pathlib import Path

from erk.core.health_checks import CheckResult

# Deprecated option name -> new option name
DEPRECATED_OPTIONS = {
    "auto_restack_skip_dangerous": "auto_restack_require_dangerous_flag",
}


def check_legacy_config_option(repo_root: Path) -> CheckResult:
    """Check for deprecated config options in .erk/config.toml.

    Detects deprecated option names that should be renamed. The
    'auto_restack_skip_dangerous' option was renamed to
    'auto_restack_require_dangerous_flag' (note: default behavior also flipped).

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with failure if deprecated options found
    """
    config_path = repo_root / ".erk" / "config.toml"

    if not config_path.exists():
        return CheckResult(
            name="legacy config option",
            passed=True,
            message="No .erk/config.toml found",
        )

    content = config_path.read_text(encoding="utf-8")

    # Check for deprecated options
    found_deprecated: list[tuple[str, str]] = []
    for old_name, new_name in DEPRECATED_OPTIONS.items():
        if old_name in content:
            found_deprecated.append((old_name, new_name))

    if not found_deprecated:
        return CheckResult(
            name="legacy config option",
            passed=True,
            message="No deprecated config options found",
        )

    # Build details with migration instructions
    details_lines: list[str] = ["Deprecated config options found:"]
    for old_name, new_name in found_deprecated:
        details_lines.append(f"  - {old_name} -> {new_name}")
    details_lines.append("")
    details_lines.append(f"Edit {config_path} to rename the option(s).")
    details_lines.append("Note: 'auto_restack_require_dangerous_flag' has inverted logic.")

    return CheckResult(
        name="legacy config option",
        passed=False,  # Failure - config won't work correctly
        message=f"Found {len(found_deprecated)} deprecated config option(s)",
        details="\n".join(details_lines),
    )
