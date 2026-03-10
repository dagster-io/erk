"""Unit tests for remove-objective-node command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.remove_objective_node import remove_objective_node
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues

ROADMAP_BODY = """\
# Objective: Build Feature X

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml

schema_version: '4'
nodes:
  - id: '1.1'
    slug: setup-project
    description: Set up project structure
    status: done
    pr: '#100'
  - id: '1.2'
    slug: add-core-types
    description: Add core types
    status: in_progress
    pr: null
  - id: '1.3'
    slug: add-utils
    description: Add utility functions
    status: pending
    pr: null
  - id: '2.1'
    slug: implement-main
    description: Implement main feature
    status: pending
    pr: null

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

NO_ROADMAP_BODY = """\
# Objective: Simple Issue

No roadmap table here, just some text.
"""


def _make_issue(number: int, body: str) -> IssueInfo:
    """Create a test IssueInfo."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test Objective #{number}",
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_remove_existing_node() -> None:
    """Remove an existing node from the roadmap."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        remove_objective_node,
        ["8470", "--node", "1.3"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["node_id"] == "1.3"
    assert output["issue_number"] == 8470

    # Verify the body was updated and the node is gone
    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert "Add utility functions" not in updated_body
    # Other nodes still present
    assert "Set up project structure" in updated_body
    assert "Add core types" in updated_body


def test_remove_node_not_found() -> None:
    """Error when node ID doesn't exist."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        remove_objective_node,
        ["8470", "--node", "9.9"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "node_not_found"


def test_remove_node_issue_not_found() -> None:
    """Error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        remove_objective_node,
        ["999", "--node", "1.1"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"


def test_remove_node_no_roadmap() -> None:
    """Error when issue has no roadmap metadata block."""
    issue = _make_issue(8470, NO_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        remove_objective_node,
        ["8470", "--node", "1.1"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_roadmap"


def test_remove_node_with_reason_posts_comment() -> None:
    """Using --reason auto-posts an action comment."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        remove_objective_node,
        [
            "8470",
            "--node",
            "1.3",
            "--reason",
            "Superseded by new approach",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    # Should have posted an action comment
    assert len(fake_gh.added_comments) == 1
    _, comment_body, _ = fake_gh.added_comments[0]
    assert "Removed node 1.3" in comment_body
    assert "Superseded by new approach" in comment_body


def test_remove_node_without_reason_no_comment() -> None:
    """Without --reason, --comment, or --lessons, no action comment is posted."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        remove_objective_node,
        ["8470", "--node", "1.3"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # No action comment posted
    assert len(fake_gh.added_comments) == 0
