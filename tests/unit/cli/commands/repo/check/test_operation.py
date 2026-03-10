"""Tests for repo check operation.

Tests run_repo_check by mocking subprocess.run to simulate
gh api responses for workflows, secrets, variables, permissions, and labels.
"""

import subprocess
from collections.abc import Callable
from unittest.mock import patch

from erk.cli.commands.repo.check.operation import (
    RepoCheckRequest,
    RepoCheckResult,
    run_repo_check,
)


def _make_subprocess_result(
    *,
    returncode: int,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _all_pass_side_effect() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Return a side_effect that makes all gh api calls succeed."""

    def side_effect(
        cmd: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        # Workflow permissions returns JSON with can_approve_pull_request_reviews
        if "actions/permissions/workflow" in " ".join(cmd):
            return _make_subprocess_result(
                returncode=0,
                stdout=(
                    '{"can_approve_pull_request_reviews": true,'
                    ' "default_workflow_permissions": "write"}'
                ),
            )
        # gh variable get
        if "variable" in cmd and "get" in cmd:
            return _make_subprocess_result(returncode=1, stderr="variable not found")
        # Everything else (workflows, secrets, labels) returns 200
        return _make_subprocess_result(returncode=0, stdout="{}")

    return side_effect


def _all_fail_side_effect() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Return a side_effect that makes all gh api calls fail with 404."""

    def side_effect(
        cmd: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        # Workflow permissions returns JSON without approval
        if "actions/permissions/workflow" in " ".join(cmd):
            return _make_subprocess_result(
                returncode=0,
                stdout=(
                    '{"can_approve_pull_request_reviews": false,'
                    ' "default_workflow_permissions": "read"}'
                ),
            )
        # gh variable get returns "false"
        if "variable" in cmd and "get" in cmd:
            return _make_subprocess_result(returncode=0, stdout="false")
        # Everything else returns 404
        return _make_subprocess_result(returncode=1, stderr="HTTP 404: Not Found")

    return side_effect


def test_invalid_repo_format() -> None:
    """Invalid repo format returns a single failed check."""
    result = run_repo_check(RepoCheckRequest(repo="invalid"))

    assert not result.all_passed
    assert len(result.checks) == 1
    assert result.checks[0].name == "format"
    assert not result.checks[0].passed
    assert "owner/repo" in result.checks[0].message


def test_invalid_repo_format_empty_parts() -> None:
    """Repo with empty owner or name returns format error."""
    result = run_repo_check(RepoCheckRequest(repo="/repo"))

    assert not result.all_passed
    assert len(result.checks) == 1
    assert result.checks[0].name == "format"


def test_invalid_repo_format_too_many_slashes() -> None:
    """Repo with multiple slashes returns format error."""
    result = run_repo_check(RepoCheckRequest(repo="a/b/c"))

    assert not result.all_passed
    assert len(result.checks) == 1
    assert result.checks[0].name == "format"


@patch("erk.cli.commands.repo.check.checks.subprocess.run")
def test_all_checks_pass(mock_run: object) -> None:
    """When all gh api calls succeed, all checks pass."""
    mock_run.side_effect = _all_pass_side_effect()  # type: ignore[attr-defined]

    result = run_repo_check(RepoCheckRequest(repo="myorg/myrepo"))

    assert result.all_passed
    assert result.repo == "myorg/myrepo"
    assert len(result.checks) > 0
    for item in result.checks:
        assert item.passed, f"Expected pass for {item.name}: {item.message}"


@patch("erk.cli.commands.repo.check.checks.subprocess.run")
def test_all_checks_fail(mock_run: object) -> None:
    """When all gh api calls return 404, all checks fail."""
    mock_run.side_effect = _all_fail_side_effect()  # type: ignore[attr-defined]

    result = run_repo_check(RepoCheckRequest(repo="myorg/myrepo"))

    assert not result.all_passed
    for item in result.checks:
        assert not item.passed, f"Expected fail for {item.name}: {item.message}"
        if item.remediation is not None:
            assert len(item.remediation) > 0


@patch("erk.cli.commands.repo.check.checks.subprocess.run")
def test_checks_include_workflows(mock_run: object) -> None:
    """Checks include all expected workflow files."""
    mock_run.side_effect = _all_pass_side_effect()  # type: ignore[attr-defined]

    result = run_repo_check(RepoCheckRequest(repo="myorg/myrepo"))

    workflow_names = {item.name for item in result.checks if item.name.startswith("workflow:")}
    assert "workflow:plan-implement.yml" in workflow_names
    assert "workflow:pr-rebase.yml" in workflow_names
    assert "workflow:pr-address.yml" in workflow_names
    assert "workflow:one-shot.yml" in workflow_names
    assert "workflow:learn.yml" in workflow_names


@patch("erk.cli.commands.repo.check.checks.subprocess.run")
def test_checks_include_secrets(mock_run: object) -> None:
    """Checks include all required secrets."""
    mock_run.side_effect = _all_pass_side_effect()  # type: ignore[attr-defined]

    result = run_repo_check(RepoCheckRequest(repo="myorg/myrepo"))

    secret_names = {item.name for item in result.checks if item.name.startswith("secret:")}
    assert "secret:ERK_QUEUE_GH_PAT" in secret_names
    assert "secret:ANTHROPIC_API_KEY" in secret_names
    assert "secret:CLAUDE_CODE_OAUTH_TOKEN" in secret_names


@patch("erk.cli.commands.repo.check.checks.subprocess.run")
def test_checks_include_labels(mock_run: object) -> None:
    """Checks include erk label checks."""
    mock_run.side_effect = _all_pass_side_effect()  # type: ignore[attr-defined]

    result = run_repo_check(RepoCheckRequest(repo="myorg/myrepo"))

    label_names = {item.name for item in result.checks if item.name.startswith("label:")}
    assert "label:erk-pr" in label_names
    assert "label:erk-objective" in label_names


@patch("erk.cli.commands.repo.check.checks.subprocess.run")
def test_checks_include_permissions(mock_run: object) -> None:
    """Checks include workflow permissions check."""
    mock_run.side_effect = _all_pass_side_effect()  # type: ignore[attr-defined]

    result = run_repo_check(RepoCheckRequest(repo="myorg/myrepo"))

    perm_names = {item.name for item in result.checks if item.name.startswith("permissions:")}
    assert "permissions:can_approve_pull_request_reviews" in perm_names


@patch("erk.cli.commands.repo.check.checks.subprocess.run")
def test_checks_include_variable(mock_run: object) -> None:
    """Checks include CLAUDE_ENABLED variable check."""
    mock_run.side_effect = _all_pass_side_effect()  # type: ignore[attr-defined]

    result = run_repo_check(RepoCheckRequest(repo="myorg/myrepo"))

    var_names = {item.name for item in result.checks if item.name.startswith("variable:")}
    assert "variable:CLAUDE_ENABLED" in var_names


@patch("erk.cli.commands.repo.check.checks.subprocess.run")
def test_to_json_dict(mock_run: object) -> None:
    """to_json_dict produces expected structure."""
    mock_run.side_effect = _all_pass_side_effect()  # type: ignore[attr-defined]

    result = run_repo_check(RepoCheckRequest(repo="myorg/myrepo"))
    json_dict = result.to_json_dict()

    assert json_dict["repo"] == "myorg/myrepo"
    assert json_dict["all_passed"] is True
    assert isinstance(json_dict["checks"], list)
    assert len(json_dict["checks"]) > 0
    first = json_dict["checks"][0]
    assert "name" in first
    assert "passed" in first
    assert "message" in first
    assert "remediation" in first


@patch("erk.cli.commands.repo.check.checks.subprocess.run")
def test_mixed_results(mock_run: object) -> None:
    """Some checks pass and some fail."""

    def side_effect(
        cmd: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        joined = " ".join(cmd)
        # Workflows pass
        if "contents/.github/workflows/" in joined:
            return _make_subprocess_result(returncode=0, stdout="{}")
        # Secrets fail
        if "actions/secrets/" in joined:
            return _make_subprocess_result(returncode=1, stderr="HTTP 404: Not Found")
        # Variable not set (pass)
        if "variable" in cmd and "get" in cmd:
            return _make_subprocess_result(returncode=1, stderr="variable not found")
        # Permissions pass
        if "actions/permissions/workflow" in joined:
            return _make_subprocess_result(
                returncode=0,
                stdout='{"can_approve_pull_request_reviews": true}',
            )
        # Labels pass
        if "labels/" in joined:
            return _make_subprocess_result(returncode=0, stdout="{}")
        return _make_subprocess_result(returncode=0, stdout="{}")

    mock_run.side_effect = side_effect  # type: ignore[attr-defined]

    result = run_repo_check(RepoCheckRequest(repo="myorg/myrepo"))

    assert not result.all_passed
    passed = [item for item in result.checks if item.passed]
    failed = [item for item in result.checks if not item.passed]
    assert len(passed) > 0
    assert len(failed) > 0
    # All failures should be secrets
    for item in failed:
        assert item.name.startswith("secret:")


def test_result_all_passed_property() -> None:
    """RepoCheckResult.all_passed property works correctly."""
    from erk.cli.commands.repo.check.checks import RepoCheckItem

    all_pass = RepoCheckResult(
        repo="a/b",
        checks=(
            RepoCheckItem(name="x", passed=True, message="ok", remediation=None),
            RepoCheckItem(name="y", passed=True, message="ok", remediation=None),
        ),
    )
    assert all_pass.all_passed

    one_fail = RepoCheckResult(
        repo="a/b",
        checks=(
            RepoCheckItem(name="x", passed=True, message="ok", remediation=None),
            RepoCheckItem(name="y", passed=False, message="bad", remediation="fix it"),
        ),
    )
    assert not one_fail.all_passed

    empty = RepoCheckResult(repo="a/b", checks=())
    assert empty.all_passed
