"""Check for legacy prompt hook files that should be migrated."""

from pathlib import Path

from erk.core.health_checks.models import CheckResult


def check_legacy_prompt_hooks(repo_root: Path) -> CheckResult:
    """Check for legacy prompt hook files that should be migrated.

    Checks if .erk/post-implement.md exists (old location) and suggests
    migration to the new .erk/prompt-hooks/ structure.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with migration suggestion if old location found
    """
    old_hook_path = repo_root / ".erk" / "post-implement.md"
    new_hook_path = repo_root / ".erk" / "prompt-hooks" / "post-plan-implement-ci.md"

    # Old location doesn't exist - all good
    if not old_hook_path.exists():
        return CheckResult(
            name="legacy-prompt-hooks",
            passed=True,
            message="No legacy prompt hooks found",
        )

    # Old location exists and new location exists - user hasn't cleaned up
    if new_hook_path.exists():
        return CheckResult(
            name="legacy-prompt-hooks",
            passed=True,
            warning=True,
            message="Legacy prompt hook found alongside new location",
            details=f"Remove old file: rm {old_hook_path.relative_to(repo_root)}",
        )

    # Old location exists, new location doesn't - needs migration
    return CheckResult(
        name="legacy-prompt-hooks",
        passed=True,
        warning=True,
        message="Legacy prompt hook found (needs migration)",
        details=(
            f"Old: {old_hook_path.relative_to(repo_root)}\n"
            f"New: {new_hook_path.relative_to(repo_root)}\n"
            f"Run: mkdir -p .erk/prompt-hooks && "
            f"mv {old_hook_path.relative_to(repo_root)} "
            f"{new_hook_path.relative_to(repo_root)}"
        ),
    )
