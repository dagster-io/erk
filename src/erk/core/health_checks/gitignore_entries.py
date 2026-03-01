"""Check that required gitignore entries exist."""

from pathlib import Path

from erk.core.health_checks.models import CheckResult
from erk.core.init_utils import REQUIRED_GITIGNORE_ENTRIES


def check_gitignore_entries(repo_root: Path) -> CheckResult:
    """Check that required gitignore entries exist.

    Args:
        repo_root: Path to the repository root (where .gitignore should be located)

    Returns:
        CheckResult indicating whether required entries are present
    """
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
    for entry in REQUIRED_GITIGNORE_ENTRIES:
        if entry not in gitignore_content:
            missing_entries.append(entry)

    if missing_entries:
        return CheckResult(
            name="gitignore",
            passed=False,
            message=f"Missing gitignore entries: {', '.join(missing_entries)}",
            remediation="Run 'erk artifact sync' or 'erk init --upgrade'",
        )

    return CheckResult(
        name="gitignore",
        passed=True,
        message="Required gitignore entries present",
    )
