"""Tests for register-one-shot-plan exec command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.register_one_shot_plan import register_one_shot_plan
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PRDetails

RUN_URL = "https://github.com/test-owner/test-repo/actions/runs/99999"
CLI_ARGS = [
    "--issue-number",
    "123",
    "--run-id",
    "99999",
    "--pr-number",
    "42",
    "--submitted-by",
    "alice",
    "--run-url",
    RUN_URL,
]


def _plan_header_body() -> str:
    return """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T12:00:00Z'
created_by: test-user
worktree_name: test-wt
last_dispatched_run_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Test Plan"""


def _issue(number: int, body: str) -> IssueInfo:
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title="Test",
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


def _pr(number: int, body: str) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        title="Test PR",
        body=body,
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )


def _ctx(tmp_path: Path, *, issues: FakeGitHubIssues, github: FakeGitHub) -> ErkContext:
    (tmp_path / ".erk").mkdir(exist_ok=True)
    (tmp_path / ".erk" / "config.toml").write_text("", encoding="utf-8")
    return ErkContext.for_test(github_issues=issues, github=github, repo_root=tmp_path)


def test_all_succeed(tmp_path: Path) -> None:
    issues = FakeGitHubIssues(issues={123: _issue(123, _plan_header_body())})
    github = FakeGitHub(pr_details={42: _pr(42, "Draft PR")})
    result = CliRunner().invoke(
        register_one_shot_plan, CLI_ARGS, obj=_ctx(tmp_path, issues=issues, github=github)
    )
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["dispatch_metadata"]["success"] is True
    assert output["queued_comment"]["success"] is True
    assert output["pr_closing_ref"]["success"] is True


def test_all_fail_when_issue_and_pr_missing(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        register_one_shot_plan,
        [
            "--issue-number",
            "999",
            "--run-id",
            "99999",
            "--pr-number",
            "999",
            "--submitted-by",
            "alice",
            "--run-url",
            RUN_URL,
        ],
        obj=_ctx(tmp_path, issues=FakeGitHubIssues(), github=FakeGitHub()),
    )
    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["dispatch_metadata"]["success"] is False
    assert output["queued_comment"]["success"] is False
    assert output["pr_closing_ref"]["success"] is False


def test_dispatch_fails_others_succeed(tmp_path: Path) -> None:
    """No plan-header block causes dispatch to fail; comment and PR update still work."""
    issues = FakeGitHubIssues(issues={123: _issue(123, "# No plan-header")})
    github = FakeGitHub(pr_details={42: _pr(42, "Draft PR")})
    result = CliRunner().invoke(
        register_one_shot_plan, CLI_ARGS, obj=_ctx(tmp_path, issues=issues, github=github)
    )
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["dispatch_metadata"]["success"] is False
    assert output["queued_comment"]["success"] is True
    assert output["pr_closing_ref"]["success"] is True


def test_pr_not_found_others_succeed(tmp_path: Path) -> None:
    issues = FakeGitHubIssues(issues={123: _issue(123, _plan_header_body())})
    result = CliRunner().invoke(
        register_one_shot_plan,
        [
            "--issue-number",
            "123",
            "--run-id",
            "99999",
            "--pr-number",
            "999",
            "--submitted-by",
            "alice",
            "--run-url",
            RUN_URL,
        ],
        obj=_ctx(tmp_path, issues=issues, github=FakeGitHub()),
    )
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["dispatch_metadata"]["success"] is True
    assert output["queued_comment"]["success"] is True
    assert output["pr_closing_ref"]["success"] is False
