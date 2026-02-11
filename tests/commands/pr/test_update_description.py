"""Tests for erk pr update-description command.

These tests verify the CLI layer behavior of the update-description command.
The command generates an AI-powered PR title/body and updates the PR on GitHub,
preserving existing header and footer metadata.
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.gateway.github.metadata.plan_header import format_plan_content_comment
from erk_shared.gateway.github.pr_footer import build_pr_body_footer
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.fakes.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import ErkIsolatedFsEnv, erk_isolated_fs_env
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_pr_details(
    *,
    number: int,
    branch: str,
    body: str = "",
    title: str = "WIP",
) -> PRDetails:
    """Create PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=title,
        body=body,
        base_ref_name="main",
        head_ref_name=branch,
        state="OPEN",
        is_draft=False,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def _make_issue_info(
    *,
    number: int,
    title: str,
    body: str,
) -> IssueInfo:
    """Create an IssueInfo for testing."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def _make_standard_fakes(
    env: ErkIsolatedFsEnv,
    *,
    branch_name: str = "feature",
    parent_branch: str = "main",
    pr_body: str = "",
    pr_number: int = 42,
    fake_github_issues: FakeGitHubIssues | None = None,
    prompt_output: str = "Add awesome feature\n\nThis PR adds an awesome new feature.",
    prompt_error: str | None = None,
    available: bool = True,
) -> tuple[FakeGit, FakeGraphite, FakeGitHub, FakePromptExecutor]:
    """Create standard fakes for update-description tests."""
    git = FakeGit(
        git_common_dirs={env.cwd: env.git_dir},
        repository_roots={env.cwd: env.git_dir},
        local_branches={env.cwd: ["main", branch_name]},
        default_branches={env.cwd: "main"},
        trunk_branches={env.git_dir: "main"},
        current_branches={env.cwd: branch_name},
        diff_to_branch={(env.cwd, parent_branch): "diff --git a/file.py b/file.py\n+new content"},
        commit_messages_since={(env.cwd, parent_branch): ["Initial implementation"]},
    )

    graphite = FakeGraphite(
        authenticated=True,
        branches={
            branch_name: BranchMetadata(
                name=branch_name,
                parent=parent_branch,
                children=[],
                is_trunk=False,
                commit_sha=None,
            ),
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=[branch_name],
                is_trunk=True,
                commit_sha=None,
            ),
        },
    )

    pr_details = _make_pr_details(
        number=pr_number,
        branch=branch_name,
        body=pr_body,
    )
    github = FakeGitHub(
        authenticated=True,
        prs_by_branch={branch_name: pr_details},
        issues_gateway=fake_github_issues,
    )

    executor = FakePromptExecutor(
        available=available,
        simulated_prompt_output=prompt_output if prompt_error is None else None,
        simulated_prompt_error=prompt_error,
    )

    return git, graphite, github, executor


def test_fails_when_claude_not_available() -> None:
    """Test that command fails when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        executor = FakePromptExecutor(available=False)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["update-description"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output


def test_fails_when_not_on_branch() -> None:
    """Test that command fails when not on a branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: None},
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["update-description"], obj=ctx)

        assert result.exit_code != 0
        assert "Not on a branch" in result.output


def test_fails_when_no_pr() -> None:
    """Test that command fails when no PR exists for the branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )

        # No PRs configured
        github = FakeGitHub(authenticated=True)
        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, github=github, prompt_executor=executor
        )

        result = runner.invoke(pr_group, ["update-description"], obj=ctx)

        assert result.exit_code != 0
        assert "No pull request found" in result.output


def test_success_updates_pr() -> None:
    """Test successful update-description generates title/body and updates PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git, graphite, github, executor = _make_standard_fakes(env)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, github=github, prompt_executor=executor
        )

        result = runner.invoke(pr_group, ["update-description"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #42 updated" in result.output
        assert "Add awesome feature" in result.output

        # Verify PR was updated on GitHub
        assert len(github.updated_pr_titles) == 1
        assert github.updated_pr_titles[0] == (42, "Add awesome feature")

        assert len(github.updated_pr_bodies) == 1
        pr_number, body = github.updated_pr_bodies[0]
        assert pr_number == 42
        assert "awesome new feature" in body


def test_preserves_header_and_footer() -> None:
    """Test that existing header and footer metadata are preserved."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        header = "**Plan:** #123"
        footer_content = build_pr_body_footer(
            42,
            issue_number=123,
            plans_repo=None,
        )
        existing_body = f"{header}\n\nOld content\n\n---\n{footer_content.lstrip()}"

        git, graphite, github, executor = _make_standard_fakes(
            env, pr_body=existing_body
        )

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, github=github, prompt_executor=executor
        )

        result = runner.invoke(pr_group, ["update-description"], obj=ctx)

        assert result.exit_code == 0

        # Verify header and footer are preserved in updated body
        _, updated_body = github.updated_pr_bodies[0]
        assert "**Plan:** #123" in updated_body
        assert "erk pr checkout" in updated_body


def test_uses_graphite_parent() -> None:
    """Test that update-description uses Graphite parent branch, not trunk.

    Stack: main (trunk) -> branch-1 -> branch-2 (current)
    Expected: Diff computed against branch-1, not main
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "branch-1", "branch-2"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "branch-2"},
            diff_to_branch={(env.cwd, "branch-1"): "diff --git a/file2.py b/file2.py\n+feature 2"},
            commit_messages_since={(env.cwd, "branch-1"): ["Add feature 2"]},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "branch-2": BranchMetadata(
                    name="branch-2",
                    parent="branch-1",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "branch-1": BranchMetadata(
                    name="branch-1",
                    parent="main",
                    children=["branch-2"],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["branch-1"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )

        pr_details = _make_pr_details(number=99, branch="branch-2")
        github = FakeGitHub(
            authenticated=True,
            prs_by_branch={"branch-2": pr_details},
        )
        executor = FakePromptExecutor(
            available=True,
            simulated_prompt_output="Add feature 2\n\nThis adds feature 2.",
        )

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, github=github, prompt_executor=executor
        )

        result = runner.invoke(pr_group, ["update-description"], obj=ctx)

        assert result.exit_code == 0

        # Verify the prompt was called with correct branches
        assert len(executor.prompt_calls) == 1
        prompt, _system_prompt, _dangerous = executor.prompt_calls[0]
        # Should contain branch-1 as parent (Graphite parent)
        assert "branch-1" in prompt
        assert "branch-2" in prompt


def test_embeds_plan_context() -> None:
    """Test that plan context is embedded in the updated PR body."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_body = format_plan_header_body_for_test(plan_comment_id=1000)
        plan_issue = _make_issue_info(number=123, title="Plan: Fix bug", body=plan_body)
        comment = IssueComment(
            id=1000,
            body=format_plan_content_comment("# Plan\nFix the bug."),
            url="https://github.com/test-owner/test-repo/issues/123#issuecomment-1000",
            author="testuser",
        )
        fake_github_issues = FakeGitHubIssues(
            issues={123: plan_issue},
            comments_with_urls={123: [comment]},
        )

        git, graphite, github, executor = _make_standard_fakes(
            env,
            branch_name="P123-fix-bug",
            fake_github_issues=fake_github_issues,
        )

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, github=github, prompt_executor=executor
        )

        result = runner.invoke(pr_group, ["update-description"], obj=ctx)

        assert result.exit_code == 0
        assert "Incorporating plan from issue #123" in result.output

        # Verify plan details section is in the updated body
        _, updated_body = github.updated_pr_bodies[0]
        assert "Implementation Plan" in updated_body
        assert "Issue #123" in updated_body
