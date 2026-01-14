"""Tests for GitHub GraphQL operations with mocked subprocess execution.

These tests verify that RealGitHub correctly passes GraphQL variables using
the gh CLI's special array and object syntax.
"""

import json
import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from erk_shared.github.real import RealGitHub
from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation
from tests.integration.test_helpers import mock_subprocess_run


def test_get_issues_with_pr_linkages_uses_gh_array_syntax_for_labels(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that get_issues_with_pr_linkages uses gh's array syntax for labels.

    Per gh api --help:
    - Arrays must use key[]=value1 -f key[]=value2 syntax
    - NOT -F key=["value1", "value2"] (which passes as literal string)
    """
    created_commands: list[list[str]] = []

    graphql_response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(graphql_response),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        github = RealGitHub.for_test()
        location = GitHubRepoLocation(
            root=Path("/repo"),
            repo_id=GitHubRepoId(owner="dagster-io", repo="erk"),
        )

        github.get_issues_with_pr_linkages(
            location=location,
            labels=["erk-plan"],
            state="OPEN",
        )

        assert len(created_commands) == 1
        cmd = created_commands[0]

        # Verify labels uses array syntax: -f labels[]=erk-plan
        # Find the labels array argument
        labels_found = False
        for arg in cmd:
            if arg == "labels[]=erk-plan":
                labels_found = True
                break

        assert labels_found, (
            f"labels should use array syntax labels[]=value, "
            f"but got: {[a for a in cmd if 'labels' in a]}"
        )


def test_get_issues_with_pr_linkages_uses_gh_array_syntax_for_states(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that get_issues_with_pr_linkages uses gh's array syntax for states."""
    created_commands: list[list[str]] = []

    graphql_response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(graphql_response),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        github = RealGitHub.for_test()
        location = GitHubRepoLocation(
            root=Path("/repo"),
            repo_id=GitHubRepoId(owner="dagster-io", repo="erk"),
        )

        github.get_issues_with_pr_linkages(
            location=location,
            labels=["erk-plan"],
            state="OPEN",
        )

        assert len(created_commands) == 1
        cmd = created_commands[0]

        # Verify states uses array syntax: -f states[]=OPEN
        states_found = False
        for arg in cmd:
            if arg == "states[]=OPEN":
                states_found = True
                break

        assert states_found, (
            f"states should use array syntax states[]=value, "
            f"but got: {[a for a in cmd if 'states' in a]}"
        )


def test_get_issues_with_pr_linkages_uses_gh_object_syntax_for_filterby(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that get_issues_with_pr_linkages uses gh's object syntax for filterBy.

    Per gh api --help:
    - Objects must use key[subkey]=value syntax
    - NOT -F key={"subkey": "value"} (which passes as literal string)
    """
    created_commands: list[list[str]] = []

    graphql_response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(graphql_response),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        github = RealGitHub.for_test()
        location = GitHubRepoLocation(
            root=Path("/repo"),
            repo_id=GitHubRepoId(owner="dagster-io", repo="erk"),
        )

        github.get_issues_with_pr_linkages(
            location=location,
            labels=["erk-plan"],
            creator="testuser",  # This triggers filterBy variable
        )

        assert len(created_commands) == 1
        cmd = created_commands[0]

        # Verify filterBy uses object syntax: -f filterBy[createdBy]=testuser
        filterby_found = False
        for arg in cmd:
            if arg == "filterBy[createdBy]=testuser":
                filterby_found = True
                break

        assert filterby_found, (
            f"filterBy should use object syntax filterBy[createdBy]=value, "
            f"but got: {[a for a in cmd if 'filterBy' in a]}"
        )


def test_get_issues_with_pr_linkages_uses_string_flags_for_strings(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that string variables (owner, repo, query) correctly use -f."""
    created_commands: list[list[str]] = []

    graphql_response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(graphql_response),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        github = RealGitHub.for_test()
        location = GitHubRepoLocation(
            root=Path("/repo"),
            repo_id=GitHubRepoId(owner="dagster-io", repo="erk"),
        )

        github.get_issues_with_pr_linkages(
            location=location,
            labels=["erk-plan"],
        )

        assert len(created_commands) == 1
        cmd = created_commands[0]

        # Find owner and repo variables - these should use -f (strings)
        owner_idx = None
        repo_idx = None
        for i, arg in enumerate(cmd):
            if arg.startswith("owner="):
                owner_idx = i - 1
            if arg.startswith("repo=") and "repo_id" not in arg:
                repo_idx = i - 1

        assert owner_idx is not None, "owner variable not found"
        assert repo_idx is not None, "repo variable not found"

        # String values should use -f
        assert cmd[owner_idx] == "-f", f"owner should use -f, but used {cmd[owner_idx]}"
        assert cmd[repo_idx] == "-f", f"repo should use -f, but used {cmd[repo_idx]}"


def test_get_issues_with_pr_linkages_uses_typed_flag_for_first(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that the 'first' parameter uses -F for integer type conversion."""
    created_commands: list[list[str]] = []

    graphql_response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(graphql_response),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        github = RealGitHub.for_test()
        location = GitHubRepoLocation(
            root=Path("/repo"),
            repo_id=GitHubRepoId(owner="dagster-io", repo="erk"),
        )

        github.get_issues_with_pr_linkages(
            location=location,
            labels=["erk-plan"],
            limit=50,
        )

        assert len(created_commands) == 1
        cmd = created_commands[0]

        # Find first variable - should use -F for integer
        first_idx = None
        for i, arg in enumerate(cmd):
            if arg.startswith("first="):
                first_idx = i - 1
                break

        assert first_idx is not None, "first variable not found"
        assert cmd[first_idx] == "-F", f"first should use -F, but used {cmd[first_idx]}"


def test_get_issues_with_pr_linkages_handles_multiple_labels(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that multiple labels are each passed with separate array syntax."""
    created_commands: list[list[str]] = []

    graphql_response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(graphql_response),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        github = RealGitHub.for_test()
        location = GitHubRepoLocation(
            root=Path("/repo"),
            repo_id=GitHubRepoId(owner="dagster-io", repo="erk"),
        )

        github.get_issues_with_pr_linkages(
            location=location,
            labels=["erk-plan", "bug"],
        )

        assert len(created_commands) == 1
        cmd = created_commands[0]

        # Verify each label is passed separately with array syntax
        label_args = [a for a in cmd if a.startswith("labels[]=")]
        assert len(label_args) == 2, f"Expected 2 label args, got {label_args}"
        assert "labels[]=erk-plan" in label_args
        assert "labels[]=bug" in label_args
