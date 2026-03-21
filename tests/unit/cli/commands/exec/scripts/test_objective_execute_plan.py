"""Tests for objective-execute-plan exec command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_execute_plan import objective_execute_plan
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import RepoInfo
from tests.fakes.gateway.remote_github import FakeRemoteGitHub

_TEST_REPO_INFO = RepoInfo(owner="test-owner", name="test-repo")

OBJECTIVE_BODY_WITH_ROADMAP = """\
# Objective: Build Feature X

## Roadmap

### Phase 1: Foundation

### Phase 2: Implementation

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml

schema_version: '4'
nodes:
  - id: '1.1'
    slug: setup-project
    description: Set up project structure
    status: pending
    pr: null
  - id: '1.2'
    slug: add-core-types
    description: Add core types
    status: pending
    pr: null
  - id: '1.3'
    slug: implement-feature
    description: Implement main feature
    status: pending
    pr: null
  - id: '2.1'
    slug: add-tests
    description: Add integration tests
    status: pending
    pr: null

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

OBJECTIVE_BODY_ALL_DONE = """\
# Objective: Completed

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml

schema_version: '4'
nodes:
  - id: '1.1'
    slug: done-node
    description: Already done
    status: done
    pr: '#1'

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""


def _make_issue(
    number: int,
    title: str,
    body: str,
    *,
    labels: list[str] | None = None,
) -> IssueInfo:
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=labels if labels is not None else ["erk-objective"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def _make_remote(issues: dict[int, IssueInfo]) -> FakeRemoteGitHub:
    return FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="master",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=issues,
        issue_comments=None,
    )


def test_json_output_structure() -> None:
    """JSON output includes objective, nodes, total_pending, requested, resolved."""
    issue = _make_issue(42, "Build Feature X", OBJECTIVE_BODY_WITH_ROADMAP)
    ctx = ErkContext.for_test(
        remote_github=_make_remote({42: issue}),
        repo_info=_TEST_REPO_INFO,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_execute_plan,
        ["42", "--count", "3", "--json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["objective"] == 42
    assert output["requested"] == 3
    assert output["resolved"] == 3
    assert output["total_pending"] == 4
    nodes = output["nodes"]
    assert len(nodes) == 3
    assert nodes[0]["position"] == 1
    assert nodes[0]["id"] == "1.1"
    assert nodes[1]["position"] == 2
    assert nodes[1]["id"] == "1.2"
    assert nodes[2]["position"] == 3
    assert nodes[2]["id"] == "1.3"


def test_json_node_ordering_reflects_dependency_simulation() -> None:
    """Nodes are returned in simulated execution order, not just graph order."""
    issue = _make_issue(42, "Build Feature X", OBJECTIVE_BODY_WITH_ROADMAP)
    ctx = ErkContext.for_test(
        remote_github=_make_remote({42: issue}),
        repo_info=_TEST_REPO_INFO,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_execute_plan,
        ["42", "--count", "4", "--json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    ids = [n["id"] for n in output["nodes"]]
    assert ids == ["1.1", "1.2", "1.3", "2.1"]


def test_json_resolved_less_than_requested_when_fewer_nodes() -> None:
    """resolved < requested when there are fewer pending nodes than count."""
    issue = _make_issue(42, "Build Feature X", OBJECTIVE_BODY_WITH_ROADMAP)
    ctx = ErkContext.for_test(
        remote_github=_make_remote({42: issue}),
        repo_info=_TEST_REPO_INFO,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_execute_plan,
        ["42", "--count", "10", "--json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["requested"] == 10
    assert output["resolved"] == 4  # only 4 pending nodes exist


def test_text_output_format() -> None:
    """Text output lists nodes with position, id, description, and phase."""
    issue = _make_issue(42, "Build Feature X", OBJECTIVE_BODY_WITH_ROADMAP)
    ctx = ErkContext.for_test(
        remote_github=_make_remote({42: issue}),
        repo_info=_TEST_REPO_INFO,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_execute_plan,
        ["42", "--count", "2"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "Execution plan for objective #42" in result.output
    assert "2 of 2 requested nodes resolved" in result.output
    assert "[1.1]" in result.output
    assert "[1.2]" in result.output
    assert "Set up project structure" in result.output


def test_objective_not_found_returns_exit_code_1() -> None:
    """Non-existent objective number exits with code 1."""
    ctx = ErkContext.for_test(
        remote_github=_make_remote({}),
        repo_info=_TEST_REPO_INFO,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_execute_plan,
        ["999", "--count", "3", "--json"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False


def test_all_done_objective_returns_empty_nodes() -> None:
    """Objective with all nodes done returns empty nodes list."""
    issue = _make_issue(42, "Completed", OBJECTIVE_BODY_ALL_DONE)
    ctx = ErkContext.for_test(
        remote_github=_make_remote({42: issue}),
        repo_info=_TEST_REPO_INFO,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_execute_plan,
        ["42", "--count", "5", "--json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["resolved"] == 0
    assert output["nodes"] == []
    assert output["total_pending"] == 0
