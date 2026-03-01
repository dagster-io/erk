"""Check for post-init prompt hook for new developer setup."""

from pathlib import Path

from erk.core.health_checks.models import CheckResult


def check_post_init_hook(repo_root: Path) -> CheckResult:
    """Check for post-init prompt hook for new developer setup.

    When the hook file exists, this returns a success (green).
    When missing, it returns info-level with instructions to create.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with post-init hook status
    """
    hook_relative_path = ".erk/prompt-hooks/post-init.md"
    hook_path = repo_root / hook_relative_path

    if hook_path.exists():
        return CheckResult(
            name="post-init-hook",
            passed=True,
            message=f"Post-init hook configured ({hook_relative_path})",
            info=False,
        )

    return CheckResult(
        name="post-init-hook",
        passed=True,
        message=f"No post-init hook ({hook_relative_path})",
        details=(
            "Create .erk/prompt-hooks/post-init.md "
            "to add setup instructions for developers joining the project"
        ),
        info=True,
    )
