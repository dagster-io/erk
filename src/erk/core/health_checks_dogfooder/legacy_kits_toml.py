"""Check for legacy .erk/kits.toml file.

This is a temporary check for early dogfooders. Delete this file once
all users have removed their kits.toml files.
"""

from pathlib import Path

from erk.core.health_checks import CheckResult


def check_legacy_kits_toml(repo_root: Path) -> CheckResult:
    """Check for legacy .erk/kits.toml file.

    Detects .erk/kits.toml which is no longer used. Managed project
    detection now uses .erk/config.toml instead.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with warning if legacy kits.toml found
    """
    kits_toml_path = repo_root / ".erk" / "kits.toml"

    if not kits_toml_path.exists():
        return CheckResult(
            name="legacy kits.toml",
            passed=True,
            message="No legacy kits.toml found",
        )

    return CheckResult(
        name="legacy kits.toml",
        passed=True,  # Warning only, doesn't fail
        warning=True,
        message="Legacy kits.toml found",
        details=(
            f"File: {kits_toml_path}\n"
            "This file is no longer used. Managed project detection now uses .erk/config.toml.\n"
            "You can safely delete this file."
        ),
    )
