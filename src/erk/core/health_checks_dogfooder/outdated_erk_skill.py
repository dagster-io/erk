"""Check for outdated erk skill that should be deleted.

This is a temporary check for early dogfooders. Delete this file once
all users have removed the outdated .claude/skills/erk/ directory.
"""

from pathlib import Path

from erk.core.health_checks import CheckResult


def check_outdated_erk_skill(repo_root: Path) -> CheckResult:
    """Check for outdated erk skill directory that should be deleted.

    The erk skill at .claude/skills/erk/ is outdated and no longer maintained.
    Users should delete this directory.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult indicating whether outdated skill was found
    """
    skill_dir = repo_root / ".claude" / "skills" / "erk"
    if not skill_dir.exists():
        return CheckResult(
            name="outdated erk skill",
            passed=True,
            message="No outdated erk skill found",
        )

    # Found outdated skill - return failure with remediation
    return CheckResult(
        name="outdated erk skill",
        passed=False,
        message="Outdated erk skill found at .claude/skills/erk/",
        details=(
            "The erk skill is outdated and should be deleted.\n"
            "\n"
            "Remediation:\n"
            "  rm -rf .claude/skills/erk/"
        ),
    )
