"""Tests for objective inspect command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo

OBJECTIVE_BODY = """# Objective: Add caching

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml

schema_version: '2'
steps:
  - id: '1.1'
    description: Setup infra
    status: done
    plan: null
    pr: '#100'
  - id: '1.2'
    description: Add tests
    status: pending
    plan: null
    pr: null
  - id: '2.1'
    description: Build feature
    status: pending
    plan: null
    pr: null

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | done | - | #100 |
| 1.2 | Add tests | pending | - | - |

### Phase 2: Core

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Build feature | pending | - | - |
"""

ALL_DONE_BODY = """# Objective: Done

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml

schema_version: '2'
steps:
  - id: '1.1'
    description: Setup infra
    status: done
    plan: null
    pr: '#100'

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | done | - | #100 |
"""

NOW = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


def _make_issue(number: int, body: str, *, title: str = "Add caching") -> IssueInfo:
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=NOW,
        updated_at=NOW,
        author="testuser",
    )


def test_inspect_shows_roadmap_with_unblocked_nodes() -> None:
    """Test human-readable output shows roadmap with graph annotations."""
    runner = CliRunner()
    issues = FakeGitHubIssues(issues={42: _make_issue(42, OBJECTIVE_BODY)})
    ctx = ErkContext.for_test(github_issues=issues)

    result = runner.invoke(cli, ["objective", "inspect", "42"], obj=ctx)

    assert result.exit_code == 0
    assert "Dependency Graph" in result.output
    assert "1.1" in result.output
    assert "1.2" in result.output
    assert "2.1" in result.output
    assert "unblocked" in result.output.lower()
    assert "Next node" in result.output


def test_inspect_json_output() -> None:
    """Test JSON output includes graph structure."""
    runner = CliRunner()
    issues = FakeGitHubIssues(issues={42: _make_issue(42, OBJECTIVE_BODY)})
    ctx = ErkContext.for_test(github_issues=issues)

    result = runner.invoke(cli, ["objective", "inspect", "42", "--json-output"], obj=ctx)

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["issue_number"] == 42
    assert "graph" in data
    assert "nodes" in data["graph"]
    assert len(data["graph"]["nodes"]) == 3
    assert data["graph"]["next_node"] == "1.2"
    assert "1.2" in data["graph"]["unblocked"]
    assert data["graph"]["is_complete"] is False


def test_inspect_all_done() -> None:
    """Test inspect with all-done objective shows complete."""
    runner = CliRunner()
    issues = FakeGitHubIssues(issues={42: _make_issue(42, ALL_DONE_BODY)})
    ctx = ErkContext.for_test(github_issues=issues)

    result = runner.invoke(cli, ["objective", "inspect", "42"], obj=ctx)

    assert result.exit_code == 0
    assert "Complete" in result.output or "Next node" in result.output


def test_inspect_json_all_done() -> None:
    """Test JSON output for all-done objective."""
    runner = CliRunner()
    issues = FakeGitHubIssues(issues={42: _make_issue(42, ALL_DONE_BODY)})
    ctx = ErkContext.for_test(github_issues=issues)

    result = runner.invoke(cli, ["objective", "inspect", "42", "--json-output"], obj=ctx)

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["graph"]["is_complete"] is True
    assert data["graph"]["next_node"] is None


def test_inspect_missing_objective() -> None:
    """Test error when objective issue doesn't exist."""
    runner = CliRunner()
    issues = FakeGitHubIssues(issues={})
    ctx = ErkContext.for_test(github_issues=issues)

    result = runner.invoke(cli, ["objective", "inspect", "999"], obj=ctx)

    assert result.exit_code == 1
    assert "not found" in result.output


def test_inspect_alias_i_works() -> None:
    """Test that 'i' alias works for inspect command."""
    runner = CliRunner()
    issues = FakeGitHubIssues(issues={42: _make_issue(42, OBJECTIVE_BODY)})
    ctx = ErkContext.for_test(github_issues=issues)

    result = runner.invoke(cli, ["objective", "i", "42"], obj=ctx)

    assert result.exit_code == 0
    assert "Dependency Graph" in result.output


def test_inspect_requires_objective_ref() -> None:
    """Test inspect requires OBJECTIVE_REF argument."""
    runner = CliRunner()

    result = runner.invoke(cli, ["objective", "inspect"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_inspect_json_includes_depends_on() -> None:
    """Test JSON output includes depends_on for each node."""
    runner = CliRunner()
    issues = FakeGitHubIssues(issues={42: _make_issue(42, OBJECTIVE_BODY)})
    ctx = ErkContext.for_test(github_issues=issues)

    result = runner.invoke(cli, ["objective", "inspect", "42", "--json-output"], obj=ctx)

    assert result.exit_code == 0
    data = json.loads(result.output)
    nodes = {n["id"]: n for n in data["graph"]["nodes"]}
    # 1.1 has no deps
    assert nodes["1.1"]["depends_on"] == []
    # 1.2 depends on 1.1
    assert nodes["1.2"]["depends_on"] == ["1.1"]
    # 2.1 depends on 1.2 (last step of previous phase)
    assert nodes["2.1"]["depends_on"] == ["1.2"]
