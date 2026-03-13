"""Individual check functions for remote repo setup validation."""

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class RepoCheckItem:
    name: str
    passed: bool
    message: str
    remediation: str | None


def _gh_api_status(owner: str, repo: str, path: str) -> int | None:
    """Call gh api and return the HTTP status code, or None on error."""
    cmd = [
        "gh",
        "api",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
        f"/repos/{owner}/{repo}/{path}",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode == 0:
            return 200
        if "404" in result.stderr or "Not Found" in result.stderr:
            return 404
        return None
    except (subprocess.TimeoutExpired, OSError):
        return None


def check_workflow_exists(owner: str, repo: str, filename: str) -> RepoCheckItem:
    """Check if a GitHub Actions workflow file exists in the repo."""
    status = _gh_api_status(owner, repo, f"contents/.github/workflows/{filename}")
    if status == 200:
        return RepoCheckItem(
            name=f"workflow:{filename}",
            passed=True,
            message=f"Workflow {filename} exists",
            remediation=None,
        )
    if status == 404:
        return RepoCheckItem(
            name=f"workflow:{filename}",
            passed=False,
            message=f"Workflow {filename} not found",
            remediation=f"Copy {filename} from erk template repo to .github/workflows/",
        )
    return RepoCheckItem(
        name=f"workflow:{filename}",
        passed=False,
        message=f"Could not check workflow {filename} (API error)",
        remediation="Verify gh CLI authentication and repo access",
    )


def check_secret_exists(owner: str, repo: str, secret_name: str) -> RepoCheckItem:
    """Check if a repository secret exists."""
    status = _gh_api_status(owner, repo, f"actions/secrets/{secret_name}")
    if status == 200:
        return RepoCheckItem(
            name=f"secret:{secret_name}",
            passed=True,
            message=f"Secret {secret_name} is set",
            remediation=None,
        )
    if status == 404:
        return RepoCheckItem(
            name=f"secret:{secret_name}",
            passed=False,
            message=f"Secret {secret_name} not found",
            remediation=f"Run: gh secret set {secret_name} --repo {owner}/{repo}",
        )
    return RepoCheckItem(
        name=f"secret:{secret_name}",
        passed=False,
        message=f"Could not check secret {secret_name} (API error)",
        remediation="Verify gh CLI authentication and repo admin access",
    )


def check_variable_not_disabled(owner: str, repo: str, variable_name: str) -> RepoCheckItem:
    """Check that a repo variable is not explicitly set to 'false'.

    Passes if the variable is unset or set to any value except 'false'.
    """
    cmd = [
        "gh",
        "variable",
        "get",
        variable_name,
        "--repo",
        f"{owner}/{repo}",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode != 0:
            # Variable doesn't exist — that's fine
            return RepoCheckItem(
                name=f"variable:{variable_name}",
                passed=True,
                message=f"Variable {variable_name} is not set (ok)",
                remediation=None,
            )
        value = result.stdout.strip()
        if value.lower() == "false":
            return RepoCheckItem(
                name=f"variable:{variable_name}",
                passed=False,
                message=f"Variable {variable_name} is explicitly disabled (value: 'false')",
                remediation=(
                    f"Run: gh variable delete {variable_name} --repo {owner}/{repo}"
                    f" or set to a truthy value"
                ),
            )
        return RepoCheckItem(
            name=f"variable:{variable_name}",
            passed=True,
            message=f"Variable {variable_name} = '{value}'",
            remediation=None,
        )
    except (subprocess.TimeoutExpired, OSError):
        return RepoCheckItem(
            name=f"variable:{variable_name}",
            passed=False,
            message=f"Could not check variable {variable_name} (timeout/error)",
            remediation="Verify gh CLI authentication and repo access",
        )


def check_workflow_permissions(owner: str, repo: str) -> RepoCheckItem:
    """Check that workflow permissions allow approving pull request reviews."""
    import json

    cmd = [
        "gh",
        "api",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
        f"/repos/{owner}/{repo}/actions/permissions/workflow",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode != 0:
            return RepoCheckItem(
                name="permissions:can_approve_pull_request_reviews",
                passed=False,
                message="Could not check workflow permissions (API error)",
                remediation="Verify gh CLI authentication and repo admin access",
            )
        data = json.loads(result.stdout)
        can_approve = data.get("can_approve_pull_request_reviews", False)
        if can_approve:
            return RepoCheckItem(
                name="permissions:can_approve_pull_request_reviews",
                passed=True,
                message="Workflow can approve pull request reviews",
                remediation=None,
            )
        return RepoCheckItem(
            name="permissions:can_approve_pull_request_reviews",
            passed=False,
            message="Workflows cannot approve pull request reviews",
            remediation=(
                "Go to Settings > Actions > General > Workflow permissions"
                " and enable 'Allow GitHub Actions to create and approve pull requests'"
            ),
        )
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
        return RepoCheckItem(
            name="permissions:can_approve_pull_request_reviews",
            passed=False,
            message="Could not check workflow permissions (timeout/parse error)",
            remediation="Verify gh CLI authentication and repo admin access",
        )


def check_label_exists(
    owner: str,
    repo: str,
    label_name: str,
    *,
    label_color: str,
    label_description: str,
) -> RepoCheckItem:
    """Check if a GitHub label exists in the repo."""
    status = _gh_api_status(owner, repo, f"labels/{label_name}")
    if status == 200:
        return RepoCheckItem(
            name=f"label:{label_name}",
            passed=True,
            message=f"Label '{label_name}' exists",
            remediation=None,
        )
    if status == 404:
        return RepoCheckItem(
            name=f"label:{label_name}",
            passed=False,
            message=f"Label '{label_name}' not found",
            remediation=(
                f"Run: gh label create '{label_name}'"
                f" --repo {owner}/{repo}"
                f" --color '{label_color}'"
                f" --description '{label_description}'"
            ),
        )
    return RepoCheckItem(
        name=f"label:{label_name}",
        passed=False,
        message=f"Could not check label '{label_name}' (API error)",
        remediation="Verify gh CLI authentication and repo access",
    )
