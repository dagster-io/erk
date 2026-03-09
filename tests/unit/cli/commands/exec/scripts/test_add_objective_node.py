"""Unit tests for add-objective-node command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.add_objective_node import add_objective_node
from erk_shared.context.context import ErkContext
from erk_shared.fakes.github import FakeLocalGitHub
from erk_shared.fakes.github_issues import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo

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

## Roadmap

### Phase 1: Foundation (1 PR)

| Node | Description | Status | PR |
|------|-------------|--------|----|
| 1.1 | Set up project structure | done | #100 |
| 1.2 | Add core types | in-progress | - |
| 1.3 | Add utility functions | pending | - |

### Phase 2: Implementation (0 PR)

| Node | Description | Status | PR |
|------|-------------|--------|----|
| 2.1 | Implement main feature | pending | - |
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


def test_add_node_to_existing_phase() -> None:
    """Add a node to an existing phase."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "8470",
            "--phase",
            "1",
            "--description",
            "Add error handling",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 8470
    assert output["node_id"] == "1.4"
    assert output["url"] == "https://github.com/test/repo/issues/8470"

    # Verify the body was updated
    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert "Add error handling" in updated_body
    assert "id: '1.4'" in updated_body or 'id: "1.4"' in updated_body


def test_add_node_to_phase_2() -> None:
    """Add a node to phase 2 (different phase)."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "8470",
            "--phase",
            "2",
            "--description",
            "Add integration tests",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["node_id"] == "2.2"


def test_add_node_auto_generates_slug() -> None:
    """Slug is auto-generated from description when not provided."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "8470",
            "--phase",
            "1",
            "--description",
            "Clean up dead code paths",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "clean-up-dead-code-paths" in updated_body


def test_add_node_with_explicit_slug() -> None:
    """Explicit slug is used when provided."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "8470",
            "--phase",
            "1",
            "--description",
            "Clean up dead code",
            "--slug",
            "cleanup-dead-code",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "cleanup-dead-code" in updated_body


def test_add_node_with_depends_on() -> None:
    """Node with depends_on is added correctly."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "8470",
            "--phase",
            "1",
            "--description",
            "Depends on setup",
            "--depends-on",
            "1.1",
            "--depends-on",
            "1.2",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["node_id"] == "1.4"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "depends_on" in updated_body


def test_add_node_with_reason() -> None:
    """Node with reason is added correctly."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "8470",
            "--phase",
            "1",
            "--description",
            "New cleanup task",
            "--reason",
            "Added during re-evaluation",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "Added during re-evaluation" in updated_body


def test_add_node_issue_not_found() -> None:
    """Error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "999",
            "--phase",
            "1",
            "--description",
            "Some task",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"


def test_add_node_no_roadmap() -> None:
    """Error when issue has no roadmap metadata block."""
    issue = _make_issue(8470, NO_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "8470",
            "--phase",
            "1",
            "--description",
            "Some task",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_roadmap"


def test_add_node_to_new_phase() -> None:
    """Adding to a phase that doesn't exist yet appends at end."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "8470",
            "--phase",
            "3",
            "--description",
            "New phase task",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # New phase 3, first node
    assert output["node_id"] == "3.1"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "New phase task" in updated_body


def test_add_node_with_explicit_status() -> None:
    """Node added with explicit non-default status."""
    issue = _make_issue(8470, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={8470: issue})
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "8470",
            "--phase",
            "1",
            "--description",
            "Already planned task",
            "--status",
            "planning",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "status: planning" in updated_body


V2_BODY_WITH_COMMENT = """\
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-header -->
<details>
<summary><code>objective-header</code></summary>

```yaml

created_at: '2025-01-01T00:00:00+00:00'
created_by: testuser
objective_comment_id: 42

```

</details>
<!-- /erk:metadata-block:objective-header -->

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
    status: pending
    pr: null

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

V2_COMMENT = """\
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-body -->
<details open>
<summary><strong>Objective</strong></summary>

# Objective: Build Feature X

## Roadmap

<!-- erk:roadmap-table -->
### Phase 1: Foundation (1 PR)

| Node | Description | Status | PR |
|------|-------------|--------|----|
| 1.1 | Set up project structure | done | #100 |
| 1.2 | Add core types | pending | - |
<!-- /erk:roadmap-table -->

</details>
<!-- /erk:metadata-block:objective-body -->
"""


def test_add_node_rerenders_comment_table() -> None:
    """v2 format: adding a node also re-renders the comment table."""
    issue = _make_issue(8470, V2_BODY_WITH_COMMENT)
    comment = IssueComment(
        body=V2_COMMENT,
        url="https://github.com/test/repo/issues/8470#issuecomment-42",
        id=42,
        author="testuser",
    )
    fake_gh = FakeGitHubIssues(
        issues={8470: issue},
        comments_with_urls={8470: [comment]},
    )
    runner = CliRunner()

    result = runner.invoke(
        add_objective_node,
        [
            "8470",
            "--phase",
            "1",
            "--description",
            "Add error handling",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["node_id"] == "1.3"

    # Body should be updated
    assert len(fake_gh.updated_bodies) == 1

    # Comment table should also be re-rendered
    assert len(fake_gh.updated_comments) == 1
    updated_comment = fake_gh.updated_comments[0][1]
    assert "Add error handling" in updated_comment
