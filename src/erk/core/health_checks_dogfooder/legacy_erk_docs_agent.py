"""Check for legacy .erk/docs/agent/ directory.

This is a temporary check for early dogfooders. Delete this file once
all users have migrated their docs to docs/learned/.
"""

from pathlib import Path

from erk.core.health_checks import CheckResult


def check_legacy_erk_docs_agent(repo_root: Path) -> CheckResult:
    """Check for legacy .erk/docs/agent/ directory.

    Detects .erk/docs/agent/ which should be moved to docs/learned/.
    This is an erk-specific documentation location change.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with warning if legacy docs directory found
    """
    agent_docs_path = repo_root / ".erk" / "docs" / "agent"

    if not agent_docs_path.exists():
        return CheckResult(
            name="legacy-erk-docs",
            passed=True,
            message="No legacy .erk/docs/agent/ found",
        )

    if not agent_docs_path.is_dir():
        return CheckResult(
            name="legacy-erk-docs",
            passed=True,
            message="No legacy .erk/docs/agent/ found",
        )

    # Count files in the directory
    files = list(agent_docs_path.glob("**/*"))
    file_count = len([f for f in files if f.is_file()])

    if file_count == 0:
        return CheckResult(
            name="legacy-erk-docs",
            passed=True,
            message="No legacy .erk/docs/agent/ found (empty directory)",
        )

    return CheckResult(
        name="legacy-erk-docs",
        passed=True,  # Warning only, doesn't fail
        warning=True,
        message=f"Legacy docs location found ({file_count} file(s))",
        details=(
            f"Directory: {agent_docs_path}\n"
            "Documentation has moved from .erk/docs/agent/ to docs/learned/.\n"
            "Move your documentation files to docs/learned/."
        ),
    )
