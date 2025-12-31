"""Check for legacy .erk/kits/ directory.

This is a temporary check for early dogfooders. Delete this file once
all users have removed their kits folder.
"""

from pathlib import Path

from erk.core.health_checks import CheckResult


def check_legacy_erk_kits_folder(repo_root: Path) -> CheckResult:
    """Check for legacy .erk/kits/ directory.

    Detects .erk/kits/ which is no longer used. The kit system has been
    removed entirely from erk.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with warning if legacy kits folder found
    """
    kits_path = repo_root / ".erk" / "kits"

    if not kits_path.exists():
        return CheckResult(
            name="legacy erk kits folder",
            passed=True,
            message="No legacy .erk/kits/ found",
        )

    if not kits_path.is_dir():
        return CheckResult(
            name="legacy erk kits folder",
            passed=True,
            message="No legacy .erk/kits/ found",
        )

    # Count items in the directory
    items = list(kits_path.iterdir())

    if not items:
        return CheckResult(
            name="legacy erk kits folder",
            passed=True,
            message="No legacy .erk/kits/ found (empty directory)",
        )

    return CheckResult(
        name="legacy erk kits folder",
        passed=True,  # Warning only, doesn't fail
        warning=True,
        message=f"Legacy kits folder found ({len(items)} item(s))",
        details=(
            f"Directory: {kits_path}\n"
            "The kit system has been removed from erk.\n"
            "You can safely delete the .erk/kits/ directory."
        ),
    )
