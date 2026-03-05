"""Tests for objective-plan-setup exec command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_plan_setup import objective_plan_setup
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo

VALID_OBJECTIVE_BODY = """\
# Objective: Test Feature

## Roadmap

### Phase 1: Foundation

### Phase 2: Core Implementation

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
  status: pending
  plan: null
  pr: null
- id: '2.1'
  description: Build main feature
  status: pending
  plan: null
  pr: null
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


def test_success_with_valid_objective(tmp_path: Path) -> None:
    issue = _make_issue(100, "Test Objective", VALID_OBJECTIVE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    ctx = ErkContext.for_test(
        github=FakeGitHub(issues_gateway=fake_gh),
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_plan_setup,
        ["100", "--session-id", "test-session"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    assert output["success"] is True
    assert output["objective"]["number"] == 100
    assert output["objective"]["title"] == "Test Objective"
    assert output["objective"]["state"] == "OPEN"
    assert "erk-objective" in output["objective"]["labels"]
    assert output["roadmap"]["summary"]["total_nodes"] == 3
    assert output["roadmap"]["summary"]["done"] == 1
    assert output["roadmap"]["summary"]["pending"] == 2
    assert output["roadmap"]["next_node"]["id"] == "1.2"
    assert output["roadmap"]["all_complete"] is False
    assert output["validation"]["passed"] is True
    assert output["marker_created"] is True
    assert output["warnings"] == []


def test_not_found_error(tmp_path: Path) -> None:
    fake_gh = FakeGitHubIssues()
    ctx = ErkContext.for_test(
        github=FakeGitHub(issues_gateway=fake_gh),
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_plan_setup,
        ["999", "--session-id", "test-session"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "not_found"


def test_is_plan_error(tmp_path: Path) -> None:
    issue = _make_issue(200, "Some Plan", "body", labels=["erk-plan"])
    fake_gh = FakeGitHubIssues(issues={200: issue})
    ctx = ErkContext.for_test(
        github=FakeGitHub(issues_gateway=fake_gh),
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_plan_setup,
        ["200", "--session-id", "test-session"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "is_plan"


def test_warning_for_missing_label(tmp_path: Path) -> None:
    issue = _make_issue(300, "No Label Issue", VALID_OBJECTIVE_BODY, labels=["bug"])
    fake_gh = FakeGitHubIssues(issues={300: issue})
    ctx = ErkContext.for_test(
        github=FakeGitHub(issues_gateway=fake_gh),
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_plan_setup,
        ["300", "--session-id", "test-session"],
        obj=ctx,
    )

    # Still succeeds despite missing label (warning only)
    # Exit code depends on validation — missing label fails check
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["warnings"]) == 1
    assert "erk-objective" in output["warnings"][0]


def test_marker_file_created(tmp_path: Path) -> None:
    issue = _make_issue(400, "Marker Test", VALID_OBJECTIVE_BODY)
    fake_gh = FakeGitHubIssues(issues={400: issue})
    ctx = ErkContext.for_test(
        github=FakeGitHub(issues_gateway=fake_gh),
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_plan_setup,
        ["400", "--session-id", "marker-test-session"],
        obj=ctx,
    )

    assert result.exit_code == 0
    marker_path = tmp_path / ".erk" / "scratch" / "sessions" / "marker-test-session" / "objective-context.marker"
    assert marker_path.exists()
    assert marker_path.read_text(encoding="utf-8") == "400"


def test_roadmap_free_objective(tmp_path: Path) -> None:
    body = "# Objective: Simple\n\nNo roadmap here."
    issue = _make_issue(500, "Simple Objective", body)
    fake_gh = FakeGitHubIssues(issues={500: issue})
    ctx = ErkContext.for_test(
        github=FakeGitHub(issues_gateway=fake_gh),
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        objective_plan_setup,
        ["500", "--session-id", "test-session"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["roadmap"]["phases"] == []
    assert output["roadmap"]["summary"] == {}
