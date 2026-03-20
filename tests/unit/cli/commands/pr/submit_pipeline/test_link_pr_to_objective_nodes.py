"""Unit tests for link_pr_to_objective_nodes pipeline step."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitState,
    link_pr_to_objective_nodes,
)
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.impl_folder import get_impl_dir, save_plan_ref
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.test_utils.test_context import context_for_test

BRANCH = "test/branch"
"""Test branch name used across tests."""

_FAKE_NOW = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)

# A minimal objective body with a roadmap metadata block using <details> format
_ROADMAP_BODY = """\
# Objective

Some description.

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '4'
nodes:
- id: '1.1'
  slug: add-auth
  description: Add auth
  status: pending
  pr: null
- id: '1.2'
  slug: add-tests
  description: Add tests
  status: pending
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""


def _make_state(
    *,
    cwd: Path,
    repo_root: Path | None = None,
    pr_number: int | None = 42,
) -> SubmitState:
    return SubmitState(
        cwd=cwd,
        repo_root=repo_root if repo_root is not None else cwd,
        branch_name="feature",
        parent_branch="main",
        trunk_branch="main",
        use_graphite=False,
        force=False,
        debug=False,
        session_id="test-session",
        skip_description=False,
        quiet=False,
        pr_id=None,
        pr_number=pr_number,
        pr_url=f"https://github.com/owner/repo/pull/{pr_number}" if pr_number else None,
        was_created=True,
        base_branch="main",
        graphite_url=None,
        diff_file=None,
        plan_context=None,
        title="My PR Title",
        body="My PR body",
        existing_pr_body="",
        graphite_is_authed=None,
        graphite_branch_tracked=None,
    )


def _make_issue(*, number: int, body: str) -> IssueInfo:
    return IssueInfo(
        number=number,
        title="Objective",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["objective"],
        assignees=[],
        created_at=_FAKE_NOW,
        updated_at=_FAKE_NOW,
        author="testuser",
    )


def _setup_impl(cwd: Path, *, objective_id: int, node_ids: tuple[str, ...]) -> None:
    """Create branch-scoped impl dir with ref.json containing node_ids."""
    impl_dir = get_impl_dir(cwd, branch_name="feature")
    impl_dir.mkdir(parents=True, exist_ok=True)
    save_plan_ref(
        impl_dir,
        provider="github",
        pr_number="100",
        url="https://github.com/owner/repo/issues/100",
        labels=(),
        objective_id=objective_id,
        node_ids=node_ids,
    )


def test_skips_when_no_pr_number(tmp_path: Path) -> None:
    """Returns state unchanged when pr_number is None."""
    state = _make_state(cwd=tmp_path, pr_number=None)
    ctx = context_for_test(cwd=tmp_path)

    result = link_pr_to_objective_nodes(ctx, state)

    assert result is state


def test_skips_when_no_impl_dir(tmp_path: Path) -> None:
    """Returns state unchanged when .impl/ doesn't exist."""
    state = _make_state(cwd=tmp_path)
    ctx = context_for_test(cwd=tmp_path)

    result = link_pr_to_objective_nodes(ctx, state)

    assert result is state


def test_skips_when_no_node_ids(tmp_path: Path) -> None:
    """Returns state unchanged when ref.json has no node_ids."""
    _setup_impl(tmp_path, objective_id=50, node_ids=())
    state = _make_state(cwd=tmp_path)
    ctx = context_for_test(cwd=tmp_path)

    result = link_pr_to_objective_nodes(ctx, state)

    assert result is state


def test_skips_when_objective_not_found(tmp_path: Path) -> None:
    """Returns state unchanged when objective issue doesn't exist."""
    _setup_impl(tmp_path, objective_id=999, node_ids=("1.1",))
    state = _make_state(cwd=tmp_path)
    fake_issues = FakeGitHubIssues()
    ctx = context_for_test(cwd=tmp_path, issues=fake_issues)

    result = link_pr_to_objective_nodes(ctx, state)

    assert result is state


def test_links_single_node(tmp_path: Path) -> None:
    """Updates roadmap frontmatter with PR reference for one node."""
    objective_id = 50
    _setup_impl(tmp_path, objective_id=objective_id, node_ids=("1.1",))

    fake_issues = FakeGitHubIssues(
        issues={objective_id: _make_issue(number=objective_id, body=_ROADMAP_BODY)},
    )
    state = _make_state(cwd=tmp_path, pr_number=42)
    ctx = context_for_test(cwd=tmp_path, issues=fake_issues)

    result = link_pr_to_objective_nodes(ctx, state)

    assert result is state
    # Verify the issue body was updated
    updated_issue = fake_issues._issues[objective_id]
    assert "#42" in updated_issue.body


def test_links_multiple_nodes(tmp_path: Path) -> None:
    """Updates roadmap frontmatter with PR reference for multiple nodes."""
    objective_id = 50
    _setup_impl(tmp_path, objective_id=objective_id, node_ids=("1.1", "1.2"))

    fake_issues = FakeGitHubIssues(
        issues={objective_id: _make_issue(number=objective_id, body=_ROADMAP_BODY)},
    )
    state = _make_state(cwd=tmp_path, pr_number=99)
    ctx = context_for_test(cwd=tmp_path, issues=fake_issues)

    result = link_pr_to_objective_nodes(ctx, state)

    assert result is state
    updated_issue = fake_issues._issues[objective_id]
    # Both nodes should reference the PR
    body = updated_issue.body
    # Parse YAML from the updated roadmap block to verify
    assert "#99" in body


def test_skips_node_not_in_roadmap(tmp_path: Path) -> None:
    """Gracefully skips nodes not found in the roadmap."""
    objective_id = 50
    _setup_impl(tmp_path, objective_id=objective_id, node_ids=("9.9",))

    fake_issues = FakeGitHubIssues(
        issues={objective_id: _make_issue(number=objective_id, body=_ROADMAP_BODY)},
    )
    state = _make_state(cwd=tmp_path, pr_number=42)
    ctx = context_for_test(cwd=tmp_path, issues=fake_issues)

    result = link_pr_to_objective_nodes(ctx, state)

    assert result is state
    # Issue body should NOT be updated (no successful links)
    updated_issue = fake_issues._issues[objective_id]
    assert updated_issue.body == _ROADMAP_BODY
