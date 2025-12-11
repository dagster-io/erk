"""Integration tests for GitHub GraphQL operations.

This tests the actual gh CLI invocation to ensure variable passing works correctly.
"""

from pathlib import Path

import pytest
from erk_shared.github.real import RealGitHub
from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation
from erk_shared.integrations.time.real import RealTime

pytestmark = pytest.mark.integration


def test_get_issues_with_pr_linkages_variable_passing():
    """Test that get_issues_with_pr_linkages passes GraphQL variables correctly.

    This is a regression test for the bug where -f flags were used instead of -F
    for JSON array/object variables, causing GraphQL type errors:

        Variable $states of type [IssueState!]! was provided invalid value for 0
        (Expected "[\"OPEN\"]" to be one of: OPEN, CLOSED)

    The bug was in real.py lines 1032-1035 and 1042 where -f was used for:
    - labels (should be -F for JSON array)
    - states (should be -F for JSON array)
    - filterBy (should be -F for JSON object)

    This test validates the fix by calling the actual gh CLI with real GitHub.
    It will fail if the variables are not passed correctly (using -f instead of -F).
    """
    github = RealGitHub(time=RealTime())

    # Use the actual erk repository (we're running in CI on this repo)
    # This test requires:
    # 1. gh CLI to be installed and authenticated
    # 2. Running in a git repository with GitHub remote
    # 3. Access to query GitHub issues

    # Create location for current repo
    location = GitHubRepoLocation(
        root=Path.cwd(),
        repo_id=GitHubRepoId(owner="dagster-io", repo="erk"),
    )

    # Call get_issues_with_pr_linkages - this will execute actual gh CLI command
    # If the bug exists (-f instead of -F), this will fail with GraphQL error
    issues, pr_linkages = github.get_issues_with_pr_linkages(
        location=location,
        labels=["erk-plan"],
        state="OPEN",
        creator=None,
        limit=5,
    )

    # If we get here without GraphQL errors, the variable passing works correctly
    # The actual content doesn't matter - we're testing command construction
    assert isinstance(issues, list)
    assert isinstance(pr_linkages, dict)

    # Also test with creator filter (filterBy JSON object)
    issues_with_creator, pr_linkages_creator = github.get_issues_with_pr_linkages(
        location=location,
        labels=["erk-plan"],
        state="OPEN",
        creator="schrockn",  # Test with a creator to verify filterBy works
        limit=5,
    )

    assert isinstance(issues_with_creator, list)
    assert isinstance(pr_linkages_creator, dict)
