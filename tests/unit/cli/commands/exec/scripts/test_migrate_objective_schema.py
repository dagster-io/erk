"""Unit tests for migrate-objective-schema command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.migrate_objective_schema import migrate_objective_schema
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo

V2_ROADMAP_BODY = """\
# Objective: Build Feature X

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml

schema_version: '2'
steps:
  - id: '1.1'
    description: Set up project structure
    status: done
    plan: null
    pr: '#100'
  - id: '1.2'
    description: Add core types
    status: in_progress
    plan: '#200'
    pr: null

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

V3_ROADMAP_BODY = """\
# Objective: Build Feature X

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml

schema_version: '3'
nodes:
  - id: '1.1'
    description: Set up project structure
    status: done
    plan: null
    pr: '#100'
  - id: '1.2'
    description: Add core types
    status: in_progress
    plan: '#200'
    pr: null

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

NO_ROADMAP_BODY = """\
# Objective: Simple Issue

No roadmap block here, just some text.
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


def test_migrate_v2_to_v3() -> None:
    """V2 objective is migrated to v3 — steps become nodes, schema_version becomes 3."""
    issue = _make_issue(7391, V2_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={7391: issue})
    runner = CliRunner()

    result = runner.invoke(
        migrate_objective_schema,
        ["7391"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 7391
    assert output["migrated"] is True
    assert output["previous_version"] == "2"
    assert output["new_version"] == "3"

    # Verify the body was actually updated
    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert "schema_version: '3'" in updated_body
    assert "nodes:" in updated_body
    # v2 key should no longer be present
    assert "steps:" not in updated_body


def test_already_v3_no_op() -> None:
    """V3 objective reports nothing to do without updating."""
    issue = _make_issue(7391, V3_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={7391: issue})
    runner = CliRunner()

    result = runner.invoke(
        migrate_objective_schema,
        ["7391"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["migrated"] is False
    assert "Already v3" in output["message"]

    # No update should have been made
    assert len(fake_gh.updated_bodies) == 0


def test_no_roadmap_block() -> None:
    """Issue without roadmap block reports appropriately."""
    issue = _make_issue(7391, NO_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={7391: issue})
    runner = CliRunner()

    result = runner.invoke(
        migrate_objective_schema,
        ["7391"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_roadmap_block"


def test_dry_run_no_update() -> None:
    """Dry run detects v2 but does not update the issue."""
    issue = _make_issue(7391, V2_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={7391: issue})
    runner = CliRunner()

    result = runner.invoke(
        migrate_objective_schema,
        ["7391", "--dry-run"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["migrated"] is True
    assert output["dry_run"] is True
    assert output["previous_version"] == "2"
    assert output["new_version"] == "3"

    # No update should have been made
    assert len(fake_gh.updated_bodies) == 0


def test_issue_not_found() -> None:
    """Error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        migrate_objective_schema,
        ["999"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"
