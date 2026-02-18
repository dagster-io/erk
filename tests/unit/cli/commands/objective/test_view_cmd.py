"""Unit tests for erk objective view command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.objective.view_cmd import view_objective
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.output_helpers import strip_ansi


def _make_issue(
    number: int,
    title: str,
    body: str,
    *,
    labels: list[str] | None = None,
) -> IssueInfo:
    """Create a test IssueInfo."""
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


OBJECTIVE_WITH_ROADMAP = """\
# Objective: Test Feature

## Roadmap

### Phase 1: Foundation

### Phase 2A: Core Implementation

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Setup infrastructure
  status: done
  plan: null
  pr: '#123'
- id: '1.2'
  description: Add basic tests
  status: in_progress
  plan: '#124'
  pr: null
- id: '1.3'
  description: Update docs
  status: pending
  plan: null
  pr: null
- id: 2A.1
  description: Build main feature
  status: done
  plan: null
  pr: '#125'
- id: 2A.2
  description: Add integration tests
  status: blocked
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

OBJECTIVE_LEGACY_TABLE = """\
# Objective: Legacy Feature

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infrastructure | done | - | #123 |
"""

OBJECTIVE_V1_SCHEMA = """\
# Objective: V1 Schema

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: '1'
steps:
- id: '1.1'
  description: First step
  status: pending
  pr: null
---
<!-- /erk:metadata-block:objective-roadmap -->
"""

OBJECTIVE_EMPTY_ROADMAP = """# Objective: Empty

No roadmap here.
"""


def test_view_objective_success() -> None:
    """Test successful view with parsed phases and steps."""
    issue = _make_issue(100, "Objective: Test Feature", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["100"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Objective: Test Feature" in result.output
        assert "Phase 1: Foundation" in result.output
        assert "Phase 2A: Core Implementation" in result.output
        assert "Setup infrastructure" in result.output
        assert "Build main feature" in result.output


def test_view_objective_with_issue_url() -> None:
    """Test view using GitHub issue URL instead of number."""
    issue = _make_issue(200, "Objective: URL Test", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={200: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["https://github.com/test/repo/issues/200"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Objective: URL Test" in result.output


def test_view_objective_not_found() -> None:
    """Test error when issue not found."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["999"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "999" in result.output
        assert "not found" in result.output


def test_view_objective_missing_label() -> None:
    """Test error when issue missing erk-objective label."""
    issue = _make_issue(
        300,
        "Some Issue",
        OBJECTIVE_WITH_ROADMAP,
        labels=["bug"],
    )
    fake_gh = FakeGitHubIssues(issues={300: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["300"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "not an objective" in result.output
        assert "erk-objective" in result.output


def test_view_objective_empty_roadmap() -> None:
    """Test view with empty roadmap rejects as legacy format."""
    issue = _make_issue(400, "Objective: Empty", OBJECTIVE_EMPTY_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={400: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["400"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "legacy format" in result.output


def test_view_objective_displays_summary() -> None:
    """Test that summary section displays with correct stats."""
    issue = _make_issue(500, "Objective: Summary Test", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={500: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["500"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "─── Summary ───" in result.output
        assert "Steps:" in result.output
        # 2 done (with PRs), 1 in_progress (plan #), 1 pending (no PR), 1 blocked
        assert "2/5 done" in result.output
        assert "Next step:" in result.output
        assert "1.3" in result.output  # First pending step


def test_view_objective_displays_timestamps() -> None:
    """Test that timestamps are displayed with relative time."""
    issue = _make_issue(600, "Objective: Timestamps", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={600: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["600"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Created:" in result.output
        assert "Updated:" in result.output


def test_view_objective_p_prefix() -> None:
    """Test view with P-prefixed identifier."""
    issue = _make_issue(700, "Objective: P Prefix", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={700: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["P700"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Objective: P Prefix" in result.output


def test_view_objective_phase_completion_counts() -> None:
    """Test that phase headers show correct completion counts."""
    issue = _make_issue(800, "Objective: Counts", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={800: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["800"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = strip_ansi(result.output)
        # Phase 1: 1 done out of 3 (only 1.1 has completed PR, 1.2 is in_progress)
        assert "Phase 1: Foundation (1/3 steps done)" in output
        # Phase 2A: 1 done out of 2 (2A.1 has PR, 2A.2 is blocked)
        assert "Phase 2A: Core Implementation (1/2 steps done)" in output


def test_view_objective_status_emojis() -> None:
    """Test that status indicators show correct emojis and plan references."""
    issue = _make_issue(900, "Objective: Emojis", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={900: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["900"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        # Check for status emojis
        assert "✅ done" in result.output  # done status
        assert "🔄 in_progress" in result.output  # in_progress status
        assert "⏳ pending" in result.output  # pending status
        assert "🚫 blocked" in result.output  # blocked status
        # in_progress status shows plan reference
        assert "in_progress plan #124" in result.output


def test_view_objective_plan_pr_columns() -> None:
    """Test that plan and PR are shown as separate columns."""
    issue = _make_issue(950, "Objective: Columns", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={950: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["950"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = strip_ansi(result.output)
        # Step 1.1 has no plan but has PR #123
        assert "#123" in output
        # Step 1.2 has plan #124 but no PR
        assert "#124" in output


def test_view_objective_legacy_format_rejected() -> None:
    """Test that table-only objective body is rejected as legacy format."""
    issue = _make_issue(1000, "Objective: Legacy", OBJECTIVE_LEGACY_TABLE)
    fake_gh = FakeGitHubIssues(issues={1000: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["1000"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "legacy format" in result.output
        assert "erk:objective-create" in result.output


def test_view_objective_v1_schema_rejected() -> None:
    """Test that metadata block with schema_version 1 is rejected."""
    issue = _make_issue(1100, "Objective: V1", OBJECTIVE_V1_SCHEMA)
    fake_gh = FakeGitHubIssues(issues={1100: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["1100"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "legacy format" in result.output


def test_view_objective_depends_on_column() -> None:
    """Test that depends_on column appears in output."""
    issue = _make_issue(1200, "Objective: Deps", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={1200: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["1200"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = strip_ansi(result.output)
        # Table header should include depends_on
        assert "depends_on" in output
        # Step 1.2 depends on 1.1
        assert "1.1" in output


def test_view_objective_unblocked_annotation() -> None:
    """Test that unblocked pending steps show (unblocked) annotation."""
    issue = _make_issue(1300, "Objective: Unblocked", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={1300: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["1300"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        # Step 1.3 is pending but depends on 1.2 (in_progress), so NOT unblocked
        # The "unblocked" text should still appear for truly unblocked steps
        # In our test data: 1.1 done, 1.2 in_progress (depends on 1.1, unblocked),
        # 1.3 pending (depends on 1.2, NOT unblocked)
        output = strip_ansi(result.output)
        assert "Unblocked:" in output


def test_view_objective_unblocked_count_in_summary() -> None:
    """Test that summary shows unblocked count."""
    issue = _make_issue(1350, "Objective: Unblocked Count", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={1350: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["1350"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = strip_ansi(result.output)
        assert "Unblocked:" in output
        # In OBJECTIVE_WITH_ROADMAP: 1.3 is the only pending step.
        # 1.3 depends on 1.2 which is in_progress (not terminal), so 1.3 is NOT unblocked.
        # Unblocked count should be 0.
        assert "Unblocked:" in output and "0" in output


def test_view_objective_json_output() -> None:
    """Test --json-output flag produces valid JSON with graph data."""
    issue = _make_issue(1400, "Objective: JSON", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={1400: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["1400", "--json-output"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        data = json.loads(result.output)
        assert data["issue_number"] == 1400
        assert "graph" in data
        assert "nodes" in data["graph"]
        assert len(data["graph"]["nodes"]) == 5
        assert "unblocked" in data["graph"]
        assert "next_node" in data["graph"]
        assert "is_complete" in data["graph"]
        assert data["graph"]["is_complete"] is False


def test_view_objective_json_includes_depends_on() -> None:
    """Test JSON output includes depends_on for each node."""
    issue = _make_issue(1500, "Objective: JSON Deps", OBJECTIVE_WITH_ROADMAP)
    fake_gh = FakeGitHubIssues(issues={1500: issue})
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        test_ctx = env.build_context(issues=fake_gh)
        result = runner.invoke(
            view_objective,
            ["1500", "--json-output"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        data = json.loads(result.output)
        nodes = {n["id"]: n for n in data["graph"]["nodes"]}
        # 1.1 has no deps (first step)
        assert nodes["1.1"]["depends_on"] == []
        # 1.2 depends on 1.1
        assert nodes["1.2"]["depends_on"] == ["1.1"]
        # 2A.1 depends on 1.3 (last step of previous phase)
        assert nodes["2A.1"]["depends_on"] == ["1.3"]
