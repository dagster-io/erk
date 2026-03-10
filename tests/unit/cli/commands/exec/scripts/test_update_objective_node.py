"""Unit tests for update-objective-node command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_objective_node import update_objective_node
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.gateway.github.metadata.core import find_metadata_block
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.test_utils.plan_helpers import format_plan_header_body_for_test

ROADMAP_BODY_V2 = """\
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
    pr: '#100'
  - id: '1.2'
    description: Add core types
    status: in_progress
    pr: null
  - id: '1.3'
    description: Add utility functions
    status: pending
    pr: null
  - id: '2.1'
    description: Implement main feature
    status: pending
    pr: null
  - id: '2.2'
    description: Add tests
    status: blocked
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

### Phase 2: Implementation (1 PR)

| Node | Description | Status | PR |
|------|-------------|--------|----|
| 2.1 | Implement main feature | pending | - |
| 2.2 | Add tests | blocked | - |
"""

NO_ROADMAP_BODY = """\
# Objective: Simple Issue

No roadmap table here, just some text.
"""


def _make_issue(number: int, body: str) -> IssueInfo:
    """Create a test IssueInfo with a roadmap body."""
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


def test_update_pending_step_with_pr() -> None:
    """Update a pending step with a PR reference."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 6423
    assert output["node_id"] == "1.3"
    assert output["previous_pr"] is None
    assert output["new_pr"] == "#500"
    assert output["url"] == "https://github.com/test/repo/issues/6423"

    # Verify the body was updated with frontmatter
    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert "#500" in updated_body
    assert "status: in_progress" in updated_body


def test_clear_pr_reference() -> None:
    """Clear a step's PR reference by passing empty string."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.1", "--pr", ""],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["previous_pr"] == "#100"
    assert output["new_pr"] is None

    updated_body = fake_gh.updated_bodies[0][1]
    assert "status: pending" in updated_body


def test_step_not_found() -> None:
    """Error when step ID doesn't exist in roadmap."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "9.9", "--pr", "#123"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "node_not_found"
    assert "9.9" in output["message"]


def test_issue_not_found() -> None:
    """Error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["999", "--node", "1.1", "--pr", "#123"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"
    assert "999" in output["message"]


def test_no_roadmap_table() -> None:
    """Error when issue has no roadmap table."""
    issue = _make_issue(6423, NO_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.1", "--pr", "#123"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_roadmap"


def test_update_step_in_phase_2() -> None:
    """Update a step in a later phase."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "2.1", "--pr", "#300"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["node_id"] == "2.1"
    assert output["previous_pr"] is None
    assert output["new_pr"] == "#300"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "#300" in updated_body


def test_update_with_frontmatter() -> None:
    """Update step when frontmatter is present updates YAML."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#999"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["new_pr"] == "#999"

    updated_body = fake_gh.updated_bodies[0][1]
    # Frontmatter should contain the new PR
    assert "pr: '#999'" in updated_body or 'pr: "#999"' in updated_body


def test_update_with_frontmatter_preserves_other_steps() -> None:
    """Update with frontmatter preserves other steps' data."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.2", "--pr", "#777"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    updated_body = fake_gh.updated_bodies[0][1]

    # Original step 1.1 should remain unchanged in frontmatter
    assert "id: '1.1'" in updated_body or 'id: "1.1"' in updated_body
    assert "pr: '#100'" in updated_body or 'pr: "#100"' in updated_body
    assert "status: done" in updated_body


def test_explicit_status_option_with_frontmatter() -> None:
    """--status flag sets explicit status in frontmatter."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500", "--status", "done"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "status: done" in updated_body


def test_update_multiple_steps_success() -> None:
    """Update multiple steps in a single operation — all succeed."""
    issue = _make_issue(6697, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6697", "--node", "1.2", "--node", "1.3", "--node", "2.1", "--pr", "#555"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 6697
    assert output["new_pr"] == "#555"
    assert output["url"] == "https://github.com/test/repo/issues/6697"

    assert "nodes" in output
    assert len(output["nodes"]) == 3

    step_1_2 = next(s for s in output["nodes"] if s["node_id"] == "1.2")
    assert step_1_2["success"] is True

    step_1_3 = next(s for s in output["nodes"] if s["node_id"] == "1.3")
    assert step_1_3["success"] is True

    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert updated_body.count("#555") == 3


def test_update_multiple_steps_partial_failure() -> None:
    """Multi-step update rejected upfront when any step is missing."""
    issue = _make_issue(6697, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6697", "--node", "1.2", "--node", "9.9", "--node", "2.1", "--pr", "#555"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["issue_number"] == 6697

    assert len(output["nodes"]) == 1
    assert output["nodes"][0]["node_id"] == "9.9"
    assert output["nodes"][0]["success"] is False

    assert len(fake_gh.updated_bodies) == 0


def test_build_output_multi_step_and_semantics() -> None:
    """_build_output uses AND semantics: success=false when any step fails.

    Tests the batch success semantics directly. The processing loop's
    replacement_failed path is defensive (parse_roadmap and
    _replace_node_refs_in_body use the same underlying parsing), so we
    verify AND semantics through _build_output with mixed results.
    """
    from erk.cli.commands.exec.scripts.update_objective_node import (
        UpdateObjectiveNodeResult,
        _build_output,
    )

    results = [
        UpdateObjectiveNodeResult.ok(node_id="1.2", previous_pr=None),
        UpdateObjectiveNodeResult.fail(node_id="1.3", error="replacement_failed"),
    ]
    output = _build_output(
        issue_number=6697,
        node=("1.2", "1.3"),
        pr_value="#555",
        url="https://github.com/test/repo/issues/6697",
        results=results,
        include_body=False,
        updated_body=None,
        backlink=None,
    )

    # AND semantics: success=false because step 1.3 failed
    output_dict = output.to_dict()
    assert output_dict["success"] is False
    assert output_dict["issue_number"] == 6697
    nodes = output_dict["nodes"]
    assert isinstance(nodes, list)
    assert len(nodes) == 2


def test_update_multiple_steps_same_phase() -> None:
    """Update multiple steps within the same phase."""
    issue = _make_issue(6697, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6697", "--node", "1.1", "--node", "1.2", "--node", "1.3", "--pr", "#555"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    assert len(output["nodes"]) == 3
    for step_result in output["nodes"]:
        assert step_result["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert updated_body.count("#555") == 3


def test_single_step_maintains_legacy_output_format() -> None:
    """Single --step usage maintains backward-compatible output format."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    # Should use legacy format (no "steps" array)
    assert "nodes" not in output
    assert output["success"] is True
    assert output["node_id"] == "1.3"
    assert output["previous_pr"] is None
    assert output["new_pr"] == "#500"


def test_include_body_flag_single_step() -> None:
    """--include-body includes updated_body in JSON output for single step."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500", "--include-body"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "updated_body" in output
    assert "#500" in output["updated_body"]
    assert "status: in_progress" in output["updated_body"]


def test_include_body_flag_multiple_steps() -> None:
    """--include-body includes updated_body with all step mutations applied."""
    issue = _make_issue(6697, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6697", "--node", "1.2", "--node", "1.3", "--pr", "#555", "--include-body"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "updated_body" in output
    # Both steps should be reflected in the body
    assert output["updated_body"].count("#555") == 2


def test_include_body_not_set_by_default() -> None:
    """updated_body field is absent when --include-body is not passed."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "updated_body" not in output


def test_none_pr_preserves_existing_value() -> None:
    """Passing new_pr=None to the update function preserves existing PR reference."""
    from erk.cli.commands.exec.scripts.update_objective_node import _replace_node_refs_in_body

    # Step 1.1 has pr=#100
    result = _replace_node_refs_in_body(
        ROADMAP_BODY_V2,
        "1.1",
        new_pr=None,
        explicit_status="planning",
        description=None,
        slug=None,
        reason=None,
    )

    assert result is not None
    # PR should be preserved
    assert "#100" in result
    assert "status: planning" in result


def test_empty_string_clears_pr_value() -> None:
    """_replace_node_refs_in_body with empty string clears to null."""
    from erk.cli.commands.exec.scripts.update_objective_node import _replace_node_refs_in_body

    # Step 1.1 has pr=#100
    result = _replace_node_refs_in_body(
        ROADMAP_BODY_V2,
        "1.1",
        new_pr="",
        explicit_status=None,
        description=None,
        slug=None,
        reason=None,
    )

    assert result is not None
    assert "status: pending" in result


def test_planning_status_via_explicit_status() -> None:
    """update-objective-node with --status planning sets planning status."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#200", "--status", "planning"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "status: planning" in updated_body
    assert "#200" in updated_body


def test_include_body_on_failure() -> None:
    """updated_body field is absent on failure even with --include-body."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "9.9", "--pr", "#500", "--include-body"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert "updated_body" not in output


def test_no_metadata_block_returns_no_roadmap() -> None:
    """When issue body has no metadata block, returns no_roadmap error."""
    body_without_metadata = """\
# Objective: Build Feature X

## Roadmap

### Phase 1: Foundation (1 PR)

| Node | Description | Status | PR |
|------|-------------|--------|----|
| 1.1 | Set up project structure | done | #100 |
"""
    issue = _make_issue(6423, body_without_metadata)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.1", "--pr", "#500"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_roadmap"


# --- v2 format tests: objective-header with objective_comment_id ---

V2_BODY = """\
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

schema_version: '2'
steps:
  - id: '1.1'
    description: Set up project structure
    status: done
    pr: '#100'
  - id: '1.2'
    description: Add core types
    status: in_progress
    pr: null
  - id: '1.3'
    description: Add utility functions
    status: pending
    pr: null

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

V2_COMMENT_BODY = """\
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
| 1.2 | Add core types | in-progress | - |
| 1.3 | Add utility functions | pending | - |
<!-- /erk:roadmap-table -->

</details>
<!-- /erk:metadata-block:objective-body -->
"""


def test_v2_update_also_updates_comment_table() -> None:
    """v2 format: update-objective-node updates both body frontmatter and comment table."""
    issue = _make_issue(6423, V2_BODY)
    comment = IssueComment(
        body=V2_COMMENT_BODY,
        url="https://github.com/test/repo/issues/6423#issuecomment-42",
        id=42,
        author="testuser",
    )
    fake_gh = FakeGitHubIssues(
        issues={6423: issue},
        comments_with_urls={6423: [comment]},
    )
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    # Body frontmatter should be updated
    updated_body = fake_gh.updated_bodies[0][1]
    assert "#500" in updated_body

    # Comment table should also be re-rendered
    assert len(fake_gh.updated_comments) == 1
    updated_comment = fake_gh.updated_comments[0][1]
    assert "#500" in updated_comment
    assert "| in-progress |" in updated_comment


def test_v2_no_comment_update_when_no_header() -> None:
    """When no objective-header exists, only body is updated (no comment)."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Body should be updated
    assert len(fake_gh.updated_bodies) == 1

    # No comment updates should happen
    assert len(fake_gh.updated_comments) == 0


def test_update_step_with_pr_and_explicit_done() -> None:
    """Pass --pr and --status done: PR set and status marked done."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.2", "--pr", "#500", "--status", "done"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["new_pr"] == "#500"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "#500" in updated_body
    assert "status: done" in updated_body


def test_status_only_without_pr() -> None:
    """--status without --pr sets status while preserving existing PR."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.1", "--status", "planning"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["node_id"] == "1.1"
    assert output["previous_pr"] == "#100"
    assert output["new_pr"] is None

    updated_body = fake_gh.updated_bodies[0][1]
    assert "status: planning" in updated_body
    # PR should be preserved
    assert "#100" in updated_body


def test_neither_pr_nor_status_returns_error() -> None:
    """Omitting all update flags returns a no_update error."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.1"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_update"
    assert len(fake_gh.updated_bodies) == 0


def test_update_description() -> None:
    """--description updates the node description in frontmatter YAML."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.2", "--description", "Updated core types description"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    # Description updated in YAML frontmatter
    assert "Updated core types description" in updated_body


def test_update_slug() -> None:
    """--slug updates the node slug in frontmatter."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--slug", "add-utils"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "add-utils" in updated_body


def test_update_reason() -> None:
    """--reason sets the reason field in frontmatter."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--status", "skipped", "--reason", "Superseded by new approach"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "Superseded by new approach" in updated_body
    assert "status: skipped" in updated_body


def test_reason_preserved_when_not_passed() -> None:
    """Reason is preserved when not passed in an update."""
    # Build a body that already has a reason
    body_with_reason = """\
# Objective: Build Feature X

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml

schema_version: '4'
nodes:
  - id: '1.1'
    description: Set up project structure
    status: skipped
    pr: null
    slug: null
    reason: Was not needed

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""
    issue = _make_issue(6423, body_with_reason)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.1", "--status", "pending"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "Was not needed" in updated_body
    assert "status: pending" in updated_body


def test_description_combined_with_status() -> None:
    """--description combined with --status updates both fields."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        [
            "6423",
            "--node",
            "2.1",
            "--description",
            "Implement main feature v2",
            "--status",
            "planning",
        ],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "Implement main feature v2" in updated_body
    assert "status: planning" in updated_body


# --- Backlink tests: --pr sets objective_issue on plan PR ---


def _make_plan_pr(number: int, *, objective_issue: int | None) -> IssueInfo:
    """Create a plan PR (as IssueInfo) with a plan-header metadata block."""
    now = datetime.now(UTC)
    body = format_plan_header_body_for_test(objective_issue=objective_issue)
    return IssueInfo(
        number=number,
        title=f"[erk-plan] Test Plan #{number}",
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/pull/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_backlink_set_when_pr_has_no_objective_issue() -> None:
    """Setting --pr on a node also sets objective_issue on the plan PR."""
    objective = _make_issue(6423, ROADMAP_BODY_V2)
    plan_pr = _make_plan_pr(500, objective_issue=None)
    fake_gh = FakeGitHubIssues(issues={6423: objective, 500: plan_pr})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["backlink_set"] is True

    # Verify objective body was updated (first call) and plan PR body was updated (second call)
    assert len(fake_gh.updated_bodies) == 2
    plan_pr_body = fake_gh.updated_bodies[1][1]
    block = find_metadata_block(plan_pr_body, "plan-header")
    assert block is not None
    assert block.data["objective_issue"] == 6423


def test_backlink_already_matching_no_extra_write() -> None:
    """If plan PR already has matching objective_issue, no extra write."""
    objective = _make_issue(6423, ROADMAP_BODY_V2)
    plan_pr = _make_plan_pr(500, objective_issue=6423)
    fake_gh = FakeGitHubIssues(issues={6423: objective, 500: plan_pr})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["backlink_set"] is True

    # Only the objective body should be updated, not the plan PR
    assert len(fake_gh.updated_bodies) == 1


def test_backlink_different_objective_emits_warning() -> None:
    """If plan PR has a different objective_issue, warning emitted, no overwrite."""
    objective = _make_issue(6423, ROADMAP_BODY_V2)
    plan_pr = _make_plan_pr(500, objective_issue=9999)
    fake_gh = FakeGitHubIssues(issues={6423: objective, 500: plan_pr})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["backlink_set"] is False
    assert "9999" in output["backlink_warning"]

    # Only the objective body should be updated, not the plan PR
    assert len(fake_gh.updated_bodies) == 1


def test_backlink_skipped_when_no_plan_header() -> None:
    """If the PR has no plan-header block, backlink is silently skipped."""
    objective = _make_issue(6423, ROADMAP_BODY_V2)
    now = datetime.now(UTC)
    plain_pr = IssueInfo(
        number=500,
        title="Regular PR #500",
        body="Just a regular PR body without plan-header",
        state="OPEN",
        url="https://github.com/test/repo/pull/500",
        labels=[],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )
    fake_gh = FakeGitHubIssues(issues={6423: objective, 500: plain_pr})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["backlink_set"] is False
    assert output["backlink_skip"] == "no plan-header block"

    # Only the objective body should be updated
    assert len(fake_gh.updated_bodies) == 1


def test_backlink_not_attempted_when_no_pr() -> None:
    """When no --pr is provided, no backlink attempt is made."""
    objective = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: objective})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.1", "--status", "planning"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "backlink_set" not in output
