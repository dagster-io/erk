"""Tests for GitHub operations."""

import pytest
from erk_shared.github.parsing import _parse_github_pr_url, extract_owner_repo_from_github_url
from erk_shared.integrations.time.fake import FakeTime

from erk.core.github.real import RealGitHub


def test_parse_github_pr_url_valid_urls() -> None:
    """Test parsing of valid GitHub PR URLs."""
    # Standard format
    result = _parse_github_pr_url("https://github.com/dagster-io/erk/pull/23")
    assert result == ("dagster-io", "erk")

    # Different owner/repo names
    result = _parse_github_pr_url("https://github.com/facebook/react/pull/12345")
    assert result == ("facebook", "react")

    # Single character names
    result = _parse_github_pr_url("https://github.com/a/b/pull/1")
    assert result == ("a", "b")

    # Names with hyphens
    result = _parse_github_pr_url("https://github.com/my-org/my-repo/pull/456")
    assert result == ("my-org", "my-repo")

    # Names with underscores
    result = _parse_github_pr_url("https://github.com/my_org/my_repo/pull/789")
    assert result == ("my_org", "my_repo")

    # Repo names with dots (valid in GitHub)
    result = _parse_github_pr_url("https://github.com/owner/repo.name/pull/100")
    assert result == ("owner", "repo.name")


def test_parse_github_pr_url_invalid_urls() -> None:
    """Test that invalid URLs return None."""
    # Not a GitHub URL
    assert _parse_github_pr_url("https://gitlab.com/owner/repo/pull/123") is None

    # Missing pull number
    assert _parse_github_pr_url("https://github.com/owner/repo/pull/") is None

    # Wrong path structure
    assert _parse_github_pr_url("https://github.com/owner/repo/issues/123") is None

    # Not a URL
    assert _parse_github_pr_url("not a url") is None

    # Empty string
    assert _parse_github_pr_url("") is None

    # Missing repo
    assert _parse_github_pr_url("https://github.com/owner/pull/123") is None


def test_parse_github_pr_url_edge_cases() -> None:
    """Test edge cases in URL parsing.

    Note: The regex is intentionally permissive about trailing content (query params,
    fragments, extra path segments) since it only needs to extract owner/repo from
    GitHub PR URLs returned by gh CLI, which are well-formed.
    """
    # PR number with leading zeros (valid)
    result = _parse_github_pr_url("https://github.com/owner/repo/pull/007")
    assert result == ("owner", "repo")

    # Very long PR number
    result = _parse_github_pr_url("https://github.com/owner/repo/pull/999999999")
    assert result == ("owner", "repo")

    # URL with query parameters (accepted - regex is permissive)
    result = _parse_github_pr_url("https://github.com/owner/repo/pull/123?tab=files")
    assert result == ("owner", "repo")

    # URL with fragment (accepted - regex is permissive)
    result = _parse_github_pr_url("https://github.com/owner/repo/pull/123#discussion")
    assert result == ("owner", "repo")

    # URL with extra path segments (accepted - regex is permissive)
    result = _parse_github_pr_url("https://github.com/owner/repo/pull/123/files")
    assert result == ("owner", "repo")


def test_extract_owner_repo_from_github_url_valid_urls() -> None:
    """Test extraction of owner/repo from various GitHub URLs."""
    # Issue URL
    result = extract_owner_repo_from_github_url("https://github.com/dagster-io/erk/issues/23")
    assert result == ("dagster-io", "erk")

    # PR URL
    result = extract_owner_repo_from_github_url("https://github.com/facebook/react/pull/12345")
    assert result == ("facebook", "react")

    # Repository URL without trailing path
    result = extract_owner_repo_from_github_url("https://github.com/owner/repo")
    assert result == ("owner", "repo")

    # Repository URL with trailing slash
    result = extract_owner_repo_from_github_url("https://github.com/owner/repo/")
    assert result == ("owner", "repo")


def test_extract_owner_repo_from_github_url_invalid_urls() -> None:
    """Test that invalid URLs return None."""
    # Not a GitHub URL
    assert extract_owner_repo_from_github_url("https://gitlab.com/owner/repo") is None

    # Not a URL
    assert extract_owner_repo_from_github_url("not a url") is None

    # Empty string
    assert extract_owner_repo_from_github_url("") is None

    # Just github.com
    assert extract_owner_repo_from_github_url("https://github.com") is None

    # Only owner, no repo
    assert extract_owner_repo_from_github_url("https://github.com/owner") is None


def test_build_batch_pr_query_uses_aggregated_count_fields() -> None:
    """Test that GraphQL query uses pre-aggregated count fields for efficiency.

    The query should use contexts(last: 1) with totalCount, checkRunCountsByState,
    and statusContextCountsByState instead of fetching up to 100 individual nodes.
    This reduces payload size by ~15-30x while maintaining identical functionality.
    """
    ops = RealGitHub(FakeTime())

    query = ops._build_batch_pr_query([123], "owner", "repo")

    # Critical: contexts should use aggregated count fields, not nodes with inline fragments
    assert "contexts(last: 1) {" in query  # Only need 1 for metadata
    assert "totalCount" in query
    assert "checkRunCountsByState" in query
    assert "statusContextCountsByState" in query

    # Should NOT have the old inefficient patterns
    assert "contexts(last: 100)" not in query
    assert "... on StatusContext" not in query
    assert "... on CheckRun" not in query


def test_build_batch_pr_query_structure() -> None:
    """Test that GraphQL query has correct overall structure with named fragments."""
    ops = RealGitHub(FakeTime())

    query = ops._build_batch_pr_query([123, 456], "test-owner", "test-repo")

    # Validate fragment definition is present
    assert "fragment PRCICheckFields on PullRequest {" in query

    # Validate basic GraphQL syntax
    assert "query {" in query
    assert 'repository(owner: "test-owner", name: "test-repo")' in query

    # Validate PR aliases are present with fragment spread
    assert "pr_123: pullRequest(number: 123) {" in query
    assert "pr_456: pullRequest(number: 456) {" in query
    assert "...PRCICheckFields" in query

    # Validate required fields are in the fragment definition (only once)
    assert query.count("commits(last: 1)") == 1  # Only in fragment definition
    assert query.count("statusCheckRollup") == 1  # Only in fragment definition

    # Validate aggregated count fields (new efficient pattern)
    assert "totalCount" in query
    assert "checkRunCountsByState" in query
    assert "statusContextCountsByState" in query
    assert "state" in query  # statusCheckRollup state field

    # Validate fragment spread is used for each PR
    assert query.count("...PRCICheckFields") == 2  # One for each PR


def test_build_batch_pr_query_multiple_prs() -> None:
    """Test that query correctly handles multiple PRs with unique aliases and fragments."""
    ops = RealGitHub(FakeTime())

    pr_numbers = [100, 200, 300]
    query = ops._build_batch_pr_query(pr_numbers, "owner", "repo")

    # Each PR should have a unique alias
    for pr_num in pr_numbers:
        alias = f"pr_{pr_num}: pullRequest(number: {pr_num})"
        assert alias in query

    # Verify all PRs are in the same repository query
    assert query.count('repository(owner: "owner", name: "repo")') == 1

    # With fragments, the structure is defined once in the fragment definition
    assert query.count("commits(last: 1)") == 1  # Only in fragment definition
    assert query.count("statusCheckRollup") == 1  # Only in fragment definition
    assert query.count("totalCount") == 1  # Only in fragment definition
    assert query.count("checkRunCountsByState") == 1  # Only in fragment definition

    # Each PR should use the fragment spread
    assert query.count("...PRCICheckFields") == len(pr_numbers)


def test_parse_pr_ci_status_handles_invalid_contexts_type() -> None:
    """Test that parser handles invalid contexts type gracefully.

    This tests that the parser correctly handles the case where the contexts
    field is a list instead of a dict (e.g., if the API response format changes).
    """
    ops = RealGitHub(FakeTime())

    # Simulate response with contexts as a list (invalid structure)
    invalid_response = {
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "statusCheckRollup": {
                            "contexts": [  # Direct array, should be dict
                                {"state": "SUCCESS", "count": 1}
                            ]
                        }
                    }
                }
            ]
        }
    }

    # Parser should handle this gracefully and return None
    result = ops._parse_pr_ci_status(invalid_response)
    assert result is None


def test_parse_pr_ci_status_with_correct_structure() -> None:
    """Test that parser correctly handles the expected GraphQL response structure."""
    ops = RealGitHub(FakeTime())

    # Simulate correct response structure with aggregated count fields
    correct_response = {
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "statusCheckRollup": {
                            "state": "SUCCESS",
                            "contexts": {
                                "totalCount": 3,
                                "checkRunCountsByState": [
                                    {"state": "SUCCESS", "count": 2},
                                ],
                                "statusContextCountsByState": [
                                    {"state": "SUCCESS", "count": 1},
                                ],
                            },
                        }
                    }
                }
            ]
        }
    }

    # Parser should successfully extract and parse CI status
    result = ops._parse_pr_ci_status(correct_response)
    assert result is True  # All checks passing (3/3)


def test_parse_pr_ci_status_with_failing_checks() -> None:
    """Test that parser correctly identifies failing checks."""
    ops = RealGitHub(FakeTime())

    response = {
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "statusCheckRollup": {
                            "state": "FAILURE",
                            "contexts": {
                                "totalCount": 3,
                                "checkRunCountsByState": [
                                    {"state": "SUCCESS", "count": 1},
                                    {"state": "FAILURE", "count": 2},
                                ],
                                "statusContextCountsByState": [],
                            },
                        }
                    }
                }
            ]
        }
    }

    # Parser should detect failing check (1/3 passing)
    result = ops._parse_pr_ci_status(response)
    assert result is False


def test_parse_pr_ci_status_with_pending_checks() -> None:
    """Test that parser correctly identifies pending/in-progress checks."""
    ops = RealGitHub(FakeTime())

    response = {
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "statusCheckRollup": {
                            "state": "PENDING",
                            "contexts": {
                                "totalCount": 2,
                                "checkRunCountsByState": [
                                    {"state": "IN_PROGRESS", "count": 1},
                                    {"state": "SUCCESS", "count": 1},
                                ],
                                "statusContextCountsByState": [],
                            },
                        }
                    }
                }
            ]
        }
    }

    # Parser should detect incomplete check (1/2 passing)
    result = ops._parse_pr_ci_status(response)
    assert result is False


def test_build_title_batch_query_structure() -> None:
    """Test that title query has correct structure with only number and title fields."""
    ops = RealGitHub(FakeTime())

    query = ops._build_title_batch_query([123, 456], "test-owner", "test-repo")

    # Validate basic GraphQL syntax
    assert "query {" in query
    assert 'repository(owner: "test-owner", name: "test-repo")' in query

    # Validate PR aliases are present
    assert "pr_123: pullRequest(number: 123) {" in query
    assert "pr_456: pullRequest(number: 456) {" in query

    # Validate required fields (number and title only)
    assert "number" in query
    assert "title" in query

    # Verify query does NOT include CI fields
    assert "statusCheckRollup" not in query
    assert "mergeable" not in query
    assert "mergeStateStatus" not in query
    assert "commits(last: 1)" not in query
    assert "contexts" not in query


def test_fetch_pr_titles_batch_enriches_titles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fetch_pr_titles_batch enriches PRs with titles from GraphQL response."""
    ops = RealGitHub(FakeTime())

    # Create input PRs without titles
    from pathlib import Path

    from erk_shared.github.types import PullRequestInfo

    prs = {
        "feature-1": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/test-owner/test-repo/pull/123",
            is_draft=False,
            title=None,  # No title initially
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        ),
        "feature-2": PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/test-owner/test-repo/pull/456",
            is_draft=False,
            title=None,  # No title initially
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        ),
    }

    # Mock GraphQL response with titles
    mock_response = {
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "title": "Add new feature",
                },
                "pr_456": {
                    "number": 456,
                    "title": "Fix bug",
                },
            }
        }
    }

    # Mock _execute_batch_pr_query to return our response
    monkeypatch.setattr(ops, "_execute_batch_pr_query", lambda query, repo_root: mock_response)

    # Execute
    result = ops.fetch_pr_titles_batch(prs, Path("/repo"))

    # Verify PRs are enriched with titles
    assert result["feature-1"].title == "Add new feature"
    assert result["feature-2"].title == "Fix bug"
    # Verify other fields are preserved
    assert result["feature-1"].number == 123
    assert result["feature-2"].number == 456


def test_fetch_pr_titles_batch_empty_input() -> None:
    """Test fetch_pr_titles_batch returns empty dict for empty input."""
    ops = RealGitHub(FakeTime())

    from pathlib import Path

    # Call with empty dict
    result = ops.fetch_pr_titles_batch({}, Path("/repo"))

    # Should return empty dict immediately without API call
    assert result == {}


def test_fetch_pr_titles_batch_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fetch_pr_titles_batch handles partial failures gracefully."""
    ops = RealGitHub(FakeTime())

    from pathlib import Path

    from erk_shared.github.types import PullRequestInfo

    # Create input PRs
    prs = {
        "feature-1": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/test-owner/test-repo/pull/123",
            is_draft=False,
            title=None,
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        ),
        "feature-2": PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/test-owner/test-repo/pull/456",
            is_draft=False,
            title=None,
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        ),
    }

    # Mock GraphQL response with one PR present, one missing (None)
    mock_response = {
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "title": "Add new feature",
                },
                "pr_456": None,  # PR not found or error
            }
        }
    }

    monkeypatch.setattr(ops, "_execute_batch_pr_query", lambda query, repo_root: mock_response)

    result = ops.fetch_pr_titles_batch(prs, Path("/repo"))

    # Successful PR should have title
    assert result["feature-1"].title == "Add new feature"
    # Failed PR should have None title
    assert result["feature-2"].title is None


def test_fetch_pr_titles_batch_missing_title_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fetch_pr_titles_batch handles missing title field gracefully."""
    ops = RealGitHub(FakeTime())

    from pathlib import Path

    from erk_shared.github.types import PullRequestInfo

    # Create input PR
    prs = {
        "feature": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/test-owner/test-repo/pull/123",
            is_draft=False,
            title=None,
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        ),
    }

    # Mock GraphQL response with PR data but missing title field
    mock_response = {
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    # title field is missing
                },
            }
        }
    }

    monkeypatch.setattr(ops, "_execute_batch_pr_query", lambda query, repo_root: mock_response)

    result = ops.fetch_pr_titles_batch(prs, Path("/repo"))

    # Should handle missing field gracefully and set title=None
    assert result["feature"].title is None
    assert result["feature"].number == 123


def test_build_issue_pr_linkage_query_structure() -> None:
    """Test that issue-PR linkage query uses timeline API with CrossReferencedEvent."""
    ops = RealGitHub(FakeTime())

    query = ops._build_issue_pr_linkage_query([100, 200], "test-owner", "test-repo")

    # Validate basic GraphQL syntax
    assert "query {" in query
    assert 'repository(owner: "test-owner", name: "test-repo")' in query

    # Validate we're using timeline approach (not pullRequests)
    assert "pullRequests(" not in query
    assert "closingIssuesReferences(" not in query

    # Validate aliased issue queries
    assert "issue_100: issue(number: 100)" in query
    assert "issue_200: issue(number: 200)" in query

    # Validate timeline items with CrossReferencedEvent
    assert "timelineItems(itemTypes: [CROSS_REFERENCED_EVENT]" in query
    assert "willCloseTarget" in query

    # Validate PR fields within source
    assert "source {" in query
    assert "... on PullRequest {" in query
    assert "number" in query
    assert "state" in query
    assert "url" in query
    assert "isDraft" in query
    assert "statusCheckRollup" in query
    assert "mergeable" in query

    # Validate aggregated check count fields are used (efficiency optimization)
    assert "contexts(last: 1)" in query
    assert "totalCount" in query
    assert "checkRunCountsByState" in query
    assert "statusContextCountsByState" in query

    # Validate inefficient patterns are NOT used
    assert "contexts(last: 100)" not in query
    assert "... on StatusContext" not in query
    assert "... on CheckRun" not in query

    # Validate title is NOT fetched (not displayed in dash)
    assert "title" not in query

    # Validate labels is NOT fetched (no longer needed)
    assert "labels" not in query


def test_parse_issue_pr_linkages_with_single_pr() -> None:
    """Test parsing GraphQL timeline response with single PR closing an issue."""
    ops = RealGitHub(FakeTime())

    # Timeline response with PR closing issue 100 (uses aggregated check counts)
    response = {
        "data": {
            "repository": {
                "issue_100": {
                    "timelineItems": {
                        "nodes": [
                            {
                                "willCloseTarget": True,
                                "source": {
                                    "number": 200,
                                    "state": "OPEN",
                                    "url": "https://github.com/owner/repo/pull/200",
                                    "isDraft": False,
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "statusCheckRollup": {
                                        "state": "SUCCESS",
                                        "contexts": {
                                            "totalCount": 3,
                                            "checkRunCountsByState": [
                                                {"state": "SUCCESS", "count": 3}
                                            ],
                                            "statusContextCountsByState": [],
                                        },
                                    },
                                    "mergeable": "MERGEABLE",
                                },
                            }
                        ]
                    }
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should have one issue with one PR
    assert 100 in result
    assert len(result[100]) == 1

    pr = result[100][0]
    assert pr.number == 200
    assert pr.state == "OPEN"
    assert pr.url == "https://github.com/owner/repo/pull/200"
    assert pr.is_draft is False
    assert pr.title is None  # Not fetched for efficiency
    assert pr.checks_passing is True
    assert pr.has_conflicts is False
    assert pr.checks_counts == (3, 3)  # Aggregated counts


def test_parse_issue_pr_linkages_with_multiple_prs() -> None:
    """Test parsing timeline response with multiple PRs closing same issue."""
    ops = RealGitHub(FakeTime())

    # Timeline response with two PRs closing issue 100 (aggregated format)
    response = {
        "data": {
            "repository": {
                "issue_100": {
                    "timelineItems": {
                        "nodes": [
                            {
                                "willCloseTarget": True,
                                "source": {
                                    "number": 201,
                                    "state": "OPEN",
                                    "url": "https://github.com/owner/repo/pull/201",
                                    "isDraft": False,
                                    "createdAt": "2024-01-02T00:00:00Z",
                                    "statusCheckRollup": None,
                                    "mergeable": "UNKNOWN",
                                },
                            },
                            {
                                "willCloseTarget": True,
                                "source": {
                                    "number": 200,
                                    "state": "CLOSED",
                                    "url": "https://github.com/owner/repo/pull/200",
                                    "isDraft": False,
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "statusCheckRollup": {"state": "FAILURE"},
                                    "mergeable": "MERGEABLE",
                                },
                            },
                        ]
                    }
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should have one issue with two PRs, sorted by created_at descending
    assert 100 in result
    assert len(result[100]) == 2

    # Most recent PR should be first
    assert result[100][0].number == 201
    assert result[100][0].title is None  # Not fetched for efficiency

    # Older PR should be second
    assert result[100][1].number == 200
    assert result[100][1].title is None  # Not fetched for efficiency


def test_parse_issue_pr_linkages_with_pr_linking_multiple_issues() -> None:
    """Test parsing timeline response where same PR closes multiple issues."""
    ops = RealGitHub(FakeTime())

    # Timeline response with same PR closing both issues 100 and 101 (aggregated format)
    response = {
        "data": {
            "repository": {
                "issue_100": {
                    "timelineItems": {
                        "nodes": [
                            {
                                "willCloseTarget": True,
                                "source": {
                                    "number": 200,
                                    "state": "OPEN",
                                    "url": "https://github.com/owner/repo/pull/200",
                                    "isDraft": False,
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "statusCheckRollup": {"state": "SUCCESS"},
                                    "mergeable": "MERGEABLE",
                                },
                            }
                        ]
                    }
                },
                "issue_101": {
                    "timelineItems": {
                        "nodes": [
                            {
                                "willCloseTarget": True,
                                "source": {
                                    "number": 200,
                                    "state": "OPEN",
                                    "url": "https://github.com/owner/repo/pull/200",
                                    "isDraft": False,
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "statusCheckRollup": {"state": "SUCCESS"},
                                    "mergeable": "MERGEABLE",
                                },
                            }
                        ]
                    }
                },
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should have two issues, each with the same PR
    assert 100 in result
    assert 101 in result
    assert len(result[100]) == 1
    assert len(result[101]) == 1

    # Both should point to same PR
    assert result[100][0].number == 200
    assert result[101][0].number == 200


def test_parse_issue_pr_linkages_handles_empty_timeline() -> None:
    """Test parsing handles issues with no cross-reference events."""
    ops = RealGitHub(FakeTime())

    # Timeline response with empty timeline (no PRs reference this issue)
    response = {
        "data": {
            "repository": {
                "issue_100": {
                    "timelineItems": {
                        "nodes": []  # Empty - no cross-references
                    }
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Issue with no PRs should not appear in result
    assert 100 not in result
    assert result == {}


def test_parse_issue_pr_linkages_handles_null_nodes() -> None:
    """Test parsing handles null values in timeline nodes gracefully."""
    ops = RealGitHub(FakeTime())

    # Timeline response with null nodes and null source (aggregated format)
    response = {
        "data": {
            "repository": {
                "issue_100": {
                    "timelineItems": {
                        "nodes": [
                            None,  # Null event node
                            {
                                "willCloseTarget": True,
                                "source": None,  # Null source
                            },
                            {
                                "willCloseTarget": True,
                                "source": {
                                    "number": 200,
                                    "state": "OPEN",
                                    "url": "https://github.com/owner/repo/pull/200",
                                    "isDraft": False,
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "statusCheckRollup": None,
                                    "mergeable": "MERGEABLE",
                                },
                            },
                        ]
                    }
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should skip null nodes and process valid ones
    assert 100 in result
    assert len(result[100]) == 1
    assert result[100][0].number == 200


def test_parse_issue_pr_linkages_handles_missing_optional_fields() -> None:
    """Test parsing handles missing optional fields (checks, conflicts)."""
    ops = RealGitHub(FakeTime())

    # Timeline response with minimal fields in PR source (aggregated format)
    response = {
        "data": {
            "repository": {
                "issue_100": {
                    "timelineItems": {
                        "nodes": [
                            {
                                "willCloseTarget": True,
                                "source": {
                                    "number": 200,
                                    "state": "MERGED",
                                    "url": "https://github.com/owner/repo/pull/200",
                                    "isDraft": None,  # Missing
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "statusCheckRollup": None,  # No checks
                                    "mergeable": None,  # Unknown
                                },
                            }
                        ]
                    }
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should handle missing fields gracefully
    assert 100 in result
    pr = result[100][0]
    assert pr.number == 200
    assert pr.is_draft is False  # Defaults to False
    assert pr.title is None  # Not fetched for efficiency
    assert pr.checks_passing is None
    assert pr.has_conflicts is None


def test_parse_issue_pr_linkages_filters_non_closing_prs() -> None:
    """Test parsing filters out PRs that don't close the issue (willCloseTarget=false)."""
    ops = RealGitHub(FakeTime())

    # Timeline response with PRs that mention but don't close the issue (aggregated format)
    response = {
        "data": {
            "repository": {
                "issue_100": {
                    "timelineItems": {
                        "nodes": [
                            {
                                "willCloseTarget": False,  # Just mentions, doesn't close
                                "source": {
                                    "number": 201,
                                    "state": "OPEN",
                                    "url": "https://github.com/owner/repo/pull/201",
                                    "isDraft": False,
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "statusCheckRollup": None,
                                    "mergeable": "MERGEABLE",
                                },
                            },
                            {
                                "willCloseTarget": True,  # Will close the issue
                                "source": {
                                    "number": 200,
                                    "state": "OPEN",
                                    "url": "https://github.com/owner/repo/pull/200",
                                    "isDraft": False,
                                    "createdAt": "2024-01-02T00:00:00Z",
                                    "statusCheckRollup": None,
                                    "mergeable": "MERGEABLE",
                                },
                            },
                        ]
                    }
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should only include the closing PR
    assert 100 in result
    assert len(result[100]) == 1
    assert result[100][0].number == 200  # Only the closing PR


def test_parse_issue_pr_linkages_handles_issue_not_found() -> None:
    """Test parsing handles non-existent issue (null result)."""
    ops = RealGitHub(FakeTime())

    # Timeline response where one issue doesn't exist (aggregated format)
    response = {
        "data": {
            "repository": {
                "issue_100": None,  # Issue doesn't exist
                "issue_101": {
                    "timelineItems": {
                        "nodes": [
                            {
                                "willCloseTarget": True,
                                "source": {
                                    "number": 200,
                                    "state": "OPEN",
                                    "url": "https://github.com/owner/repo/pull/200",
                                    "isDraft": False,
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "statusCheckRollup": None,
                                    "mergeable": "MERGEABLE",
                                },
                            }
                        ]
                    }
                },
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Non-existent issue should be skipped
    assert 100 not in result
    # Valid issue should be processed
    assert 101 in result
    assert result[101][0].number == 200
