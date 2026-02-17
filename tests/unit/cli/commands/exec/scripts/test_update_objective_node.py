"""Unit tests for update-objective-node command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_objective_node import update_objective_node
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo

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
    plan: null
    pr: '#100'
  - id: '1.2'
    description: Add core types
    status: in_progress
    plan: '#200'
    pr: null
  - id: '1.3'
    description: Add utility functions
    status: pending
    plan: null
    pr: null
  - id: '2.1'
    description: Implement main feature
    status: pending
    plan: null
    pr: null
  - id: '2.2'
    description: Add tests
    status: blocked
    plan: null
    pr: null

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Foundation (1 PR)

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Set up project structure | done | - | #100 |
| 1.2 | Add core types | in-progress | #200 | - |
| 1.3 | Add utility functions | pending | - | - |

### Phase 2: Implementation (1 PR)

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Implement main feature | pending | - | - |
| 2.2 | Add tests | blocked | - | - |
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


def test_update_pending_step_with_plan() -> None:
    """Update a pending step with a plan reference using --plan."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--plan", "#6464"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 6423
    assert output["node_id"] == "1.3"
    assert output["previous_plan"] is None
    assert output["new_plan"] == "#6464"
    assert output["url"] == "https://github.com/test/repo/issues/6423"

    # Verify the body was updated with frontmatter
    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert "#6464" in updated_body
    assert "status: in_progress" in updated_body


def test_update_step_with_pr_requires_plan() -> None:
    """Setting --pr without --plan returns an error."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.2", "--pr", "#500"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "plan_required_with_pr"


def test_clear_pr_reference() -> None:
    """Clear a step's PR reference by passing empty string."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.1", "--pr", ""],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["6423", "--node", "9.9", "--plan", "#123"],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["999", "--node", "1.1", "--pr", "#123", "--plan", ""],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["6423", "--node", "1.1", "--pr", "#123", "--plan", ""],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["6423", "--node", "2.1", "--plan", "#300"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["node_id"] == "2.1"
    assert output["previous_plan"] is None
    assert output["new_plan"] == "#300"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "#300" in updated_body


def test_update_with_frontmatter() -> None:
    """Update step when frontmatter is present updates YAML."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#999", "--plan", ""],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["6423", "--node", "1.2", "--pr", "#777", "--plan", ""],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["6423", "--node", "1.3", "--pr", "#500", "--plan", "", "--status", "done"],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["6697", "--node", "1.2", "--node", "1.3", "--node", "2.1", "--plan", "#6759"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 6697
    assert output["new_plan"] == "#6759"
    assert output["url"] == "https://github.com/test/repo/issues/6697"

    assert "nodes" in output
    assert len(output["nodes"]) == 3

    step_1_2 = next(s for s in output["nodes"] if s["node_id"] == "1.2")
    assert step_1_2["success"] is True
    assert step_1_2["previous_plan"] == "#200"

    step_1_3 = next(s for s in output["nodes"] if s["node_id"] == "1.3")
    assert step_1_3["success"] is True
    assert step_1_3["previous_plan"] is None

    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert updated_body.count("#6759") == 3


def test_update_multiple_steps_partial_failure() -> None:
    """Multi-step update rejected upfront when any step is missing."""
    issue = _make_issue(6697, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6697", "--node", "1.2", "--node", "9.9", "--node", "2.1", "--plan", "#6759"],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
    from erk.cli.commands.exec.scripts.update_objective_node import _build_output

    results: list[dict[str, object]] = [
        {"node_id": "1.2", "success": True, "previous_plan": "#200", "previous_pr": None},
        {"node_id": "1.3", "success": False, "error": "replacement_failed"},
    ]
    output = _build_output(
        issue_number=6697,
        node=("1.2", "1.3"),
        plan_value="#6759",
        pr_value=None,
        url="https://github.com/test/repo/issues/6697",
        results=results,
        include_body=False,
        updated_body=None,
    )

    # AND semantics: success=false because step 1.3 failed
    assert output["success"] is False
    assert output["issue_number"] == 6697
    nodes = output["nodes"]
    assert isinstance(nodes, list)
    assert len(nodes) == 2


def test_update_multiple_steps_same_phase() -> None:
    """Update multiple steps within the same phase."""
    issue = _make_issue(6697, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6697", "--node", "1.1", "--node", "1.2", "--node", "1.3", "--pr", "#555", "--plan", ""],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["6423", "--node", "1.3", "--plan", "#6464"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    # Should use legacy format (no "steps" array)
    assert "nodes" not in output
    assert output["success"] is True
    assert output["node_id"] == "1.3"
    assert output["previous_plan"] is None
    assert output["new_plan"] == "#6464"


def test_missing_ref_error() -> None:
    """Error when neither --plan nor --pr is provided."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "missing_ref"


def test_include_body_flag_single_step() -> None:
    """--include-body includes updated_body in JSON output for single step."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500", "--plan", "", "--include-body"],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["6697", "--node", "1.2", "--node", "1.3", "--pr", "#555", "--plan", "", "--include-body"],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["6423", "--node", "1.3", "--pr", "#500", "--plan", ""],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "updated_body" not in output


def test_none_plan_preserves_when_pr_set() -> None:
    """_replace_node_refs_in_body with new_plan=None preserves plan when PR is set."""
    from erk.cli.commands.exec.scripts.update_objective_node import _replace_node_refs_in_body

    # Step 1.2 has plan=#200
    result = _replace_node_refs_in_body(
        ROADMAP_BODY_V2, "1.2", new_plan=None, new_pr="#500", explicit_status=None
    )

    assert result is not None
    # Plan should be preserved (#200 still present) because new_plan=None means preserve
    assert "#200" in result
    assert "#500" in result
    assert "status: in_progress" in result


def test_none_plan_preserves_when_no_pr() -> None:
    """_replace_node_refs_in_body with new_plan=None preserves plan when PR not set."""
    from erk.cli.commands.exec.scripts.update_objective_node import _replace_node_refs_in_body

    # Step 1.2 has plan=#200
    result = _replace_node_refs_in_body(
        ROADMAP_BODY_V2, "1.2", new_plan=None, new_pr=None, explicit_status=None
    )

    assert result is not None
    # Plan should be preserved because PR is not being set
    assert "#200" in result


def test_none_pr_preserves_existing_value() -> None:
    """_replace_node_refs_in_body with new_pr=None preserves existing PR."""
    from erk.cli.commands.exec.scripts.update_objective_node import _replace_node_refs_in_body

    # Step 1.1 has pr=#100
    result = _replace_node_refs_in_body(
        ROADMAP_BODY_V2, "1.1", new_plan=None, new_pr=None, explicit_status="planning"
    )

    assert result is not None
    # PR should be preserved
    assert "#100" in result
    assert "status: planning" in result


def test_empty_string_clears_value() -> None:
    """_replace_node_refs_in_body with empty string clears to null."""
    from erk.cli.commands.exec.scripts.update_objective_node import _replace_node_refs_in_body

    # Step 1.2 has plan=#200, pr=null
    result = _replace_node_refs_in_body(
        ROADMAP_BODY_V2, "1.2", new_plan="", new_pr=None, explicit_status=None
    )

    assert result is not None
    # After clearing plan and preserving pr=null, status should be pending
    assert "status: pending" in result


def test_planning_status_via_explicit_status() -> None:
    """update-objective-node with --status planning sets planning status."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#200", "--plan", "", "--status", "planning"],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        ["6423", "--node", "9.9", "--pr", "#500", "--plan", "", "--include-body"],
        obj=ErkContext.for_test(github_issues=fake_gh),
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

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Set up project structure | done | - | #100 |
"""
    issue = _make_issue(6423, body_without_metadata)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.1", "--plan", "#6464"],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
    plan: null
    pr: '#100'
  - id: '1.2'
    description: Add core types
    status: in_progress
    plan: '#200'
    pr: null
  - id: '1.3'
    description: Add utility functions
    status: pending
    plan: null
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

### Phase 1: Foundation (1 PR)

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Set up project structure | done | - | #100 |
| 1.2 | Add core types | in-progress | #200 | - |
| 1.3 | Add utility functions | pending | - | - |

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
        ["6423", "--node", "1.3", "--plan", "#6464"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    # Body frontmatter should be updated
    updated_body = fake_gh.updated_bodies[0][1]
    assert "plan: '#6464'" in updated_body or 'plan: "#6464"' in updated_body

    # Comment table should also be updated
    assert len(fake_gh.updated_comments) == 1
    updated_comment = fake_gh.updated_comments[0][1]
    assert "#6464" in updated_comment
    assert "| in-progress |" in updated_comment


def test_v2_pr_without_plan_returns_error() -> None:
    """v2 format: setting PR without plan returns error requiring --plan."""
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

    # Step 1.2 has plan=#200. Setting only --pr should now error.
    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.2", "--pr", "#777"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "plan_required_with_pr"


def test_v2_no_comment_update_when_no_header() -> None:
    """When no objective-header exists, only body is updated (no comment)."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--plan", "#6464"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Body should be updated
    assert len(fake_gh.updated_bodies) == 1

    # No comment updates should happen
    assert len(fake_gh.updated_comments) == 0


def test_replace_table_in_text_basic() -> None:
    """_replace_table_in_text updates a step's plan/PR cells in markdown text."""
    from erk.cli.commands.exec.scripts.update_objective_node import _replace_table_in_text

    text = """\
| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Set up project | done | - | #100 |
| 1.2 | Add core types | pending | - | - |
"""
    result = _replace_table_in_text(text, "1.2", new_plan="#200", new_pr=None, explicit_status=None)
    assert result is not None
    assert "| in-progress | #200 | - |" in result


def test_replace_table_in_text_not_found() -> None:
    """_replace_table_in_text returns None when step not found."""
    from erk.cli.commands.exec.scripts.update_objective_node import _replace_table_in_text

    text = "| 1.1 | desc | done | - | #100 |"
    result = _replace_table_in_text(text, "9.9", new_plan="#200", new_pr=None, explicit_status=None)
    assert result is None


def test_replace_table_in_text_preserves_plan_when_pr_set() -> None:
    """_replace_table_in_text preserves plan when PR is explicitly set and plan is None."""
    from erk.cli.commands.exec.scripts.update_objective_node import _replace_table_in_text

    text = """\
| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Set up project | in-progress | #200 | - |
"""
    result = _replace_table_in_text(text, "1.1", new_plan=None, new_pr="#500", explicit_status=None)
    assert result is not None
    assert "| #200 | #500 |" in result
    assert "| in-progress |" in result


def test_replace_table_in_text_preserves_plan_when_no_pr() -> None:
    """_replace_table_in_text preserves plan when PR is not set."""
    from erk.cli.commands.exec.scripts.update_objective_node import _replace_table_in_text

    text = """\
| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Set up project | in-progress | #200 | - |
"""
    result = _replace_table_in_text(text, "1.1", new_plan=None, new_pr=None, explicit_status=None)
    assert result is not None
    assert "#200" in result


def test_update_step_with_pr_and_plan_preserved() -> None:
    """Pass --pr and --plan together: both present in result, status in_progress."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.2", "--pr", "#500", "--plan", "#200"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["previous_plan"] == "#200"
    assert output["new_plan"] == "#200"
    assert output["new_pr"] == "#500"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "#500" in updated_body
    assert "#200" in updated_body
    assert "status: in_progress" in updated_body


def test_update_step_with_pr_and_plan_cleared() -> None:
    """Pass --pr and --plan '' together: plan cleared, PR set, status in_progress."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.2", "--pr", "#500", "--plan", ""],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["previous_plan"] == "#200"
    assert output["new_plan"] is None
    assert output["new_pr"] == "#500"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "#500" in updated_body
    assert "status: in_progress" in updated_body


def test_pr_without_plan_returns_error() -> None:
    """Pass only --pr without --plan: returns error response."""
    issue = _make_issue(6423, ROADMAP_BODY_V2)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_objective_node,
        ["6423", "--node", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "plan_required_with_pr"
    assert "--plan" in output["message"]

    # No body updates should have occurred
    assert len(fake_gh.updated_bodies) == 0
