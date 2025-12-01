"""Tests for erk submit worktree_name update functionality."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.metadata import extract_plan_header_worktree_name
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.commands.submit import ERK_PLAN_LABEL, submit_cmd
from erk.core.context import ErkContext
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.repo_discovery import RepoContext
from tests.fakes.issue_link_branches import FakeIssueLinkBranches


def test_submit_stores_worktree_name_in_plan_header(tmp_path: Path) -> None:
    """Test submit updates plan-header with worktree_name (branch name)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with plan-header (schema v2) but NO worktree_name yet
    now = datetime.now(UTC)
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T14:30:00Z'
created_by: 'testuser'
last_dispatched_run_id: null
last_dispatched_at: null
last_local_impl_at: null
last_remote_impl_at: null
```
</details>
<!-- /erk:metadata-block:plan-header -->

# Plan

Implementation details..."""

    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=issue_body,
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Create plan for the issue
    plan = Plan(
        plan_identifier="123",
        title="Implement feature X",
        body=issue_body,
        state=PlanState.OPEN,
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_plan_store = FakePlanStore(plans={"123": plan})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub()
    fake_issue_dev = FakeIssueLinkBranches()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        issue_link_branches=fake_issue_dev,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output

    # Branch name is sanitize_worktree_name(...) + timestamp suffix "-01-15-1430"
    expected_branch = "123-implement-feature-x-01-15-1430"

    # Verify issue body was updated with worktree_name
    assert len(fake_github_issues.updated_issue_bodies) == 1
    issue_number, updated_body = fake_github_issues.updated_issue_bodies[0]
    assert issue_number == 123

    # Extract worktree_name from updated issue body
    extracted_worktree_name = extract_plan_header_worktree_name(updated_body)
    assert extracted_worktree_name == expected_branch


def test_submit_stores_worktree_name_when_branch_exists(tmp_path: Path) -> None:
    """Test submit updates plan-header when reusing existing branch."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T14:30:00Z'
created_by: 'testuser'
last_dispatched_run_id: null
last_dispatched_at: null
last_local_impl_at: null
last_remote_impl_at: null
```
</details>
<!-- /erk:metadata-block:plan-header -->

# Plan

Implementation details..."""

    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=issue_body,
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Pre-existing branch from previous gh issue develop (no PR though)
    expected_branch = "123-existing-branch"

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    # FakeIssueLinkBranches with existing branch for issue 123
    fake_issue_dev = FakeIssueLinkBranches(existing_branches={123: expected_branch})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        # Simulate branch existing on remote
        remote_branches={repo_root: [f"origin/{expected_branch}"]},
    )
    # No PR status for this branch (pr_statuses is empty)
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        issue_link_branches=fake_issue_dev,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify issue body was updated with worktree_name (existing branch name)
    assert len(fake_github_issues.updated_issue_bodies) == 1
    issue_number, updated_body = fake_github_issues.updated_issue_bodies[0]
    assert issue_number == 123

    # Extract worktree_name from updated issue body
    extracted_worktree_name = extract_plan_header_worktree_name(updated_body)
    assert extracted_worktree_name == expected_branch


def test_submit_stores_worktree_name_when_pr_already_exists(tmp_path: Path) -> None:
    """Test submit updates plan-header when PR already exists (just triggering workflow)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T14:30:00Z'
created_by: 'testuser'
last_dispatched_run_id: null
last_dispatched_at: null
last_local_impl_at: null
last_remote_impl_at: null
```
</details>
<!-- /erk:metadata-block:plan-header -->

# Plan

Implementation details..."""

    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=issue_body,
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Pre-existing branch with PR
    expected_branch = "123-existing-branch"

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_issue_dev = FakeIssueLinkBranches(existing_branches={123: expected_branch})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        # Branch exists on remote
        remote_branches={repo_root: [f"origin/{expected_branch}"]},
    )
    # PR already exists for this branch
    from erk_shared.github.types import PullRequestInfo

    pr_info = PullRequestInfo(
        number=999,
        state="OPEN",
        url="https://github.com/test-owner/test-repo/pull/999",
        is_draft=True,
        title="Existing PR",
        checks_passing=None,
        owner="test-owner",
        repo="test-repo",
        has_conflicts=False,
    )
    fake_github = FakeGitHub(prs={expected_branch: pr_info})

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        issue_link_branches=fake_issue_dev,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "already exists for branch" in result.output
    assert "Skipping branch/PR creation, triggering workflow..." in result.output

    # Verify issue body was updated with worktree_name even when just triggering workflow
    assert len(fake_github_issues.updated_issue_bodies) == 1
    issue_number, updated_body = fake_github_issues.updated_issue_bodies[0]
    assert issue_number == 123

    # Extract worktree_name from updated issue body
    extracted_worktree_name = extract_plan_header_worktree_name(updated_body)
    assert extracted_worktree_name == expected_branch
