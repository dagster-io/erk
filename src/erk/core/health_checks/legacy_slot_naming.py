"""Check for legacy slot naming convention in pool state."""

from erk.core.health_checks.models import CheckResult
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import load_pool_state


def check_legacy_slot_naming(repo: RepoContext) -> CheckResult:
    """Check for legacy slot naming convention in pool state.

    The old naming convention was 'erk-managed-wt-XX'. The new convention
    is 'erk-slot-XX'. This check detects old-style assignments that need
    migration.

    Args:
        repo: Repository context with pool.json path

    Returns:
        CheckResult indicating whether legacy slot names were found
    """
    pool_state = load_pool_state(repo.pool_json_path)

    # No pool file exists - nothing to check
    if pool_state is None:
        return CheckResult(
            name="legacy-slot-naming",
            passed=True,
            message="No pool state configured",
        )

    # No assignments - nothing to check
    if not pool_state.assignments:
        return CheckResult(
            name="legacy-slot-naming",
            passed=True,
            message="No slot assignments to check",
        )

    # Check for old-style slot names
    old_style_slots: list[str] = []
    for assignment in pool_state.assignments:
        if assignment.slot_name.startswith("erk-managed-wt-"):
            old_style_slots.append(assignment.slot_name)

    if not old_style_slots:
        return CheckResult(
            name="legacy-slot-naming",
            passed=True,
            message="All slot assignments use current naming",
        )

    # Build details listing the old slots
    slots_list = ", ".join(old_style_slots)
    details = f"Old-style slots: {slots_list}"

    # Build remediation instructions
    repo_name = repo.repo_name
    remediation = (
        f"To migrate:\n"
        f"  1. Edit ~/.erk/repos/{repo_name}/pool.json - remove assignments "
        f"for: {slots_list}\n"
        f"  2. Delete old dirs: rm -rf ~/.erk/repos/{repo_name}/worktrees/erk-managed-wt-*\n"
        f"  3. Prune worktrees: git worktree prune"
    )

    message = (
        f"Legacy slot naming found ({len(old_style_slots)} assignment(s) use 'erk-managed-wt-XX')"
    )

    return CheckResult(
        name="legacy-slot-naming",
        passed=False,
        message=message,
        details=details,
        remediation=remediation,
    )
