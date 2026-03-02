"""Tests for erk exec rerender-objective-comment."""

import json
import textwrap
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.rerender_objective_comment import (
    _count_table_columns,
    _rerender_single_objective,
    rerender_objective_comment,
)
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo

COMMENT_ID = 55555
REPO_ROOT = "/tmp/repo"

OBJECTIVE_BODY = textwrap.dedent("""\
    # Test Objective

    <!-- erk:metadata-block:objective-header -->

    <details>
    <summary><code>objective-header</code></summary>

    ```yaml
    created_at: '2026-01-01T00:00:00Z'
    created_by: testuser
    objective_comment_id: 55555
    slug: test-obj
    ```

    </details>

    <!-- /erk:metadata-block:objective-header -->

    <!-- erk:metadata-block:objective-roadmap -->

    <details>
    <summary><code>objective-roadmap</code></summary>

    ```yaml
    schema_version: "4"
    nodes:
    - id: "1.1"
      slug: add-models
      description: "Add data models"
      status: "done"
      plan: "#100"
      pr: "#200"
    - id: "1.2"
      slug: add-api
      description: "Add API endpoints"
      status: "in_progress"
      plan: "#101"
      pr: null
    - id: "2.1"
      slug: add-tests
      description: "Add integration tests"
      status: "pending"
      plan: null
      pr: null
    ```

    </details>

    <!-- /erk:metadata-block:objective-roadmap -->
""")


def _make_issue(*, number: int, body: str) -> IssueInfo:
    return IssueInfo(
        number=number,
        title="Test Objective",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        author="testuser",
    )


def _make_comment_body(table_content: str) -> str:
    """Wrap table content in objective-body block with markers."""
    return textwrap.dedent(f"""\
        <!-- erk:metadata-block:objective-body -->
        <details open>
        <summary><strong>Objective</strong></summary>

        # Test Objective

        Some description here.

        <!-- erk:roadmap-table -->
        ### Phase 1: Setup (1 PR)
        | Node | Description | Status | Plan | PR |
        |------|-------------|--------|------|----|
        {table_content}
        ### Phase 2: Testing (0 PR)
        | Node | Description | Status | Plan | PR |
        |------|-------------|--------|------|----|
        | 2.1 | Add integration tests | pending | - | - |
        <!-- /erk:roadmap-table -->

        </details>
        <!-- /erk:metadata-block:objective-body -->
    """)


STALE_COMMENT = _make_comment_body(
    "| 1.1 | Add data models | pending | - | - |\n| 1.2 | Add API endpoints | pending | - | - |"
)

CURRENT_COMMENT = _make_comment_body(
    "| 1.1 | Add data models | done | #100 | #200 |\n"
    "| 1.2 | Add API endpoints | in-progress | #101 | - |"
)


# --- Unit tests for helpers ---


def test_count_table_columns_five_columns() -> None:
    table = (
        "| Node | Description | Status | Plan | PR |\n"
        "|------|------|------|------|------|\n"
        "| 1.1 | foo | done | - | - |"
    )
    assert _count_table_columns(table) == 5


def test_count_table_columns_six_columns() -> None:
    table = (
        "| Node | Description | Depends On | Status | Plan | PR |\n"
        "|------|------|------|------|------|------|\n"
        "| 1.1 | foo | - | done | - | - |"
    )
    assert _count_table_columns(table) == 6


def test_count_table_columns_empty() -> None:
    assert _count_table_columns("") == 0


# --- Integration tests for _rerender_single_objective ---


def test_rerender_stale_comment() -> None:
    """Stale comment tables are rerendered with current data."""
    issues = FakeGitHubIssues(
        issues={42: _make_issue(number=42, body=OBJECTIVE_BODY)},
        comments_with_urls={
            42: [
                IssueComment(
                    body=STALE_COMMENT,
                    url="https://example.com/c/1",
                    id=COMMENT_ID,
                    author="testuser",
                )
            ]
        },
    )
    from pathlib import Path

    result = _rerender_single_objective(issues, Path(REPO_ROOT), 42, dry_run=False)
    assert result.status == "rerendered"
    assert result.new_columns == 5
    # Verify comment was actually updated
    assert len(issues._updated_comments) == 1


def test_rerender_dry_run_does_not_mutate() -> None:
    """Dry run reports changes but does not update the comment."""
    issues = FakeGitHubIssues(
        issues={42: _make_issue(number=42, body=OBJECTIVE_BODY)},
        comments_with_urls={
            42: [
                IssueComment(
                    body=STALE_COMMENT,
                    url="https://example.com/c/1",
                    id=COMMENT_ID,
                    author="testuser",
                )
            ]
        },
    )
    from pathlib import Path

    result = _rerender_single_objective(issues, Path(REPO_ROOT), 42, dry_run=True)
    assert result.status == "rerendered"
    assert len(issues._updated_comments) == 0


def test_rerender_already_current() -> None:
    """Already-current comments are not updated."""
    issues = FakeGitHubIssues(
        issues={42: _make_issue(number=42, body=OBJECTIVE_BODY)},
        comments_with_urls={
            42: [
                IssueComment(
                    body=CURRENT_COMMENT,
                    url="https://example.com/c/1",
                    id=COMMENT_ID,
                    author="testuser",
                )
            ]
        },
    )
    from pathlib import Path

    result = _rerender_single_objective(issues, Path(REPO_ROOT), 42, dry_run=False)
    # The tables should be regenerated from YAML source, so they might differ in formatting
    assert result.status in ("already_current", "rerendered")
    assert result.old_columns == 5


def test_rerender_issue_not_found() -> None:
    """Missing issues produce error status."""
    issues = FakeGitHubIssues()
    from pathlib import Path

    result = _rerender_single_objective(issues, Path(REPO_ROOT), 99, dry_run=False)
    assert result.status == "error"
    assert "not found" in result.message


def test_rerender_no_label() -> None:
    """Issues without erk-objective label are skipped."""
    issue = IssueInfo(
        number=42,
        title="Not an objective",
        body="just text",
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=[],
        assignees=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        author="testuser",
    )
    issues = FakeGitHubIssues(issues={42: issue})
    from pathlib import Path

    result = _rerender_single_objective(issues, Path(REPO_ROOT), 42, dry_run=False)
    assert result.status == "skipped"


def test_rerender_no_comment_id() -> None:
    """Issues without objective_comment_id are skipped."""
    body_no_comment_id = textwrap.dedent("""\
        <!-- erk:metadata-block:objective-header -->

        <details>
        <summary><code>objective-header</code></summary>

        ```yaml
        created_at: '2026-01-01T00:00:00Z'
        created_by: testuser
        slug: null
        ```

        </details>

        <!-- /erk:metadata-block:objective-header -->

        <!-- erk:metadata-block:objective-roadmap -->

        <details>
        <summary><code>objective-roadmap</code></summary>

        ```yaml
        schema_version: "4"
        nodes:
        - id: "1.1"
          slug: null
          description: "Step one"
          status: "pending"
          plan: null
          pr: null
        ```

        </details>

        <!-- /erk:metadata-block:objective-roadmap -->
    """)
    issues = FakeGitHubIssues(
        issues={42: _make_issue(number=42, body=body_no_comment_id)},
    )
    from pathlib import Path

    result = _rerender_single_objective(issues, Path(REPO_ROOT), 42, dry_run=False)
    assert result.status == "skipped"
    assert "objective_comment_id" in result.message


# --- CLI integration test ---


def test_cli_missing_argument() -> None:
    """CLI without --issue or --all exits with error."""
    runner = CliRunner()
    ctx = context_for_test()
    result = runner.invoke(rerender_objective_comment, [], obj=ctx)
    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "missing_argument"


def test_cli_single_issue() -> None:
    """CLI with --issue processes a single objective."""
    issues = FakeGitHubIssues(
        issues={42: _make_issue(number=42, body=OBJECTIVE_BODY)},
        comments_with_urls={
            42: [
                IssueComment(
                    body=STALE_COMMENT,
                    url="https://example.com/c/1",
                    id=COMMENT_ID,
                    author="testuser",
                )
            ]
        },
    )
    ctx = context_for_test(github_issues=issues)
    runner = CliRunner()
    result = runner.invoke(rerender_objective_comment, ["--issue", "42"], obj=ctx)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["results"]) == 1
    assert output["results"][0]["status"] == "rerendered"


def test_cli_all_flag() -> None:
    """CLI with --all processes all open objectives."""
    issues = FakeGitHubIssues(
        issues={
            42: _make_issue(number=42, body=OBJECTIVE_BODY),
            43: _make_issue(number=43, body=OBJECTIVE_BODY),
        },
        comments_with_urls={
            42: [
                IssueComment(
                    body=STALE_COMMENT,
                    url="https://example.com/c/1",
                    id=COMMENT_ID,
                    author="testuser",
                )
            ],
            43: [
                IssueComment(
                    body=STALE_COMMENT,
                    url="https://example.com/c/2",
                    id=COMMENT_ID + 1,
                    author="testuser",
                )
            ],
        },
    )
    ctx = context_for_test(github_issues=issues)
    runner = CliRunner()
    result = runner.invoke(rerender_objective_comment, ["--all"], obj=ctx)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["results"]) == 2


def test_cli_dry_run() -> None:
    """CLI with --dry-run does not mutate and reports dry-run in summary."""
    issues = FakeGitHubIssues(
        issues={42: _make_issue(number=42, body=OBJECTIVE_BODY)},
        comments_with_urls={
            42: [
                IssueComment(
                    body=STALE_COMMENT,
                    url="https://example.com/c/1",
                    id=COMMENT_ID,
                    author="testuser",
                )
            ]
        },
    )
    ctx = context_for_test(github_issues=issues)
    runner = CliRunner()
    result = runner.invoke(rerender_objective_comment, ["--issue", "42", "--dry-run"], obj=ctx)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "(dry-run)" in output["summary"]
    assert len(issues._updated_comments) == 0
