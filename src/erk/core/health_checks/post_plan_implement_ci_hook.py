"""Check for post-plan-implement CI instructions hook."""

from pathlib import Path

from erk.core.health_checks.models import CheckResult


def check_post_plan_implement_ci_hook(repo_root: Path) -> CheckResult:
    """Check for post-plan-implement CI instructions hook.

    When the hook file exists and has content, this returns a success (green).
    When missing, it returns info-level with the path to create.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with CI hook status
    """
    hook_relative_path = ".erk/prompt-hooks/post-plan-implement-ci.md"
    hook_path = repo_root / hook_relative_path

    if hook_path.exists():
        return CheckResult(
            name="post-plan-implement-ci-hook",
            passed=True,
            message=f"CI instructions hook configured ({hook_relative_path})",
            info=False,
        )

    return CheckResult(
        name="post-plan-implement-ci-hook",
        passed=True,
        message=f"No CI instructions hook ({hook_relative_path})",
        details=(
            "Create .erk/prompt-hooks/post-plan-implement-ci.md "
            "to add CI instructions for plan implementation"
        ),
        info=True,
    )
