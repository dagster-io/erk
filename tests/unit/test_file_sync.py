"""Tests to verify files that must be kept in sync are identical."""

from pathlib import Path


def _get_repo_root() -> Path:
    """Get the repository root directory."""
    current = Path(__file__).resolve()
    # Walk up until we find .git directory
    while current != current.parent:
        if (current / ".git").exists() or (current / ".git").is_file():
            return current
        current = current.parent
    msg = "Could not find repository root"
    raise RuntimeError(msg)


def test_diff_analysis_guide_in_sync_with_commit_message_prompt() -> None:
    """Verify the two copies of the diff-analysis prompt are identical.

    The prompt exists in two locations:
    1. .claude/skills/erk-diff-analysis/references/commit-message-prompt.md
       (used by erk-diff-analysis skill)
    2. packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md
       (used by Python CLI)

    These must stay in sync. If you need to update the prompt, update BOTH files.
    """
    repo_root = _get_repo_root()

    claude_docs_copy = (
        repo_root / ".claude/skills/erk-diff-analysis/references/commit-message-prompt.md"
    )
    python_package_copy = (
        repo_root / "packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md"
    )

    if not claude_docs_copy.exists():
        msg = f"Missing skill prompt copy: {claude_docs_copy}"
        raise AssertionError(msg)

    if not python_package_copy.exists():
        msg = f"Missing Python package copy: {python_package_copy}"
        raise AssertionError(msg)

    claude_content = claude_docs_copy.read_text(encoding="utf-8")
    python_content = python_package_copy.read_text(encoding="utf-8")

    assert claude_content == python_content, (
        "Skill prompt and Python package prompt are out of sync!\n"
        "These two files must have identical content:\n"
        f"  1. {claude_docs_copy.relative_to(repo_root)}\n"
        f"  2. {python_package_copy.relative_to(repo_root)}\n"
        "Update both files to keep them in sync."
    )
