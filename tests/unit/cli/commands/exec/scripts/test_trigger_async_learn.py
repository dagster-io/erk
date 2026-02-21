"""Unit tests for trigger_async_learn exec script.

Tests triggering the learn.yml workflow for async learn.
Uses FakeGitHub, FakeGitHubIssues, and FakeClaudeInstallation for
dependency injection — no subprocess mocking.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.trigger_async_learn import (
    _get_pr_for_plan_direct,
)
from erk.cli.commands.exec.scripts.trigger_async_learn import (
    trigger_async_learn as trigger_async_learn_command,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo, RepoInfo
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend


def _parse_json_output(output: str) -> dict[str, object]:
    """Parse JSON from CliRunner output, skipping stderr progress lines.

    Click 8.x mixes stderr into result.output. The trigger-async-learn script
    writes progress messages to stderr and JSON to stdout. This helper extracts
    the JSON line from the mixed output.
    """
    for line in reversed(output.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)  # type: ignore[no-any-return]
    raise ValueError(f"No JSON found in output: {output!r}")


def _get_stderr_lines(output: str) -> list[str]:
    """Extract stderr diagnostic lines from CliRunner output.

    Returns all non-JSON lines (JSON lines are stdout, everything else is stderr diagnostics).
    """
    return [line for line in output.strip().splitlines() if not line.startswith("{")]


def _make_plan_issue_body(*, branch_name: str | None) -> str:
    """Create a plan issue body with plan-header metadata block."""
    branch_line = f"branch_name: {branch_name}" if branch_name is not None else "branch_name: null"
    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
worktree_name: test-worktree
{branch_line}
last_dispatched_run_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->"""


def _make_plan_issue_body_with_session(
    *,
    branch_name: str | None,
    planning_session_id: str,
    impl_session_id: str | None = None,
) -> str:
    """Create a plan issue body with plan-header metadata including session IDs."""
    branch_line = f"branch_name: {branch_name}" if branch_name is not None else "branch_name: null"
    impl_line = (
        f"last_local_impl_session: {impl_session_id}"
        if impl_session_id is not None
        else "last_local_impl_session: null"
    )
    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
worktree_name: test-worktree
{branch_line}
created_from_session: {planning_session_id}
{impl_line}
last_dispatched_run_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->"""


def _make_issue_info(number: int, body: str) -> IssueInfo:
    """Create test IssueInfo."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title="Test Issue",
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


def _make_minimal_session_jsonl(session_id: str) -> str:
    """Create minimal JSONL content that passes preprocessing filters.

    Creates a session with enough meaningful content to not be filtered
    as empty or warmup. Content uses list-of-blocks format as required
    by the preprocessing pipeline.
    """
    entries = [
        {
            "type": "system",
            "message": {"content": [{"type": "text", "text": "System prompt"}]},
            "session_id": session_id,
        },
        {
            "type": "user",
            "message": {"content": [{"type": "text", "text": "Please implement the feature"}]},
            "session_id": session_id,
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "I'll implement the feature now."}]},
            "session_id": session_id,
        },
        {
            "type": "user",
            "message": {"content": [{"type": "text", "text": "Looks good, thanks"}]},
            "session_id": session_id,
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "You're welcome!"}]},
            "session_id": session_id,
        },
    ]
    return "\n".join(json.dumps(entry) for entry in entries) + "\n"


def _make_pr_info(*, number: int, head_branch: str) -> PullRequestInfo:
    """Create test PullRequestInfo."""
    return PullRequestInfo(
        number=number,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        is_draft=False,
        title=f"PR #{number}",
        checks_passing=True,
        owner="test-owner",
        repo="test-repo",
        head_branch=head_branch,
    )


def _make_pr_details(*, number: int, head_ref_name: str) -> PRDetails:
    """Create test PRDetails."""
    return PRDetails(
        number=number,
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        title=f"PR #{number}",
        body="Test PR body",
        state="OPEN",
        is_draft=False,
        base_ref_name="master",
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )


# ============================================================================
# Success Cases
# ============================================================================


def test_trigger_async_learn_success(tmp_path: Path) -> None:
    """Test successful workflow trigger with session preprocessing pipeline."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    session_id = "planning-session-1"

    # Create a real JSONL session file that preprocessing can read
    session_content = _make_minimal_session_jsonl(session_id)
    session_dir = tmp_path / ".claude" / "projects" / "test-project"
    session_dir.mkdir(parents=True)
    session_file = session_dir / f"{session_id}.jsonl"
    session_file.write_text(session_content, encoding="utf-8")

    # Set up plan issue with session reference
    body = _make_plan_issue_body_with_session(
        branch_name=None,
        planning_session_id=session_id,
    )
    fake_issues = FakeGitHubIssues(issues={123: _make_issue_info(123, body)})

    # FakeClaudeInstallation that can find the session
    fake_claude = FakeClaudeInstallation.for_test(
        projects={
            session_dir: FakeProject(
                sessions={
                    session_id: FakeSessionData(
                        content=session_content,
                        size_bytes=len(session_content),
                        modified_at=1700000000.0,
                    ),
                }
            ),
        },
    )

    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)
    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    # Create the .erk/scratch directory
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    output = _parse_json_output(result.output)
    assert output["success"] is True
    assert output["plan_id"] == "123"
    assert output["workflow_triggered"] is True
    assert output["run_id"] == "1234567890"
    assert (
        output["workflow_url"] == "https://github.com/test-owner/test-repo/actions/runs/1234567890"
    )
    assert isinstance(output["learn_branch"], str)
    assert output["learn_branch"] == "learn/123"


def test_trigger_async_learn_verifies_workflow_call(tmp_path: Path) -> None:
    """Test that workflow trigger is called with correct parameters including learn_branch."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    # Plan issue with no sessions (no created_from_session in metadata)
    body = _make_plan_issue_body(branch_name=None)
    fake_issues = FakeGitHubIssues(issues={456: _make_issue_info(456, body)})
    fake_claude = FakeClaudeInstallation.for_test()
    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)

    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    # Create learn dir with a dummy file so branch commit has content
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-456"
    learn_dir.mkdir(parents=True)
    (learn_dir / "placeholder.txt").write_text("test content", encoding="utf-8")

    runner.invoke(trigger_async_learn_command, ["456"], obj=ctx)

    assert len(fake_gh.triggered_workflows) == 1
    workflow, inputs = fake_gh.triggered_workflows[0]
    assert workflow == "learn.yml"
    assert inputs["plan_id"] == "456"
    assert "learn_branch" in inputs
    assert inputs["learn_branch"] == "learn/456"


def test_trigger_async_learn_no_repo_info(tmp_path: Path) -> None:
    """Test error when not in a GitHub repository."""
    runner = CliRunner()
    fake_gh = FakeGitHub()
    fake_issues = FakeGitHubIssues()
    fake_claude = FakeClaudeInstallation.for_test()
    # Not passing repo_info leaves it as None
    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
    )

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 1
    output = _parse_json_output(result.output)
    assert output["success"] is False
    assert "GitHub repository" in output["error"]


def test_trigger_async_learn_no_context(tmp_path: Path) -> None:
    """Test error when context is not initialized."""
    runner = CliRunner()

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=None)

    assert result.exit_code == 1
    output = _parse_json_output(result.output)
    assert output["success"] is False
    assert "Context not initialized" in output["error"]


def test_trigger_async_learn_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success including learn_branch."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="dagster-io", name="erk")

    body = _make_plan_issue_body(branch_name=None)
    fake_issues = FakeGitHubIssues(issues={789: _make_issue_info(789, body)})
    fake_claude = FakeClaudeInstallation.for_test()
    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)

    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    # Create learn dir with content
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-789"
    learn_dir.mkdir(parents=True)
    (learn_dir / "placeholder.txt").write_text("test content", encoding="utf-8")

    result = runner.invoke(trigger_async_learn_command, ["789"], obj=ctx)

    assert result.exit_code == 0
    output = _parse_json_output(result.output)

    # Verify expected keys
    assert "success" in output
    assert "plan_id" in output
    assert "workflow_triggered" in output
    assert "run_id" in output
    assert "workflow_url" in output
    assert "learn_branch" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["plan_id"], str)
    assert isinstance(output["workflow_triggered"], bool)
    assert isinstance(output["run_id"], str)
    assert isinstance(output["workflow_url"], str)
    assert isinstance(output["learn_branch"], str)


def test_trigger_async_learn_filtered_session_skipped(tmp_path: Path) -> None:
    """Test that a filtered session (empty content) is skipped gracefully."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    session_id = "planning-session-1"

    # Create a session file with too few entries (will be filtered as empty)
    session_content = (
        json.dumps({"type": "system", "message": {"content": "x"}, "session_id": session_id}) + "\n"
    )
    session_dir = tmp_path / ".claude" / "projects" / "test-project"
    session_dir.mkdir(parents=True)
    session_file = session_dir / f"{session_id}.jsonl"
    session_file.write_text(session_content, encoding="utf-8")

    body = _make_plan_issue_body_with_session(
        branch_name=None,
        planning_session_id=session_id,
    )
    fake_issues = FakeGitHubIssues(issues={123: _make_issue_info(123, body)})
    fake_claude = FakeClaudeInstallation.for_test(
        projects={
            session_dir: FakeProject(
                sessions={
                    session_id: FakeSessionData(
                        content=session_content,
                        size_bytes=len(session_content),
                        modified_at=1700000000.0,
                    ),
                }
            ),
        },
    )
    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)

    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    # Create learn dir with content for branch commit
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)
    (learn_dir / "placeholder.txt").write_text("test", encoding="utf-8")

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    output = _parse_json_output(result.output)
    assert output["success"] is True


def test_trigger_async_learn_preprocess_failure(tmp_path: Path) -> None:
    """Test that a missing session file produces an error."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    session_id = "planning-session-1"

    # Session file path that doesn't actually exist on disk
    session_dir = tmp_path / ".claude" / "projects" / "test-project"
    session_dir.mkdir(parents=True)

    body = _make_plan_issue_body_with_session(
        branch_name=None,
        planning_session_id=session_id,
    )
    fake_issues = FakeGitHubIssues(issues={123: _make_issue_info(123, body)})

    # FakeClaudeInstallation reports the session exists, but the file isn't on disk
    fake_claude = FakeClaudeInstallation.for_test(
        projects={
            session_dir: FakeProject(
                sessions={
                    session_id: FakeSessionData(
                        content="not real",
                        size_bytes=10,
                        modified_at=1700000000.0,
                    ),
                }
            ),
        },
    )
    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)

    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 1
    output = _parse_json_output(result.output)
    assert output["success"] is False
    assert "failed" in str(output["error"]).lower()


# ============================================================================
# Diagnostic Output Tests (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_trigger_async_learn_logs_session_source_summary(tmp_path: Path) -> None:
    """Test that session source summary is logged to stderr after session discovery."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    planning_id = "plan-sess-1"
    impl_id = "impl-sess-2"

    # Create real session files for both sessions
    session_dir = tmp_path / ".claude" / "projects" / "test-project"
    session_dir.mkdir(parents=True)

    for sid in [planning_id, impl_id]:
        content = _make_minimal_session_jsonl(sid)
        (session_dir / f"{sid}.jsonl").write_text(content, encoding="utf-8")

    # Issue body with both planning and impl session references
    body = _make_plan_issue_body_with_session(
        branch_name=None,
        planning_session_id=planning_id,
        impl_session_id=impl_id,
    )
    fake_issues = FakeGitHubIssues(issues={123: _make_issue_info(123, body)})

    fake_claude = FakeClaudeInstallation.for_test(
        projects={
            session_dir: FakeProject(
                sessions={
                    planning_id: FakeSessionData(
                        content=_make_minimal_session_jsonl(planning_id),
                        size_bytes=500,
                        modified_at=1700000000.0,
                    ),
                    impl_id: FakeSessionData(
                        content=_make_minimal_session_jsonl(impl_id),
                        size_bytes=500,
                        modified_at=1700000001.0,
                    ),
                }
            ),
        },
    )
    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)

    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    stderr_lines = _get_stderr_lines(result.output)

    # Check session source summary line
    summary_lines = [line for line in stderr_lines if "Found 2 session" in line]
    assert len(summary_lines) == 1
    assert "planning" in summary_lines[0]
    assert "impl" in summary_lines[0]

    # Check individual session source lines (filter to only source listing lines)
    planning_lines = [line for line in stderr_lines if planning_id in line and "(local)" in line]
    assert len(planning_lines) == 1

    impl_lines = [line for line in stderr_lines if impl_id in line and "(local)" in line]
    assert len(impl_lines) == 1


def test_trigger_async_learn_pr_lookup_failure_continues(tmp_path: Path) -> None:
    """Test that PR lookup failure is handled gracefully and pipeline continues."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    # Plan issue with no branch_name -> _get_pr_for_plan_direct returns None
    body = _make_plan_issue_body(branch_name=None)
    fake_issues = FakeGitHubIssues(issues={999: _make_issue_info(999, body)})
    fake_claude = FakeClaudeInstallation.for_test()
    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)

    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    # Create learn dir with content for branch commit
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-999"
    learn_dir.mkdir(parents=True)
    (learn_dir / "placeholder.txt").write_text("test", encoding="utf-8")

    result = runner.invoke(trigger_async_learn_command, ["999"], obj=ctx)

    # Pipeline should still succeed even though PR lookup failed
    assert result.exit_code == 0
    output = _parse_json_output(result.output)
    assert output["success"] is True
    assert output["plan_id"] == "999"
    assert output["workflow_triggered"] is True

    # Verify PR lookup warning
    stderr_lines = _get_stderr_lines(result.output)
    warning_lines = [line for line in stderr_lines if "failed, skipping" in line]
    assert len(warning_lines) == 1
    assert "Getting PR for plan" in warning_lines[0]


def test_trigger_async_learn_pr_lookup_with_branch_inference(tmp_path: Path) -> None:
    """Test PR lookup succeeds via branch inference when branch_name is missing."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    branch_name = "P999-fix-something-02-17-0846"

    # Plan issue with no branch_name in metadata
    body = _make_plan_issue_body(branch_name=None)
    fake_issues = FakeGitHubIssues(issues={999: _make_issue_info(999, body)})
    fake_claude = FakeClaudeInstallation.for_test()
    fake_gh = FakeGitHub(
        repo_info=repo_info,
        issues_gateway=fake_issues,
        prs={branch_name: _make_pr_info(number=1000, head_branch=branch_name)},
        pr_details={1000: _make_pr_details(number=1000, head_ref_name=branch_name)},
    )
    # FakeGit with current branch matching P{issue}- prefix
    fake_git = FakeGit(current_branches={tmp_path: branch_name})

    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        git=fake_git,
        repo_info=repo_info,
    )

    # Create learn dir with content
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-999"
    learn_dir.mkdir(parents=True)
    (learn_dir / "placeholder.txt").write_text("test", encoding="utf-8")

    result = runner.invoke(trigger_async_learn_command, ["999"], obj=ctx)

    assert result.exit_code == 0
    output = _parse_json_output(result.output)
    assert output["success"] is True

    # Verify PR lookup succeeded (no "failed, skipping" warning)
    stderr_lines = _get_stderr_lines(result.output)
    warning_lines = [line for line in stderr_lines if "failed, skipping" in line]
    assert len(warning_lines) == 0

    # Verify review comments were fetched (indicates PR was found)
    review_lines = [line for line in stderr_lines if "Fetching review comments" in line]
    assert len(review_lines) == 1


def test_trigger_async_learn_logs_output_file_sizes(tmp_path: Path) -> None:
    """Test that preprocessed output file sizes are logged."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    session_id = "plan-sess-1"

    # Create a real session file
    session_dir = tmp_path / ".claude" / "projects" / "test-project"
    session_dir.mkdir(parents=True)
    session_content = _make_minimal_session_jsonl(session_id)
    (session_dir / f"{session_id}.jsonl").write_text(session_content, encoding="utf-8")

    body = _make_plan_issue_body_with_session(
        branch_name=None,
        planning_session_id=session_id,
    )
    fake_issues = FakeGitHubIssues(issues={123: _make_issue_info(123, body)})
    fake_claude = FakeClaudeInstallation.for_test(
        projects={
            session_dir: FakeProject(
                sessions={
                    session_id: FakeSessionData(
                        content=session_content,
                        size_bytes=len(session_content),
                        modified_at=1700000000.0,
                    ),
                }
            ),
        },
    )
    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)

    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    stderr_lines = _get_stderr_lines(result.output)

    # Should have output file with size logged
    output_lines = [line for line in stderr_lines if f"planning-{session_id}" in line]
    assert len(output_lines) >= 1
    assert "chars)" in output_lines[0]


def test_trigger_async_learn_logs_branch_size(tmp_path: Path) -> None:
    """Test that branch commit logs file count and total size."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    body = _make_plan_issue_body(branch_name=None)
    fake_issues = FakeGitHubIssues(issues={123: _make_issue_info(123, body)})
    fake_claude = FakeClaudeInstallation.for_test()
    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)

    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    # Create learn dir with multiple files for branch stats
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)
    (learn_dir / "file1.txt").write_text("content one", encoding="utf-8")
    (learn_dir / "file2.txt").write_text("content two", encoding="utf-8")
    (learn_dir / "file3.txt").write_text("content three", encoding="utf-8")

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    stderr_lines = _get_stderr_lines(result.output)

    branch_lines = [line for line in stderr_lines if "3 file(s)" in line]
    assert len(branch_lines) == 1
    assert "bytes" in branch_lines[0]


def test_trigger_async_learn_skip_workflow(tmp_path: Path) -> None:
    """Test that --skip-workflow runs preprocessing but does not trigger the workflow."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    # Plan issue with no sessions (no created_from_session in metadata)
    body = _make_plan_issue_body(branch_name=None)
    fake_issues = FakeGitHubIssues(issues={456: _make_issue_info(456, body)})
    fake_claude = FakeClaudeInstallation.for_test()
    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)

    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    # Create learn dir with content for branch commit
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-456"
    learn_dir.mkdir(parents=True)
    (learn_dir / "placeholder.txt").write_text("test content", encoding="utf-8")

    result = runner.invoke(trigger_async_learn_command, ["456", "--skip-workflow"], obj=ctx)

    assert result.exit_code == 0, result.output
    output = _parse_json_output(result.output)

    # Verify preprocessing succeeded but workflow was not triggered
    assert output["success"] is True
    assert output["plan_id"] == "456"
    assert output["workflow_triggered"] is False

    # Verify no run_id or workflow_url fields in output
    assert "run_id" not in output
    assert "workflow_url" not in output

    # Verify learn_branch is present
    assert isinstance(output["learn_branch"], str)
    assert output["learn_branch"] == "learn/456"

    # Verify no workflows were triggered on FakeGitHub
    assert len(fake_gh.triggered_workflows) == 0


# ============================================================================
# Remote Session Tests (Layer 4: Business Logic over Fakes)
# ============================================================================


def _make_plan_issue_body_with_remote_session(
    *,
    branch_name: str | None,
    planning_session_id: str,
    remote_session_id: str,
    gist_url: str,
) -> str:
    """Create a plan issue body with both a planning session and a remote gist session."""
    branch_line = f"branch_name: {branch_name}" if branch_name is not None else "branch_name: null"
    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
worktree_name: test-worktree
{branch_line}
created_from_session: {planning_session_id}
last_session_gist_url: {gist_url}
last_session_id: {remote_session_id}
last_session_source: remote
last_dispatched_run_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->"""


def test_trigger_async_learn_includes_remote_session(tmp_path: Path) -> None:
    """Test that remote sessions are downloaded and preprocessed alongside local sessions."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    planning_id = "plan-sess-1"
    remote_id = "remote-impl-sess-2"

    # Create a real JSONL session file for the planning session
    session_dir = tmp_path / ".claude" / "projects" / "test-project"
    session_dir.mkdir(parents=True)
    planning_content = _make_minimal_session_jsonl(planning_id)
    (session_dir / f"{planning_id}.jsonl").write_text(planning_content, encoding="utf-8")

    # Create a remote session JSONL file and serve via file:// URL
    remote_content = _make_minimal_session_jsonl(remote_id)
    remote_file = tmp_path / "remote-session.jsonl"
    remote_file.write_text(remote_content, encoding="utf-8")
    gist_url = remote_file.as_uri()

    # Set up plan issue with both planning and remote session references
    body = _make_plan_issue_body_with_remote_session(
        branch_name=None,
        planning_session_id=planning_id,
        remote_session_id=remote_id,
        gist_url=gist_url,
    )
    fake_issues = FakeGitHubIssues(issues={123: _make_issue_info(123, body)})

    fake_claude = FakeClaudeInstallation.for_test(
        projects={
            session_dir: FakeProject(
                sessions={
                    planning_id: FakeSessionData(
                        content=planning_content,
                        size_bytes=len(planning_content),
                        modified_at=1700000000.0,
                    ),
                }
            ),
        },
    )

    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)
    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    output = _parse_json_output(result.output)
    assert output["success"] is True

    # Verify both sessions were preprocessed
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    planning_xmls = list(learn_dir.glob(f"planning-{planning_id}*.xml"))
    impl_xmls = list(learn_dir.glob(f"impl-{remote_id}*.xml"))
    assert len(planning_xmls) >= 1, f"Expected planning XML, found: {list(learn_dir.iterdir())}"
    assert len(impl_xmls) >= 1, f"Expected impl XML, found: {list(learn_dir.iterdir())}"

    # Verify both sessions were committed to the learn branch
    output = _parse_json_output(result.output)
    assert output["learn_branch"] == "learn/123"


def test_trigger_async_learn_remote_session_download_failure(tmp_path: Path) -> None:
    """Test that a failed remote session download is handled gracefully."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")

    planning_id = "plan-sess-1"
    remote_id = "remote-impl-sess-2"

    # Create a real JSONL session file for the planning session
    session_dir = tmp_path / ".claude" / "projects" / "test-project"
    session_dir.mkdir(parents=True)
    planning_content = _make_minimal_session_jsonl(planning_id)
    (session_dir / f"{planning_id}.jsonl").write_text(planning_content, encoding="utf-8")

    # Use an unreachable file:// URL to simulate download failure
    gist_url = "file:///nonexistent/path/to/session.jsonl"

    body = _make_plan_issue_body_with_remote_session(
        branch_name=None,
        planning_session_id=planning_id,
        remote_session_id=remote_id,
        gist_url=gist_url,
    )
    fake_issues = FakeGitHubIssues(issues={123: _make_issue_info(123, body)})

    fake_claude = FakeClaudeInstallation.for_test(
        projects={
            session_dir: FakeProject(
                sessions={
                    planning_id: FakeSessionData(
                        content=planning_content,
                        size_bytes=len(planning_content),
                        modified_at=1700000000.0,
                    ),
                }
            ),
        },
    )

    fake_gh = FakeGitHub(repo_info=repo_info, issues_gateway=fake_issues)
    ctx = ErkContext.for_test(
        repo_root=tmp_path,
        cwd=tmp_path,
        github=fake_gh,
        github_issues=fake_issues,
        claude_installation=fake_claude,
        repo_info=repo_info,
    )

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    # Pipeline should still succeed - the planning session is processed, remote failure is warned
    assert result.exit_code == 0, result.output
    output = _parse_json_output(result.output)
    assert output["success"] is True

    # Verify the planning session was still preprocessed
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    planning_xmls = list(learn_dir.glob(f"planning-{planning_id}*.xml"))
    assert len(planning_xmls) >= 1

    # Verify warning was logged about the download failure
    stderr_lines = _get_stderr_lines(result.output)
    warning_lines = [line for line in stderr_lines if "Failed to download" in line]
    assert len(warning_lines) == 1


# ============================================================================
# Draft-PR Backend Tests (Fix 1: _get_pr_for_plan_direct shortcut)
# ============================================================================


def test_get_pr_for_plan_direct_draft_pr_backend(tmp_path: Path) -> None:
    """Test that _get_pr_for_plan_direct returns PR directly for draft-PR backend."""
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(
        issues_gateway=fake_issues,
        pr_details={7618: _make_pr_details(number=7618, head_ref_name="plan-fix-something")},
    )
    fake_git = FakeGit()
    draft_backend = DraftPRPlanBackend(fake_gh, fake_issues, time=FakeTime())

    result = _get_pr_for_plan_direct(
        plan_backend=draft_backend,
        github=fake_gh,
        git=fake_git,
        repo_root=tmp_path,
        plan_id="7618",
    )

    assert result is not None
    assert result["success"] is True
    assert result["pr_number"] == 7618
    assert result["pr"]["number"] == 7618
    assert result["pr"]["head_ref_name"] == "plan-fix-something"


def test_get_pr_for_plan_direct_draft_pr_backend_not_found(tmp_path: Path) -> None:
    """Test that _get_pr_for_plan_direct returns None when PR not found for draft-PR backend."""
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(issues_gateway=fake_issues)
    fake_git = FakeGit()
    draft_backend = DraftPRPlanBackend(fake_gh, fake_issues, time=FakeTime())

    result = _get_pr_for_plan_direct(
        plan_backend=draft_backend,
        github=fake_gh,
        git=fake_git,
        repo_root=tmp_path,
        plan_id="9999",
    )

    assert result is None
