"""Unit tests for objective-link-pr command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_link_pr import objective_link_pr
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.impl_folder import get_impl_dir
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github_issues import FakeGitHubIssues

BRANCH = "test/branch"
"""Test branch name used across tests."""

ROADMAP_BODY = """\
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


def _write_ref_json(
    impl_dir: Path,
    *,
    objective_id: int | None,
    node_ids: list[str] | None,
) -> None:
    """Write a ref.json file in the given impl_dir."""
    impl_dir.mkdir(parents=True, exist_ok=True)
    ref_data = {
        "provider": "github-draft-pr",
        "plan_id": "42",
        "url": "https://github.com/test/repo/pull/42",
        "created_at": "2025-01-01T00:00:00Z",
        "synced_at": "2025-01-01T00:00:00Z",
        "title": "Test Plan",
        "objective_id": objective_id,
        "node_ids": node_ids,
    }
    (impl_dir / "ref.json").write_text(json.dumps(ref_data), encoding="utf-8")


def test_no_impl_dir(tmp_path: Path) -> None:
    """Returns no_impl_dir when impl dir doesn't exist."""
    runner = CliRunner()
    git = FakeGit(current_branches={tmp_path: BRANCH})

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "42"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["reason"] == "no_impl_dir"


def test_no_plan_ref(tmp_path: Path) -> None:
    """Returns no_plan_ref when impl dir exists but has no ref.json."""
    impl_dir = get_impl_dir(tmp_path, branch_name=BRANCH)
    impl_dir.mkdir(parents=True)
    git = FakeGit(current_branches={tmp_path: BRANCH})

    runner = CliRunner()

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "42"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["reason"] == "no_plan_ref"


def test_no_objective_id(tmp_path: Path) -> None:
    """Returns no_objective_id when ref.json lacks objective_id."""
    _write_ref_json(get_impl_dir(tmp_path, branch_name=BRANCH), objective_id=None, node_ids=["1.1"])
    git = FakeGit(current_branches={tmp_path: BRANCH})

    runner = CliRunner()

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "42"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["reason"] == "no_objective_id"


def test_no_node_ids(tmp_path: Path) -> None:
    """Returns no_node_ids when ref.json lacks node_ids."""
    _write_ref_json(get_impl_dir(tmp_path, branch_name=BRANCH), objective_id=100, node_ids=None)
    git = FakeGit(current_branches={tmp_path: BRANCH})

    runner = CliRunner()

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "42"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["reason"] == "no_node_ids"


def test_empty_node_ids(tmp_path: Path) -> None:
    """Returns no_node_ids when ref.json has empty node_ids list."""
    _write_ref_json(get_impl_dir(tmp_path, branch_name=BRANCH), objective_id=100, node_ids=[])
    git = FakeGit(current_branches={tmp_path: BRANCH})

    runner = CliRunner()

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "42"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["reason"] == "no_node_ids"


def test_issue_not_found(tmp_path: Path) -> None:
    """Returns issue_not_found when objective issue doesn't exist."""
    _write_ref_json(get_impl_dir(tmp_path, branch_name=BRANCH), objective_id=999, node_ids=["1.1"])
    git = FakeGit(current_branches={tmp_path: BRANCH})
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "42"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git, github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["reason"] == "issue_not_found"
    assert output["objective_id"] == 999


def test_successful_single_node_link(tmp_path: Path) -> None:
    """Successfully links PR to a single roadmap node."""
    _write_ref_json(get_impl_dir(tmp_path, branch_name=BRANCH), objective_id=50, node_ids=["1.2"])
    git = FakeGit(current_branches={tmp_path: BRANCH})
    issue = _make_issue(50, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={50: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "42"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git, github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["objective_id"] == 50
    assert output["pr_number"] == 42
    assert len(output["nodes"]) == 1
    assert output["nodes"][0]["node_id"] == "1.2"
    assert output["nodes"][0]["success"] is True

    # Verify the issue body was updated with the PR reference
    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert "'#42'" in updated_body or "pr: '#42'" in updated_body


def test_node_not_found_in_roadmap(tmp_path: Path) -> None:
    """Reports failure for a node_id that doesn't exist in the roadmap."""
    _write_ref_json(get_impl_dir(tmp_path, branch_name=BRANCH), objective_id=50, node_ids=["9.9"])
    git = FakeGit(current_branches={tmp_path: BRANCH})
    issue = _make_issue(50, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={50: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "42"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git, github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["nodes"][0]["node_id"] == "9.9"
    assert output["nodes"][0]["success"] is False
    assert output["nodes"][0]["error"] == "node_not_found"

    # No body updates should happen
    assert len(fake_gh.updated_bodies) == 0


def test_no_roadmap_block(tmp_path: Path) -> None:
    """Reports failure when issue has no roadmap metadata block."""
    _write_ref_json(get_impl_dir(tmp_path, branch_name=BRANCH), objective_id=50, node_ids=["1.1"])
    git = FakeGit(current_branches={tmp_path: BRANCH})
    issue = _make_issue(50, NO_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={50: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "42"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git, github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["nodes"][0]["error"] == "no_roadmap"


def test_impl_context_scoped_layout(tmp_path: Path) -> None:
    """Finds ref.json in .erk/impl-context/ scoped layout."""
    branch = "my-branch"
    _write_ref_json(get_impl_dir(tmp_path, branch_name=branch), objective_id=50, node_ids=["1.3"])
    git = FakeGit(current_branches={tmp_path: branch})
    issue = _make_issue(50, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={50: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "77"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git, github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 77
    assert output["nodes"][0]["node_id"] == "1.3"
    assert output["nodes"][0]["success"] is True


def test_comment_roadmap_rerendered(tmp_path: Path) -> None:
    """Re-renders comment roadmap when objective-header has comment_id."""
    body_with_header = (
        "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->\n"
        "<!-- erk:metadata-block:objective-header -->\n"
        "<details>\n"
        "<summary><code>objective-header</code></summary>\n"
        "\n"
        "```yaml\n"
        "\n"
        "objective_comment_id: 5001\n"
        "\n"
        "```\n"
        "\n"
        "</details>\n"
        "<!-- /erk:metadata-block:objective-header -->\n"
        "\n"
        "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->\n"
        "<!-- erk:metadata-block:objective-roadmap -->\n"
        "<details>\n"
        "<summary><code>objective-roadmap</code></summary>\n"
        "\n"
        "```yaml\n"
        "\n"
        "schema_version: '2'\n"
        "steps:\n"
        "  - id: '1.1'\n"
        "    description: Set up project structure\n"
        "    status: in_progress\n"
        "    pr: null\n"
        "\n"
        "```\n"
        "\n"
        "</details>\n"
        "<!-- /erk:metadata-block:objective-roadmap -->\n"
    )
    _write_ref_json(get_impl_dir(tmp_path, branch_name=BRANCH), objective_id=50, node_ids=["1.1"])
    git = FakeGit(current_branches={tmp_path: BRANCH})
    issue = _make_issue(50, body_with_header)

    comment = IssueComment(
        id=5001,
        body=(
            "## Roadmap\n\n"
            "<!-- erk:roadmap-table -->\n"
            "| Node | Description | Status | PR |\n"
            "|------|-------------|--------|----|\n"
            "| 1.1 | Set up project structure | in-progress | - |\n"
            "<!-- /erk:roadmap-table -->"
        ),
        url="https://github.com/test/repo/issues/50#issuecomment-5001",
        author="testuser",
    )
    fake_gh = FakeGitHubIssues(
        issues={50: issue},
        comments_with_urls={50: [comment]},
    )
    runner = CliRunner()

    result = runner.invoke(
        objective_link_pr,
        ["--pr-number", "200"],
        obj=ErkContext.for_test(cwd=tmp_path, git=git, github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify body was updated
    assert len(fake_gh.updated_bodies) == 1
    # Comment should be updated via rerender
    assert len(fake_gh.updated_comments) == 1
    comment_id, comment_body = fake_gh.updated_comments[0]
    assert comment_id == 5001
    assert "#200" in comment_body
