"""Check for legacy .claude/docs/ directory.

This is a temporary check for early dogfooders. Delete this file once
all users have migrated their docs to skills.
"""

from pathlib import Path

from erk.core.health_checks import CheckResult


def check_legacy_claude_docs(repo_root: Path) -> CheckResult:
    """Check for legacy .claude/docs/ directory.

    Detects .claude/docs/ which is no longer supported. Standalone docs
    should be converted to skills under .claude/skills/<name>/SKILL.md.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with warning if legacy docs directory found
    """
    docs_path = repo_root / ".claude" / "docs"

    if not docs_path.exists():
        return CheckResult(
            name="legacy claude docs",
            passed=True,
            message="No legacy .claude/docs/ found",
        )

    # Check if it's a directory with markdown files
    if not docs_path.is_dir():
        return CheckResult(
            name="legacy claude docs",
            passed=True,
            message="No legacy .claude/docs/ found",
        )

    # Find markdown files
    md_files = list(docs_path.glob("*.md"))
    if not md_files:
        return CheckResult(
            name="legacy claude docs",
            passed=True,
            message="No legacy .claude/docs/ found (empty directory)",
        )

    # Build details with file list
    details_lines: list[str] = [
        "Standalone docs in .claude/docs/ no longer supported.",
        "",
        "Files found:",
    ]
    for md_file in md_files[:5]:  # Limit display to first 5
        details_lines.append(f"  - {md_file.name}")
    if len(md_files) > 5:
        details_lines.append(f"  ... and {len(md_files) - 5} more")
    details_lines.append("")
    details_lines.append("Convert to skills under .claude/skills/<name>/SKILL.md")

    return CheckResult(
        name="legacy claude docs",
        passed=True,  # Warning only, doesn't fail
        warning=True,
        message=f"Found {len(md_files)} doc(s) in .claude/docs/",
        details="\n".join(details_lines),
    )
