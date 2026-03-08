"""Check that required erk labels exist in the plans repository."""

from pathlib import Path

from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.objective_issues import LabelDefinition, get_required_erk_labels


def check_plans_repo_labels(
    repo_root: Path,
    plans_repo: str,
    github_issues: GitHubIssues,
) -> CheckResult:
    """Check that required erk labels exist in the plans repository.

    When plans_repo is configured, issues are created in that repository.
    This check verifies that required erk labels (erk-plan, erk-objective)
    exist in the target repository. Excludes erk-extraction which is
    optional for documentation workflows.

    Args:
        repo_root: Path to the working repository root (for gh CLI context)
        plans_repo: Target repository in "owner/repo" format
        github_issues: GitHubIssues interface (should be configured with target_repo)

    Returns:
        CheckResult indicating whether labels are present
    """
    labels = get_required_erk_labels()
    missing_labels: list[LabelDefinition] = []

    # Check each label exists (LBYL pattern - check before reporting)
    for label in labels:
        if not github_issues.label_exists(repo_root, label.name):
            missing_labels.append(label)

    if missing_labels:
        # Build gh label create commands for remediation
        commands = [
            f'gh label create "{label.name}" --description "{label.description}" '
            f'--color "{label.color}" -R {plans_repo}'
            for label in missing_labels
        ]
        missing_names = ", ".join(label.name for label in missing_labels)
        return CheckResult(
            name="plans-repo-labels",
            passed=False,
            message=f"Missing labels in {plans_repo}: {missing_names}",
            remediation="\n  ".join(commands),
        )

    return CheckResult(
        name="plans-repo-labels",
        passed=True,
        message=f"Labels configured in {plans_repo}",
    )
