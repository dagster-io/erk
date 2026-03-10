"""Tests for objective plan with --repo flag (no local repo)."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.test_utils.test_context import context_for_test

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
    status: pending
    plan: null
    pr: null
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

| Node | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | pending | - | - |
| 1.2 | Add tests | pending | - | - |

### Phase 2: Core

| Node | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Build feature | pending | - | - |
"""

OBJECTIVE_ALL_DONE_BODY = """# Objective: Done

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
    status: done
    plan: null
    pr: '#101'

```

</details>
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Foundation

| Node | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | done | - | #100 |
| 1.2 | Add tests | done | - | #101 |
"""

NOW = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


def _make_objective_issue(number: int, body: str) -> IssueInfo:
    return IssueInfo(
        number=number,
        title="Add caching",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=NOW,
        updated_at=NOW,
        author="testuser",
    )


def _make_fake_remote(
    *,
    issues: dict[int, IssueInfo] | None = None,
) -> FakeRemoteGitHub:
    return FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=issues,
        issue_comments=None,
        pr_references=None,
    )


def _build_remote_context(fake_remote: FakeRemoteGitHub) -> context_for_test:
    return context_for_test(
        repo=NoRepoSentinel(),
        remote_github=fake_remote,
    )


# --- one-shot remote ---


def test_one_shot_remote_dispatches_workflow() -> None:
    """Test --repo owner/repo --one-shot dispatches via RemoteGitHub."""
    issues = {42: _make_objective_issue(42, OBJECTIVE_BODY)}
    fake_remote = _make_fake_remote(issues=issues)
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["objective", "plan", "42", "--one-shot", "--repo", "owner/repo"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert len(fake_remote.dispatched_workflows) == 1
    wf = fake_remote.dispatched_workflows[0]
    assert wf.inputs["objective_issue"] == "42"
    assert wf.inputs["node_id"] == "1.1"
    assert "Setup infra" in wf.inputs["prompt"]


def test_one_shot_remote_with_node() -> None:
    """Test --repo --one-shot --node 2.1 dispatches specific node."""
    issues = {42: _make_objective_issue(42, OBJECTIVE_BODY)}
    fake_remote = _make_fake_remote(issues=issues)
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["objective", "plan", "42", "--one-shot", "--node", "2.1", "--repo", "owner/repo"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert len(fake_remote.dispatched_workflows) == 1
    assert fake_remote.dispatched_workflows[0].inputs["node_id"] == "2.1"
    assert "Build feature" in fake_remote.dispatched_workflows[0].inputs["prompt"]


def test_one_shot_remote_no_pending_nodes() -> None:
    """Test all-done objective returns cleanly in remote mode."""
    issues = {42: _make_objective_issue(42, OBJECTIVE_ALL_DONE_BODY)}
    fake_remote = _make_fake_remote(issues=issues)
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["objective", "plan", "42", "--one-shot", "--repo", "owner/repo"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "no pending nodes" in result.output
    assert len(fake_remote.dispatched_workflows) == 0


def test_one_shot_remote_default_ref() -> None:
    """Test remote mode uses default branch when no --ref."""
    issues = {42: _make_objective_issue(42, OBJECTIVE_BODY)}
    fake_remote = _make_fake_remote(issues=issues)
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["objective", "plan", "42", "--one-shot", "--repo", "owner/repo"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert len(fake_remote.dispatched_workflows) == 1
    # Default branch "main" should be used as ref
    assert fake_remote.dispatched_workflows[0].ref == "main"


def test_one_shot_remote_explicit_ref() -> None:
    """Test --ref custom-ref is threaded through in remote mode."""
    issues = {42: _make_objective_issue(42, OBJECTIVE_BODY)}
    fake_remote = _make_fake_remote(issues=issues)
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "objective",
            "plan",
            "42",
            "--one-shot",
            "--repo",
            "owner/repo",
            "--ref",
            "custom-ref",
        ],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert len(fake_remote.dispatched_workflows) == 1
    assert fake_remote.dispatched_workflows[0].ref == "custom-ref"


# --- all-unblocked remote ---


def test_all_unblocked_remote_dispatches_all() -> None:
    """Test --repo --all-unblocked dispatches all unblocked nodes."""
    issues = {42: _make_objective_issue(42, OBJECTIVE_BODY)}
    fake_remote = _make_fake_remote(issues=issues)
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["objective", "plan", "42", "--all-unblocked", "--repo", "owner/repo"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    # Nodes 1.1 and 1.2 are unblocked (2.1 depends on phase 1)
    assert len(fake_remote.dispatched_workflows) >= 1
    node_ids = [wf.inputs["node_id"] for wf in fake_remote.dispatched_workflows]
    assert "1.1" in node_ids


# --- error cases ---


def test_repo_without_one_shot_fails() -> None:
    """Test --repo without --one-shot produces error."""
    issues = {42: _make_objective_issue(42, OBJECTIVE_BODY)}
    fake_remote = _make_fake_remote(issues=issues)
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["objective", "plan", "42", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 1
    assert "--repo requires --one-shot or --all-unblocked" in result.output


def test_ref_current_without_local_repo_fails() -> None:
    """Test --ref-current --repo errors (no local repo for current branch)."""
    issues = {42: _make_objective_issue(42, OBJECTIVE_BODY)}
    fake_remote = _make_fake_remote(issues=issues)
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "objective",
            "plan",
            "42",
            "--one-shot",
            "--repo",
            "owner/repo",
            "--ref-current",
        ],
        obj=ctx,
    )

    assert result.exit_code != 0
    assert "--ref-current requires a local git repository" in result.output


def test_next_without_issue_ref_remote_fails() -> None:
    """Test --next without ISSUE_REF in remote mode errors."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["objective", "plan", "--one-shot", "--next", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 1
    assert "ISSUE_REF is required" in result.output
