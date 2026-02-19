"""Unit tests for erk objective plan command --all-unblocked flag."""

from datetime import UTC, datetime

import click
import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.objective.plan_cmd import (
    ResolvedAllUnblocked,
    _resolve_all_unblocked,
)
from erk.core.context import context_for_test
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


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


# Objective body with fan-out: 1.1 done, 2.1 and 2.2 both pending and unblocked
_FAN_OUT_BODY = """\
# Objective: Fan-Out Test

### Phase 1: Root

### Phase 2: Branches

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '3'
nodes:
- id: '1.1'
  description: Root step
  status: done
  plan: null
  pr: '#100'
  depends_on: []
- id: '2.1'
  description: Branch A
  status: pending
  plan: null
  pr: null
  depends_on:
  - '1.1'
- id: '2.2'
  description: Branch B
  status: pending
  plan: null
  pr: null
  depends_on:
  - '1.1'
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

# Objective body with all nodes done
_ALL_DONE_BODY = """\
# Objective: All Done

### Phase 1: Done

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Step A
  status: done
  plan: null
  pr: '#100'
- id: '1.2'
  description: Step B
  status: done
  plan: null
  pr: '#101'
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""


# ---------------------------------------------------------------------------
# Flag validation tests (CLI-level)
# ---------------------------------------------------------------------------


class TestFlagValidation:
    def test_all_unblocked_mutually_exclusive_with_node(self) -> None:
        """--all-unblocked and --node cannot be used together."""
        runner = CliRunner()
        ctx = context_for_test()

        result = runner.invoke(
            cli,
            ["objective", "plan", "42", "--all-unblocked", "--node", "1.1"],
            obj=ctx,
        )

        assert result.exit_code != 0
        assert "--all-unblocked and --node are mutually exclusive" in result.output

    def test_all_unblocked_mutually_exclusive_with_next(self) -> None:
        """--all-unblocked and --next cannot be used together."""
        runner = CliRunner()
        ctx = context_for_test()

        result = runner.invoke(
            cli,
            ["objective", "plan", "42", "--all-unblocked", "--next"],
            obj=ctx,
        )

        assert result.exit_code != 0
        assert "--all-unblocked and --next are mutually exclusive" in result.output

    def test_all_unblocked_without_issue_ref_requires_branch(self) -> None:
        """--all-unblocked without ISSUE_REF infers from branch (fails when not on branch)."""
        runner = CliRunner()
        ctx = context_for_test()

        result = runner.invoke(
            cli,
            ["objective", "plan", "--all-unblocked"],
            obj=ctx,
        )

        # Should fail trying to resolve objective (not in a repo / no branch)
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# _resolve_all_unblocked() unit tests
# ---------------------------------------------------------------------------


class TestResolveAllUnblocked:
    def test_returns_pending_unblocked_nodes(self) -> None:
        """_resolve_all_unblocked returns all pending unblocked nodes with phase names."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner, env_overrides=None) as env:
            env.setup_repo_structure()

            issue = _make_issue(42, "Objective: Fan-Out", _FAN_OUT_BODY)
            issues = FakeGitHubIssues(issues={42: issue})
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                default_branches={env.cwd: "main"},
                trunk_branches={env.cwd: "main"},
                current_branches={env.cwd: "main"},
            )
            ctx = build_workspace_test_context(env, git=git, issues=issues)

            resolved = _resolve_all_unblocked(ctx, issue_ref="42")

            assert isinstance(resolved, ResolvedAllUnblocked)
            assert resolved.issue_number == 42
            assert len(resolved.nodes) == 2
            node_ids = [node.id for node, _phase in resolved.nodes]
            assert node_ids == ["2.1", "2.2"]

    def test_no_pending_raises(self) -> None:
        """_resolve_all_unblocked raises when no pending unblocked nodes."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner, env_overrides=None) as env:
            env.setup_repo_structure()

            issue = _make_issue(42, "Objective: All Done", _ALL_DONE_BODY)
            issues = FakeGitHubIssues(issues={42: issue})
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                default_branches={env.cwd: "main"},
                trunk_branches={env.cwd: "main"},
                current_branches={env.cwd: "main"},
            )
            ctx = build_workspace_test_context(env, git=git, issues=issues)

            with pytest.raises(click.ClickException, match="no pending unblocked nodes"):
                _resolve_all_unblocked(ctx, issue_ref="42")


# ---------------------------------------------------------------------------
# _handle_all_unblocked() integration tests (CLI-level)
# ---------------------------------------------------------------------------


class TestHandleAllUnblocked:
    def test_dispatches_each_node(self) -> None:
        """--all-unblocked dispatches one-shot workflow for each unblocked node."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner, env_overrides=None) as env:
            env.setup_repo_structure()

            issue = _make_issue(42, "Objective: Fan-Out", _FAN_OUT_BODY)
            issues = FakeGitHubIssues(issues={42: issue})
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                default_branches={env.cwd: "main"},
                trunk_branches={env.cwd: "main"},
                current_branches={env.cwd: "main"},
            )
            github = FakeGitHub(authenticated=True, issues_gateway=issues)
            ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

            result = runner.invoke(
                cli,
                ["objective", "plan", "42", "--all-unblocked"],
                obj=ctx,
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            assert "2 unblocked pending node(s)" in result.output
            assert "Dispatching node 2.1" in result.output
            assert "Dispatching node 2.2" in result.output
            assert "Dispatched 2/2 node(s)" in result.output

            # Verify two workflows triggered (one per node)
            assert len(github.triggered_workflows) == 2
            for _workflow, inputs in github.triggered_workflows:
                assert inputs["objective_issue"] == "42"
            triggered_node_ids = [
                inputs["node_id"] for _workflow, inputs in github.triggered_workflows
            ]
            assert triggered_node_ids == ["2.1", "2.2"]

    def test_dry_run_shows_preview(self) -> None:
        """--all-unblocked --dry-run shows preview without dispatching."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner, env_overrides=None) as env:
            env.setup_repo_structure()

            issue = _make_issue(42, "Objective: Fan-Out", _FAN_OUT_BODY)
            issues = FakeGitHubIssues(issues={42: issue})
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                default_branches={env.cwd: "main"},
                trunk_branches={env.cwd: "main"},
                current_branches={env.cwd: "main"},
            )
            github = FakeGitHub(authenticated=True, issues_gateway=issues)
            ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

            result = runner.invoke(
                cli,
                ["objective", "plan", "42", "--all-unblocked", "--dry-run"],
                obj=ctx,
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            assert "2 unblocked pending node(s)" in result.output
            assert "Dry-run" in result.output
            assert "Would dispatch 2 node(s)" in result.output

            # No workflows should be triggered in dry-run
            assert len(github.triggered_workflows) == 0

    def test_updates_objective_nodes_to_planning(self) -> None:
        """--all-unblocked marks each dispatched node as 'planning' atomically."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner, env_overrides=None) as env:
            env.setup_repo_structure()

            issue = _make_issue(42, "Objective: Fan-Out", _FAN_OUT_BODY)
            issues = FakeGitHubIssues(issues={42: issue})
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                default_branches={env.cwd: "main"},
                trunk_branches={env.cwd: "main"},
                current_branches={env.cwd: "main"},
            )
            github = FakeGitHub(authenticated=True, issues_gateway=issues)
            ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

            result = runner.invoke(
                cli,
                ["objective", "plan", "42", "--all-unblocked"],
                obj=ctx,
                catch_exceptions=False,
            )

            assert result.exit_code == 0

            # Verify atomicity: single body write for objective issue #42
            # (other issues may be updated by dispatch_one_shot for skeleton plans)
            objective_updates = [
                (num, body) for num, body in issues.updated_bodies if num == 42
            ]
            assert len(objective_updates) == 1

            # Verify both nodes appear as "planning" in the final body
            from erk_shared.gateway.github.issues.types import IssueNotFound

            updated_issue = issues.get_issue(env.cwd, 42)
            assert not isinstance(updated_issue, IssueNotFound)
            assert "planning" in updated_issue.body

    def test_batch_update_atomicity(self) -> None:
        """Dispatching 2 nodes results in exactly 1 update_issue_body call."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner, env_overrides=None) as env:
            env.setup_repo_structure()

            issue = _make_issue(42, "Objective: Fan-Out", _FAN_OUT_BODY)
            issues = FakeGitHubIssues(issues={42: issue})
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                default_branches={env.cwd: "main"},
                trunk_branches={env.cwd: "main"},
                current_branches={env.cwd: "main"},
            )
            github = FakeGitHub(authenticated=True, issues_gateway=issues)
            ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

            result = runner.invoke(
                cli,
                ["objective", "plan", "42", "--all-unblocked"],
                obj=ctx,
                catch_exceptions=False,
            )

            assert result.exit_code == 0

            # 2 nodes dispatched, but only 1 update_issue_body call for objective #42
            assert len(github.triggered_workflows) == 2
            objective_updates = [
                (num, body) for num, body in issues.updated_bodies if num == 42
            ]
            assert len(objective_updates) == 1

            # The single write should contain both draft PR references
            _issue_number, final_body = objective_updates[0]
            # FakeGitHub assigns PR numbers starting at 999
            assert "#999" in final_body
            assert "#1000" in final_body
