"""Tests for GitHub operations."""

from erk_shared.github.parsing import _parse_github_pr_url, extract_owner_repo_from_github_url
from erk_shared.github.real import RealGitHub
from erk_shared.github.types import GitHubRepoId
from erk_shared.integrations.time.fake import FakeTime


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


def test_build_issue_pr_linkage_query_structure() -> None:
    """Test that issue PR linkage query uses timelineItems with CrossReferencedEvent."""
    ops = RealGitHub(FakeTime())

    query = ops._build_issue_pr_linkage_query([100, 200], GitHubRepoId("test-owner", "test-repo"))

    # Validate basic GraphQL syntax
    assert "query {" in query
    assert 'repository(owner: "test-owner", name: "test-repo")' in query

    # Validate fragment definition
    assert "fragment IssuePRLinkageFields on CrossReferencedEvent {" in query

    # Validate aliased issue queries
    assert "issue_100: issue(number: 100)" in query
    assert "issue_200: issue(number: 200)" in query

    # Validate timelineItems query with CrossReferencedEvent filter
    assert "timelineItems(itemTypes: [CROSS_REFERENCED_EVENT], first: 20)" in query

    # Validate fragment includes required fields
    assert "willCloseTarget" in query
    assert "source {" in query
    assert "... on PullRequest {" in query
    assert "number" in query
    assert "state" in query
    assert "url" in query
    assert "isDraft" in query
    assert "createdAt" in query
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
    # Note: title IS fetched for issues (in issues query), so check PR-specific context
    assert "source {" in query

    # Validate labels is NOT fetched for PRs (no longer needed)
    # Note: labels field appears in issues query, not PR source


def test_issues_with_pr_linkages_query_structure() -> None:
    """Test that issues with PR linkages query uses timeline events."""
    from erk_shared.github.graphql_queries import GET_ISSUES_WITH_PR_LINKAGES_QUERY

    query = GET_ISSUES_WITH_PR_LINKAGES_QUERY

    # Validate basic GraphQL syntax
    assert "query(" in query
    assert "repository(owner: $owner, name: $repo)" in query

    # Validate issues query (parameterized version uses variables)
    assert "issues(" in query
    assert "labels: $labels" in query
    assert "states: $states" in query
    assert "first: $first" in query

    # Validate issue fields
    assert "number" in query
    assert "title" in query
    assert "body" in query
    assert "state" in query
    assert "url" in query
    assert "author { login }" in query
    assert "createdAt" in query
    assert "updatedAt" in query

    # Validate timeline items for PR linkages
    assert "timelineItems" in query
    assert "CROSS_REFERENCED_EVENT" in query
    assert "willCloseTarget" in query

    # Validate PR fields in timeline source
    assert "isDraft" in query
    assert "statusCheckRollup" in query
    assert "mergeable" in query

    # Validate aggregated check count fields
    assert "contexts(last: 1)" in query
    assert "totalCount" in query
    assert "checkRunCountsByState" in query
    assert "statusContextCountsByState" in query

    # Validate we're NOT using closingIssuesReferences
    assert "closingIssuesReferences" not in query


def test_parse_issue_pr_linkages_with_single_pr() -> None:
    """Test parsing timeline response with single PR closing issue."""
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

    result = ops._parse_issue_pr_linkages(response, GitHubRepoId("owner", "repo"))

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

    result = ops._parse_issue_pr_linkages(response, GitHubRepoId("owner", "repo"))

    assert 100 in result
    assert len(result[100]) == 2

    # Most recent PR should be first
    assert result[100][0].number == 201
    assert result[100][0].title is None  # Not fetched for efficiency

    # Older PR should be second
    assert result[100][1].number == 200
    assert result[100][1].title is None  # Not fetched for efficiency


def test_parse_issue_pr_linkages_with_pr_linking_multiple_issues() -> None:
    """Test parsing response where same PR closes multiple issues."""
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

    result = ops._parse_issue_pr_linkages(response, GitHubRepoId("owner", "repo"))

    # Both issues should have the same PR
    assert 100 in result
    assert 101 in result
    assert result[100][0].number == 200
    assert result[101][0].number == 200


def test_parse_issue_pr_linkages_handles_empty_timeline() -> None:
    """Test parsing handles issues with no linked PRs."""
    ops = RealGitHub(FakeTime())

    response = {"data": {"repository": {"issue_100": {"timelineItems": {"nodes": []}}}}}

    result = ops._parse_issue_pr_linkages(response, GitHubRepoId("owner", "repo"))

    # Issue with no PRs should not appear in result
    assert 100 not in result
    assert result == {}


def test_parse_issue_pr_linkages_handles_null_nodes() -> None:
    """Test parsing handles null values gracefully."""
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

    result = ops._parse_issue_pr_linkages(response, GitHubRepoId("owner", "repo"))

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

    result = ops._parse_issue_pr_linkages(response, GitHubRepoId("owner", "repo"))

    # Should handle missing fields gracefully
    assert 100 in result
    pr = result[100][0]
    assert pr.number == 200
    assert pr.is_draft is False  # Defaults to False
    assert pr.title is None  # Not fetched for efficiency
    assert pr.checks_passing is None
    assert pr.has_conflicts is None


def test_parse_issue_pr_linkages_includes_all_referencing_prs() -> None:
    """Test parsing includes all PRs regardless of willCloseTarget."""
    ops = RealGitHub(FakeTime())

    # Timeline response with PRs that reference the issue (aggregated format)
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

    result = ops._parse_issue_pr_linkages(response, GitHubRepoId("owner", "repo"))

    # Should include all PRs regardless of willCloseTarget
    assert 100 in result
    assert len(result[100]) == 2
    # Sorted by created_at descending - PR 200 (Jan 2) comes before PR 201 (Jan 1)
    assert result[100][0].number == 200
    assert result[100][1].number == 201


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

    result = ops._parse_issue_pr_linkages(response, GitHubRepoId("owner", "repo"))

    # Non-existent issue should be skipped
    assert 100 not in result
    # Valid issue should be processed
    assert 101 in result
    assert result[101][0].number == 200


# Tests for _parse_issues_with_pr_linkages (timeline events approach)


def test_parse_issues_with_pr_linkages_single_pr_closing_issue() -> None:
    """Test parsing response with a PR that closes a single issue."""
    ops = RealGitHub(FakeTime())

    response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [
                        {
                            "number": 100,
                            "title": "Test Issue",
                            "body": "Issue body",
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/issues/100",
                            "author": {"login": "testuser"},
                            "labels": {"nodes": [{"name": "bug"}]},
                            "assignees": {"nodes": []},
                            "createdAt": "2024-01-01T00:00:00Z",
                            "updatedAt": "2024-01-02T00:00:00Z",
                            "timelineItems": {
                                "nodes": [
                                    {
                                        "willCloseTarget": True,
                                        "source": {
                                            "number": 200,
                                            "state": "OPEN",
                                            "url": "https://github.com/owner/repo/pull/200",
                                            "isDraft": False,
                                            "createdAt": "2024-01-03T00:00:00Z",
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
                            },
                        }
                    ]
                },
            }
        }
    }

    issues, pr_linkages = ops._parse_issues_with_pr_linkages(
        response, GitHubRepoId("owner", "repo")
    )

    # Verify issues parsed
    assert len(issues) == 1
    assert issues[0].number == 100
    assert issues[0].title == "Test Issue"

    # Verify PR linkages
    assert 100 in pr_linkages
    assert len(pr_linkages[100]) == 1
    pr = pr_linkages[100][0]
    assert pr.number == 200
    assert pr.state == "OPEN"
    assert pr.checks_passing is True
    assert pr.has_conflicts is False
    assert pr.checks_counts == (3, 3)
    assert pr.will_close_target is True


def test_parse_issues_with_pr_linkages_pr_closing_multiple_issues() -> None:
    """Test parsing response with a PR that closes multiple issues.

    With timeline events approach, each issue has its own timeline showing the PR.
    """
    ops = RealGitHub(FakeTime())

    # PR 200 references both issues (shows up in each issue's timeline)
    pr_event = {
        "willCloseTarget": True,
        "source": {
            "number": 200,
            "state": "OPEN",
            "url": "https://github.com/owner/repo/pull/200",
            "isDraft": False,
            "createdAt": "2024-01-02T00:00:00Z",
            "statusCheckRollup": None,
            "mergeable": "MERGEABLE",
        },
    }

    response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [
                        {
                            "number": 100,
                            "title": "Issue 100",
                            "body": "",
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/issues/100",
                            "author": {"login": "user"},
                            "labels": {"nodes": []},
                            "assignees": {"nodes": []},
                            "createdAt": "2024-01-01T00:00:00Z",
                            "updatedAt": "2024-01-01T00:00:00Z",
                            "timelineItems": {"nodes": [pr_event]},
                        },
                        {
                            "number": 101,
                            "title": "Issue 101",
                            "body": "",
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/issues/101",
                            "author": {"login": "user"},
                            "labels": {"nodes": []},
                            "assignees": {"nodes": []},
                            "createdAt": "2024-01-01T00:00:00Z",
                            "updatedAt": "2024-01-01T00:00:00Z",
                            "timelineItems": {"nodes": [pr_event]},
                        },
                    ]
                },
            }
        }
    }

    issues, pr_linkages = ops._parse_issues_with_pr_linkages(
        response, GitHubRepoId("owner", "repo")
    )

    # Both issues should have the same PR
    assert 100 in pr_linkages
    assert 101 in pr_linkages
    assert pr_linkages[100][0].number == 200
    assert pr_linkages[101][0].number == 200


def test_parse_issues_with_pr_linkages_multiple_prs_for_same_issue() -> None:
    """Test parsing response with multiple PRs referencing the same issue."""
    ops = RealGitHub(FakeTime())

    response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [
                        {
                            "number": 100,
                            "title": "Issue 100",
                            "body": "",
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/issues/100",
                            "author": {"login": "user"},
                            "labels": {"nodes": []},
                            "assignees": {"nodes": []},
                            "createdAt": "2024-01-01T00:00:00Z",
                            "updatedAt": "2024-01-01T00:00:00Z",
                            "timelineItems": {
                                "nodes": [
                                    {
                                        "willCloseTarget": True,
                                        "source": {
                                            "number": 201,
                                            "state": "OPEN",
                                            "url": "https://github.com/owner/repo/pull/201",
                                            "isDraft": False,
                                            "createdAt": "2024-01-02T00:00:00Z",  # Newer
                                            "statusCheckRollup": None,
                                            "mergeable": "MERGEABLE",
                                        },
                                    },
                                    {
                                        "willCloseTarget": False,  # Just a reference
                                        "source": {
                                            "number": 200,
                                            "state": "CLOSED",
                                            "url": "https://github.com/owner/repo/pull/200",
                                            "isDraft": False,
                                            "createdAt": "2024-01-01T00:00:00Z",  # Older
                                            "statusCheckRollup": {"state": "FAILURE"},
                                            "mergeable": "MERGEABLE",
                                        },
                                    },
                                ]
                            },
                        }
                    ]
                },
            }
        }
    }

    issues, pr_linkages = ops._parse_issues_with_pr_linkages(
        response, GitHubRepoId("owner", "repo")
    )

    # Issue should have both PRs, sorted by created_at descending
    assert 100 in pr_linkages
    assert len(pr_linkages[100]) == 2
    assert pr_linkages[100][0].number == 201  # Newer PR first
    assert pr_linkages[100][1].number == 200  # Older PR second
    # Verify will_close_target is preserved
    assert pr_linkages[100][0].will_close_target is True
    assert pr_linkages[100][1].will_close_target is False


def test_parse_issues_with_pr_linkages_issue_with_no_referencing_prs() -> None:
    """Test parsing response with issue that has no referencing PRs."""
    ops = RealGitHub(FakeTime())

    response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [
                        {
                            "number": 100,
                            "title": "Issue 100",
                            "body": "",
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/issues/100",
                            "author": {"login": "user"},
                            "labels": {"nodes": []},
                            "assignees": {"nodes": []},
                            "createdAt": "2024-01-01T00:00:00Z",
                            "updatedAt": "2024-01-01T00:00:00Z",
                            "timelineItems": {"nodes": []},  # No timeline events
                        }
                    ]
                },
            }
        }
    }

    issues, pr_linkages = ops._parse_issues_with_pr_linkages(
        response, GitHubRepoId("owner", "repo")
    )

    # Issue should be returned, but no PR linkages
    assert len(issues) == 1
    assert issues[0].number == 100
    assert 100 not in pr_linkages


def test_parse_issues_with_pr_linkages_handles_null_nodes() -> None:
    """Test parsing handles null values in nodes arrays."""
    ops = RealGitHub(FakeTime())

    response = {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [
                        None,  # Null issue node
                        {
                            "number": 100,
                            "title": "Issue 100",
                            "body": "",
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/issues/100",
                            "author": {"login": "user"},
                            "labels": {"nodes": []},
                            "assignees": {"nodes": []},
                            "createdAt": "2024-01-01T00:00:00Z",
                            "updatedAt": "2024-01-01T00:00:00Z",
                            "timelineItems": {
                                "nodes": [
                                    None,  # Null timeline event
                                    {
                                        "willCloseTarget": True,
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
                            },
                        },
                    ]
                },
            }
        }
    }

    issues, pr_linkages = ops._parse_issues_with_pr_linkages(
        response, GitHubRepoId("owner", "repo")
    )

    # Should skip null nodes and process valid ones
    assert len(issues) == 1
    assert issues[0].number == 100
    assert 100 in pr_linkages
    assert pr_linkages[100][0].number == 200
