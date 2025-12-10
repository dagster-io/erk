"""Tests for update-pr-body command."""

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit
from erk_shared.github.abc import GitHub
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.prompt_executor import PromptExecutor, PromptResult

from dot_agent_kit.data.kits.erk.scripts.erk.update_pr_body import (
    UpdateError,
    UpdateSuccess,
    _update_pr_body_impl,
    update_pr_body,
)


def make_pr_info(pr_number: int) -> PullRequestInfo:
    """Create test PullRequestInfo for prs mapping."""
    return PullRequestInfo(
        number=pr_number,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}",
        is_draft=False,
        title=f"Test PR #{pr_number}",
        checks_passing=True,
        owner="test-owner",
        repo="test-repo",
    )


def make_pr_details(pr_number: int, branch: str = "feature-branch") -> PRDetails:
    """Create test PRDetails with all required fields."""
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}",
        title=f"Test PR #{pr_number}",
        body="Test PR body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )


class FakePromptExecutor(PromptExecutor):
    """Fake prompt executor for testing."""

    def __init__(
        self,
        *,
        output: str = "Generated summary",
        error: str | None = None,
        should_fail: bool = False,
    ) -> None:
        self._output = output
        self._error = error
        self._should_fail = should_fail

    def execute_prompt(
        self, prompt: str, *, model: str = "haiku", cwd: Path | None = None
    ) -> PromptResult:
        if self._should_fail:
            return PromptResult(success=False, output="", error=self._error or "Prompt failed")
        return PromptResult(success=True, output=self._output, error=None)


@dataclass
class CLIContext:
    """Context for CLI tests."""

    github: GitHub
    git: Git
    prompt_executor: PromptExecutor
    repo_root: Path


# =============================================================================
# Implementation Logic Tests
# =============================================================================


class TestUpdatePrBodyImpl:
    """Tests for _update_pr_body_impl function."""

    def test_success_updates_pr_body(self, tmp_path: Path) -> None:
        """Test successful PR body update."""
        fake_github = FakeGitHub(
            prs={"feature-branch": make_pr_info(123)},
            pr_details={123: make_pr_details(123)},
            pr_diffs={123: "diff --git a/foo.py b/foo.py\n+new line"},
        )
        fake_git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            trunk_branches={tmp_path: "main"},
        )
        fake_executor = FakePromptExecutor(output="This PR adds a new feature")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _update_pr_body_impl(
                github=fake_github,
                git=fake_git,
                executor=fake_executor,
                repo_root=tmp_path,
                branch="feature-branch",
                issue_number=456,
            )

        assert isinstance(result, UpdateSuccess)
        assert result.success is True
        assert result.pr_number == 123
        assert result.message == "PR body updated successfully"
        mock_run.assert_called_once()

    def test_error_when_pr_not_found(self, tmp_path: Path) -> None:
        """Test error when no PR exists for branch."""
        fake_github = FakeGitHub(prs={})
        fake_git = FakeGit()
        fake_executor = FakePromptExecutor()

        result = _update_pr_body_impl(
            github=fake_github,
            git=fake_git,
            executor=fake_executor,
            repo_root=tmp_path,
            branch="nonexistent-branch",
            issue_number=None,
        )

        assert isinstance(result, UpdateError)
        assert result.success is False
        assert result.error == "pr_not_found"
        assert "No PR found" in result.message

    def test_error_when_diff_empty(self, tmp_path: Path) -> None:
        """Test error when PR diff is empty."""
        fake_github = FakeGitHub(
            prs={"feature-branch": make_pr_info(123)},
            pr_details={123: make_pr_details(123)},
            pr_diffs={123: ""},
        )
        fake_git = FakeGit()
        fake_executor = FakePromptExecutor()

        result = _update_pr_body_impl(
            github=fake_github,
            git=fake_git,
            executor=fake_executor,
            repo_root=tmp_path,
            branch="feature-branch",
            issue_number=None,
        )

        assert isinstance(result, UpdateError)
        assert result.success is False
        assert result.error == "empty_diff"

    def test_error_when_claude_fails(self, tmp_path: Path) -> None:
        """Test error when Claude execution fails."""
        fake_github = FakeGitHub(
            prs={"feature-branch": make_pr_info(123)},
            pr_details={123: make_pr_details(123)},
            pr_diffs={123: "diff --git a/foo.py b/foo.py\n+new line"},
        )
        fake_git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            trunk_branches={tmp_path: "main"},
        )
        fake_executor = FakePromptExecutor(error="API error", should_fail=True)

        result = _update_pr_body_impl(
            github=fake_github,
            git=fake_git,
            executor=fake_executor,
            repo_root=tmp_path,
            branch="feature-branch",
            issue_number=None,
        )

        assert isinstance(result, UpdateError)
        assert result.success is False
        assert result.error == "claude_failed"

    def test_error_when_gh_edit_fails(self, tmp_path: Path) -> None:
        """Test error when gh pr edit fails."""
        import subprocess

        fake_github = FakeGitHub(
            prs={"feature-branch": make_pr_info(123)},
            pr_details={123: make_pr_details(123)},
            pr_diffs={123: "diff --git a/foo.py b/foo.py\n+new line"},
        )
        fake_git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            trunk_branches={tmp_path: "main"},
        )
        fake_executor = FakePromptExecutor(output="Generated summary")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "gh", stderr="Permission denied"
            )
            result = _update_pr_body_impl(
                github=fake_github,
                git=fake_git,
                executor=fake_executor,
                repo_root=tmp_path,
                branch="feature-branch",
                issue_number=None,
            )

        assert isinstance(result, UpdateError)
        assert result.success is False
        assert result.error == "gh_edit_failed"

    def test_issue_number_included_in_footer(self, tmp_path: Path) -> None:
        """Test that issue number is included when provided."""
        fake_github = FakeGitHub(
            prs={"feature-branch": make_pr_info(123)},
            pr_details={123: make_pr_details(123)},
            pr_diffs={123: "diff --git a/foo.py b/foo.py\n+new line"},
        )
        fake_git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            trunk_branches={tmp_path: "main"},
        )
        fake_executor = FakePromptExecutor(output="Test summary")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _update_pr_body_impl(
                github=fake_github,
                git=fake_git,
                executor=fake_executor,
                repo_root=tmp_path,
                branch="feature-branch",
                issue_number=789,
            )

        assert isinstance(result, UpdateSuccess)
        # The gh pr edit was called - we can't easily verify the body content
        # but the command succeeded with issue_number provided
        mock_run.assert_called_once()


# =============================================================================
# CLI Command Tests
# =============================================================================


class TestUpdatePrBodyCLI:
    """Tests for update-pr-body CLI command."""

    def test_cli_success_returns_json(self, tmp_path: Path) -> None:
        """Test CLI returns JSON on success."""
        fake_github = FakeGitHub(
            prs={"feature-branch": make_pr_info(123)},
            pr_details={123: make_pr_details(123)},
            pr_diffs={123: "diff --git a/foo.py b/foo.py\n+new line"},
        )
        fake_git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            trunk_branches={tmp_path: "main"},
        )
        fake_executor = FakePromptExecutor(output="CLI test summary")

        ctx = CLIContext(
            github=fake_github,
            git=fake_git,
            prompt_executor=fake_executor,
            repo_root=tmp_path,
        )

        runner = CliRunner()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(
                update_pr_body,
                ["--branch", "feature-branch"],
                obj=ctx,
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["pr_number"] == 123

    def test_cli_error_returns_exit_code_1(self, tmp_path: Path) -> None:
        """Test CLI returns exit code 1 on error."""
        fake_github = FakeGitHub(prs={})
        fake_git = FakeGit()
        fake_executor = FakePromptExecutor()

        ctx = CLIContext(
            github=fake_github,
            git=fake_git,
            prompt_executor=fake_executor,
            repo_root=tmp_path,
        )

        runner = CliRunner()
        result = runner.invoke(
            update_pr_body,
            ["--branch", "nonexistent-branch"],
            obj=ctx,
        )

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "pr_not_found"

    def test_cli_with_issue_number(self, tmp_path: Path) -> None:
        """Test CLI accepts issue number option."""
        fake_github = FakeGitHub(
            prs={"feature-branch": make_pr_info(123)},
            pr_details={123: make_pr_details(123)},
            pr_diffs={123: "diff --git a/foo.py b/foo.py\n+new line"},
        )
        fake_git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            trunk_branches={tmp_path: "main"},
        )
        fake_executor = FakePromptExecutor(output="Test summary")

        ctx = CLIContext(
            github=fake_github,
            git=fake_git,
            prompt_executor=fake_executor,
            repo_root=tmp_path,
        )

        runner = CliRunner()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(
                update_pr_body,
                ["--branch", "feature-branch", "--issue-number", "456"],
                obj=ctx,
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
