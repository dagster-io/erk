"""Operation module for erk repo check."""

from dataclasses import dataclass
from typing import Any

from erk.cli.commands.repo.check.checks import (
    RepoCheckItem,
    check_label_exists,
    check_secret_exists,
    check_variable_not_disabled,
    check_workflow_exists,
    check_workflow_permissions,
)
from erk.cli.constants import WORKFLOW_COMMAND_MAP
from erk_shared.gateway.github.objective_issues import (
    LabelDefinition,
    get_erk_label_definitions,
)

# Secrets required for erk workflows
_REQUIRED_SECRETS = (
    "ERK_QUEUE_GH_PAT",
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN",
)

# Variable that must not be set to "false"
_CHECKED_VARIABLE = "CLAUDE_ENABLED"


@dataclass(frozen=True)
class RepoCheckRequest:
    repo: str  # "owner/repo" format


@dataclass(frozen=True)
class RepoCheckResult:
    repo: str
    checks: tuple[RepoCheckItem, ...]

    @property
    def all_passed(self) -> bool:
        return all(item.passed for item in self.checks)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "all_passed": self.all_passed,
            "checks": [
                {
                    "name": item.name,
                    "passed": item.passed,
                    "message": item.message,
                    "remediation": item.remediation,
                }
                for item in self.checks
            ],
        }


def _parse_owner_repo(repo: str) -> tuple[str, str] | None:
    """Parse 'owner/repo' string. Returns None if invalid format."""
    parts = repo.split("/")
    if len(parts) != 2:
        return None
    owner, repo_name = parts
    if not owner or not repo_name:
        return None
    return owner, repo_name


def _get_label_definitions() -> list[LabelDefinition]:
    """Get all erk label definitions for checking."""
    return get_erk_label_definitions()


def run_repo_check(request: RepoCheckRequest) -> RepoCheckResult:
    """Run all repo setup checks against a remote GitHub repository."""
    parsed = _parse_owner_repo(request.repo)
    if parsed is None:
        return RepoCheckResult(
            repo=request.repo,
            checks=(
                RepoCheckItem(
                    name="format",
                    passed=False,
                    message=f"Invalid repo format: '{request.repo}' (expected 'owner/repo')",
                    remediation="Use format: erk repo check owner/repo",
                ),
            ),
        )

    owner, repo_name = parsed
    items: list[RepoCheckItem] = []

    # Check workflows
    for workflow_filename in WORKFLOW_COMMAND_MAP.values():
        items.append(check_workflow_exists(owner, repo_name, workflow_filename))

    # Check secrets
    for secret_name in _REQUIRED_SECRETS:
        items.append(check_secret_exists(owner, repo_name, secret_name))

    # Check variable
    items.append(check_variable_not_disabled(owner, repo_name, _CHECKED_VARIABLE))

    # Check workflow permissions
    items.append(check_workflow_permissions(owner, repo_name))

    # Check labels
    for label_def in _get_label_definitions():
        items.append(
            check_label_exists(
                owner,
                repo_name,
                label_def.name,
                label_color=label_def.color,
                label_description=label_def.description,
            )
        )

    return RepoCheckResult(repo=request.repo, checks=tuple(items))
