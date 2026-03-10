"""Unit tests for RealLocalGitHub._parse_check_runs_response."""

from tests.test_utils.context_builders import real_github_for_test


def _make_check_run_node(
    *,
    name: str = "CI / unit-tests",
    status: str = "COMPLETED",
    conclusion: str | None = "SUCCESS",
    details_url: str | None = "https://github.com/runs/1",
) -> dict:
    """Create a CheckRun node matching GraphQL statusCheckRollup response shape."""
    node: dict = {
        "__typename": "CheckRun",
        "name": name,
        "status": status,
        "detailsUrl": details_url,
    }
    if conclusion is not None:
        node["conclusion"] = conclusion
    return node


def _make_status_context_node(
    *,
    context: str = "ci/build",
    state: str = "SUCCESS",
    target_url: str | None = "https://ci.example.com/build/1",
) -> dict:
    """Create a StatusContext node matching GraphQL statusCheckRollup response shape."""
    return {
        "__typename": "StatusContext",
        "context": context,
        "state": state,
        "targetUrl": target_url,
    }


def _wrap_check_runs_response(nodes: list[dict | None]) -> dict:
    """Wrap nodes in the expected GraphQL statusCheckRollup response structure."""
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "statusCheckRollup": {
                        "contexts": {
                            "nodes": nodes,
                        }
                    }
                }
            }
        }
    }


def test_parse_check_runs_filters_successful_checks() -> None:
    """SUCCESS CheckRuns are excluded from results."""
    github = real_github_for_test()
    response = _wrap_check_runs_response(
        [
            _make_check_run_node(name="passing-check", conclusion="SUCCESS"),
        ]
    )

    result = github._parse_check_runs_response(response)

    assert len(result) == 0


def test_parse_check_runs_includes_failed_checks() -> None:
    """FAILURE CheckRuns are included in results."""
    github = real_github_for_test()
    response = _wrap_check_runs_response(
        [
            _make_check_run_node(name="failing-check", conclusion="FAILURE"),
        ]
    )

    result = github._parse_check_runs_response(response)

    assert len(result) == 1
    assert result[0].name == "failing-check"
    assert result[0].conclusion == "failure"
    assert result[0].status == "completed"


def test_parse_check_runs_includes_in_progress_checks() -> None:
    """CheckRuns with null conclusion (in progress) are included."""
    github = real_github_for_test()
    response = _wrap_check_runs_response(
        [
            _make_check_run_node(name="running-check", status="IN_PROGRESS", conclusion=None),
        ]
    )

    # conclusion=None means we don't set it in the node dict
    # but _make_check_run_node only omits it when conclusion is None
    result = github._parse_check_runs_response(response)

    assert len(result) == 1
    assert result[0].name == "running-check"
    assert result[0].conclusion is None
    assert result[0].status == "in_progress"


def test_parse_check_runs_handles_status_context_failure() -> None:
    """StatusContext with FAILURE state is included."""
    github = real_github_for_test()
    response = _wrap_check_runs_response(
        [
            _make_status_context_node(context="ci/deploy", state="FAILURE"),
        ]
    )

    result = github._parse_check_runs_response(response)

    assert len(result) == 1
    assert result[0].name == "ci/deploy"
    assert result[0].conclusion == "failure"
    assert result[0].status == "completed"


def test_parse_check_runs_handles_status_context_pending() -> None:
    """StatusContext with PENDING state is included with no conclusion."""
    github = real_github_for_test()
    response = _wrap_check_runs_response(
        [
            _make_status_context_node(context="ci/pending-job", state="PENDING"),
        ]
    )

    result = github._parse_check_runs_response(response)

    assert len(result) == 1
    assert result[0].name == "ci/pending-job"
    assert result[0].conclusion is None
    assert result[0].status == "pending"


def test_parse_check_runs_excludes_status_context_success() -> None:
    """StatusContext with SUCCESS state is excluded."""
    github = real_github_for_test()
    response = _wrap_check_runs_response(
        [
            _make_status_context_node(context="ci/passing", state="SUCCESS"),
        ]
    )

    result = github._parse_check_runs_response(response)

    assert len(result) == 0


def test_parse_check_runs_sorts_by_name() -> None:
    """Results are sorted alphabetically by name."""
    github = real_github_for_test()
    response = _wrap_check_runs_response(
        [
            _make_check_run_node(name="z-check", conclusion="FAILURE"),
            _make_check_run_node(name="a-check", conclusion="FAILURE"),
            _make_status_context_node(context="m-context", state="FAILURE"),
        ]
    )

    result = github._parse_check_runs_response(response)

    assert [c.name for c in result] == ["a-check", "m-context", "z-check"]


def test_parse_check_runs_empty_response() -> None:
    """Null/missing data returns empty list."""
    github = real_github_for_test()

    # No pullRequest data
    response = {"data": {"repository": {"pullRequest": None}}}
    assert github._parse_check_runs_response(response) == []

    # No statusCheckRollup
    response = {"data": {"repository": {"pullRequest": {"statusCheckRollup": None}}}}
    assert github._parse_check_runs_response(response) == []

    # Empty data (no repository key)
    response = {"data": {}}
    assert github._parse_check_runs_response(response) == []


def test_parse_check_runs_null_nodes_skipped() -> None:
    """None nodes in the list are skipped."""
    github = real_github_for_test()
    response = _wrap_check_runs_response(
        [
            None,
            _make_check_run_node(name="real-check", conclusion="FAILURE"),
            None,
        ]
    )

    result = github._parse_check_runs_response(response)

    assert len(result) == 1
    assert result[0].name == "real-check"
