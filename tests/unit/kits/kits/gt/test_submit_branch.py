"""Tests for submit_branch kit CLI command using fake ops.

Testing Generator-Based Operations
----------------------------------
Operations in erk_shared.integrations.gt.operations yield ProgressEvent and
CompletionEvent objects. To test them:

1. Use render_events() to consume the generator and get the final result:

    result = render_events(execute_pre_analysis(ops, tmp_path))
    assert isinstance(result, PreAnalysisResult)

2. render_events() handles all the iteration and returns the CompletionEvent's
   result, which is what you typically want to assert on.

3. ProgressEvents are for UI feedback - render_events() prints them but they
   don't affect the returned result.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from erk_shared.github.pr_footer import build_pr_body_footer
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.finalize import execute_finalize
from erk_shared.integrations.gt.operations.pre_analysis import execute_pre_analysis
from erk_shared.integrations.gt.operations.preflight import execute_preflight
from erk_shared.integrations.gt.types import (
    FinalizeResult,
    PostAnalysisError,
    PreAnalysisError,
    PreAnalysisResult,
    PreflightResult,
)
from tests.unit.kits.kits.gt.fake_ops import FakeGtKitOps


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


def extract_json_from_output(output: str) -> dict:
    """Extract JSON object from CLI output that may contain styled messages.

    The CLI outputs styled messages (with ↳, ✓, etc.) followed by JSON.
    This function finds and parses the JSON portion.
    """
    # Find the start of JSON (first '{')
    json_start = output.find("{")
    if json_start == -1:
        raise ValueError(f"No JSON found in output: {output}")

    # Find matching closing brace
    brace_count = 0
    for i, char in enumerate(output[json_start:], start=json_start):
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0:
                json_str = output[json_start : i + 1]
                return json.loads(json_str)

    raise ValueError(f"No complete JSON found in output: {output}")


class TestBuildPRBodyFooter:
    """Tests for build_pr_body_footer() function.

    The function builds a footer section for PR bodies containing:
    - Separator (---) at start
    - Checkout command with && erk pr sync
    """

    def test_build_footer_with_pr_number(self) -> None:
        """Test building footer with a PR number."""
        result = build_pr_body_footer(456)

        assert "---" in result
        assert "erk pr checkout 456 && erk pr sync" in result


class TestPreAnalysisExecution:
    """Tests for pre-analysis phase execution logic."""

    def test_pre_analysis_gt_not_authenticated(self, tmp_path: Path) -> None:
        """Test error when Graphite CLI is not authenticated."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "gt_not_authenticated"
        assert "Graphite CLI (gt) is not authenticated" in result.message
        assert result.details["fix"] == "Run 'gt auth' to authenticate with Graphite"
        assert result.details["authenticated"] is False

    def test_pre_analysis_gh_not_authenticated(self, tmp_path: Path) -> None:
        """Test error when GitHub CLI is not authenticated (gt is authenticated)."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gh_unauthenticated()
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "gh_not_authenticated"
        assert "GitHub CLI (gh) is not authenticated" in result.message
        assert result.details["fix"] == "Run 'gh auth login' to authenticate with GitHub"
        assert result.details["authenticated"] is False

    def test_pre_analysis_gt_checked_before_gh(self, tmp_path: Path) -> None:
        """Test that Graphite authentication is checked before GitHub."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
            .with_gh_unauthenticated()
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        # When both are unauthenticated, gt should be reported first
        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "gt_not_authenticated"

    def test_pre_analysis_with_uncommitted_changes(self, tmp_path: Path) -> None:
        """Test pre-analysis when uncommitted changes exist (should commit them)."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.txt"])
            .with_commits(0)  # Start with no commits
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.branch_name == "feature-branch"
        assert result.uncommitted_changes_committed is True
        assert "Committed uncommitted changes" in result.message

    def test_pre_analysis_without_uncommitted_changes(self, tmp_path: Path) -> None:
        """Test pre-analysis when no uncommitted changes exist."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)  # Single commit, no uncommitted files
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.uncommitted_changes_committed is False
        assert result.commit_count == 1
        assert result.squashed is False
        assert "Single commit, no squash needed" in result.message

    def test_pre_analysis_with_multiple_commits(self, tmp_path: Path) -> None:
        """Test pre-analysis with 2+ commits (should squash)."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)  # Multiple commits
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.commit_count == 3
        assert result.squashed is True
        assert "Squashed 3 commits into 1" in result.message

    def test_pre_analysis_single_commit(self, tmp_path: Path) -> None:
        """Test pre-analysis with single commit (no squash needed)."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)  # Single commit
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.commit_count == 1
        assert result.squashed is False
        assert "Single commit, no squash needed" in result.message

    def test_pre_analysis_no_branch(self, tmp_path: Path) -> None:
        """Test error when current branch cannot be determined."""
        # Use with_no_branch builder to configure empty current branch
        ops = FakeGtKitOps().with_repo_root(str(tmp_path)).with_no_branch()

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "no_branch"
        assert "Could not determine current branch" in result.message

    def test_pre_analysis_no_parent(self, tmp_path: Path) -> None:
        """Test error when parent branch cannot be determined."""
        # Use with_orphan_branch to set a branch without parent tracking
        ops = FakeGtKitOps().with_repo_root(str(tmp_path)).with_orphan_branch("orphan-branch")

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "no_parent"
        assert "Could not determine parent branch" in result.message

    def test_pre_analysis_no_commits(self, tmp_path: Path) -> None:
        """Test error when branch has no commits."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(0)  # No commits
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "no_commits"
        assert "No commits found in branch" in result.message

    def test_pre_analysis_squash_fails(self, tmp_path: Path) -> None:
        """Test error when gt squash fails."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)  # Multiple commits to trigger squash
            .with_squash_failure()  # Configure squash to fail
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "squash_failed"
        assert "Failed to squash commits" in result.message

    def test_pre_analysis_detects_squash_conflict(self, tmp_path: Path) -> None:
        """Test that squash conflicts are detected and reported correctly."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)  # Multiple commits to trigger squash
            .with_squash_failure(
                stdout="",
                stderr=(
                    "error: could not apply abc123... commit message\n"
                    "CONFLICT (content): Merge conflict in file.txt"
                ),
            )
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "squash_conflict"
        assert "Merge conflicts detected while squashing commits" in result.message
        stderr = result.details["stderr"]
        assert isinstance(stderr, str)
        assert "CONFLICT" in stderr

    def test_pre_analysis_squash_conflict_preserves_output(self, tmp_path: Path) -> None:
        """Test that conflict errors include stdout/stderr for debugging."""
        test_stdout = "Some output"
        test_stderr = "CONFLICT (content): Merge conflict in README.md"

        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(2)
            .with_squash_failure(stdout=test_stdout, stderr=test_stderr)
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "squash_conflict"
        assert result.details["stdout"] == test_stdout
        assert result.details["stderr"] == test_stderr
        assert result.details["branch_name"] == "feature-branch"

    def test_pre_analysis_detects_pr_conflicts_from_github(self, tmp_path: Path) -> None:
        """Test that PR conflicts are detected and reported informational (not blocking)."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="master")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
            .with_pr_conflicts(123)
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        # Assert: Should succeed with conflict info included
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.has_conflicts is True
        assert result.conflict_details is not None
        assert result.conflict_details["pr_number"] == "123"
        assert result.conflict_details["parent_branch"] == "master"
        assert result.conflict_details["detection_method"] == "github_api"

    def test_pre_analysis_proceeds_when_no_conflicts(self, tmp_path: Path) -> None:
        """Test that workflow proceeds normally when no conflicts exist."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="master")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        # Assert: Should succeed with no conflicts
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.has_conflicts is False
        assert result.conflict_details is None

    def test_pre_analysis_fallback_to_git_merge_tree(self, tmp_path: Path) -> None:
        """Test fallback to git merge-tree when no PR exists (informational, not blocking)."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="master")
            .with_commits(1)
            .with_merge_conflict("master", "feature-branch")  # Use builder method
        )

        # No PR configured - should fallback to git merge-tree
        result = render_events(execute_pre_analysis(ops, tmp_path))

        # Assert: Should succeed with conflict info via git merge-tree
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.has_conflicts is True
        assert result.conflict_details is not None
        assert result.conflict_details["detection_method"] == "git_merge_tree"

    def test_pre_analysis_proceeds_on_unknown_mergeability(self, tmp_path: Path) -> None:
        """Test that UNKNOWN mergeability doesn't block workflow."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="master")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
            .with_pr_mergeability(123, "UNKNOWN", "UNKNOWN")
        )

        result = render_events(execute_pre_analysis(ops, tmp_path))

        # Assert: Should proceed with warning
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True


class TestExecutePreflight:
    """Tests for execute_preflight() function."""

    @patch("erk_shared.integrations.gt.operations.preflight.time.sleep")
    def test_preflight_success(self, mock_sleep: Mock, tmp_path: Path) -> None:
        """Test successful preflight execution."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_remote_url("https://github.com/org/repo.git")
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        result = render_events(execute_preflight(ops, tmp_path, "test-session-123"))

        assert isinstance(result, PreflightResult)
        assert result.success is True
        assert result.pr_number == 123
        assert result.pr_url == "https://github.com/org/repo/pull/123"
        assert result.branch_name == "feature-branch"
        assert ".erk/scratch/sessions/test-session-123/" in result.diff_file
        assert result.diff_file.endswith(".diff")
        assert result.current_branch == "feature-branch"
        assert result.parent_branch == "main"

        # Clean up temp file
        diff_path = Path(result.diff_file)
        if diff_path.exists():
            diff_path.unlink()

    def test_preflight_pre_analysis_error(self, tmp_path: Path) -> None:
        """Test preflight returns error when pre-analysis fails."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
        )

        result = render_events(execute_preflight(ops, tmp_path, "test-session-123"))

        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "gt_not_authenticated"

    @patch("erk_shared.integrations.gt.operations.preflight.time.sleep")
    def test_preflight_submit_error(self, mock_sleep: Mock, tmp_path: Path) -> None:
        """Test preflight returns error when submit fails."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_failure(stderr="submit failed")
        )

        result = render_events(execute_preflight(ops, tmp_path, "test-session-123"))

        assert isinstance(result, PostAnalysisError)
        assert result.error_type == "submit_failed"


class TestExecuteFinalize:
    """Tests for execute_finalize() function."""

    def test_finalize_success(self, tmp_path: Path) -> None:
        """Test successful finalize execution."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_remote_url("https://github.com/org/repo.git")
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        pr_body = "This adds a great new feature"

        result = render_events(
            execute_finalize(
                ops,
                tmp_path,
                pr_number=123,
                pr_title="Add new feature",
                pr_body=pr_body,
                diff_file=None,
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        assert result.pr_number == 123
        assert result.pr_title == "Add new feature"
        assert result.branch_name == "feature-branch"

        # Verify PR was updated using mutation tracking
        github = ops.github
        assert (123, "Add new feature") in github.updated_pr_titles  # type: ignore[attr-defined]
        # Check body was updated (find the body in updated_pr_bodies list)
        bodies = [body for pr_num, body in github.updated_pr_bodies if pr_num == 123]  # type: ignore[attr-defined]
        assert len(bodies) > 0
        assert "This adds a great new feature" in bodies[0]

    def test_finalize_cleans_up_diff_file(self, tmp_path: Path) -> None:
        """Test that finalize cleans up the temp diff file."""
        # Create a temp diff file
        diff_file = tmp_path / "test.diff"
        diff_file.write_text("test diff content", encoding="utf-8")
        assert diff_file.exists()

        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_remote_url("https://github.com/org/repo.git")
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        pr_body = "Description"

        result = render_events(
            execute_finalize(
                ops,
                tmp_path,
                pr_number=123,
                pr_title="Add feature",
                pr_body=pr_body,
                diff_file=str(diff_file),
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        # Diff file should be cleaned up
        assert not diff_file.exists()

    def test_finalize_with_issue_reference(self, tmp_path: Path) -> None:
        """Test finalize includes metadata when issue reference exists."""
        # Create .impl/issue.json
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 456, "issue_url": "https://github.com/repo/issues/456", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}',
            encoding="utf-8",
        )

        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_remote_url("https://github.com/org/repo.git")
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        pr_body = "Description"

        result = render_events(
            execute_finalize(
                ops,
                tmp_path,
                pr_number=123,
                pr_title="Add feature",
                pr_body=pr_body,
                diff_file=None,
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        assert result.issue_number == 456

        # Verify PR body includes footer metadata using mutation tracking
        github = ops.github
        # Find the body in updated_pr_bodies list
        bodies = [body for pr_num, body in github.updated_pr_bodies if pr_num == 123]  # type: ignore[attr-defined]
        assert len(bodies) > 0
        final_pr_body = bodies[0]
        # Body comes first, then footer
        assert final_pr_body.startswith("Description")
        # Footer contains separator, issue closing reference, and checkout command
        assert "---" in final_pr_body
        assert "erk pr checkout 123 && erk pr sync" in final_pr_body
        # Closes #N is included when issue reference exists
        assert "Closes #456" in final_pr_body

    def test_finalize_amends_local_commit(self, tmp_path: Path) -> None:
        """Test that finalize amends local commit with PR title and body."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_remote_url("https://github.com/org/repo.git")
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        # Seed the FakeGit with an initial commit to amend
        fake_git = ops.git
        fake_git._commits.append((tmp_path, "Original message", []))  # type: ignore[attr-defined]

        pr_title = "Add new feature"
        pr_body = "This PR adds a great new feature"

        result = render_events(
            execute_finalize(
                ops,
                tmp_path,
                pr_number=123,
                pr_title=pr_title,
                pr_body=pr_body,
                diff_file=None,
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True

        # Verify local commit was amended with title and body
        assert len(fake_git._commits) == 1  # type: ignore[attr-defined]
        amended_message = fake_git._commits[-1][1]  # type: ignore[attr-defined]
        assert amended_message == "Add new feature\n\nThis PR adds a great new feature"

    def test_finalize_amends_commit_with_title_only(self, tmp_path: Path) -> None:
        """Test finalize amends commit correctly when PR has no body."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_remote_url("https://github.com/org/repo.git")
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        # Seed the FakeGit with an initial commit to amend
        fake_git = ops.git
        fake_git._commits.append((tmp_path, "Original message", []))  # type: ignore[attr-defined]

        pr_title = "Fix bug"
        pr_body = ""  # Empty body

        result = render_events(
            execute_finalize(
                ops,
                tmp_path,
                pr_number=123,
                pr_title=pr_title,
                pr_body=pr_body,
                diff_file=None,
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True

        # Verify local commit was amended with title only (no body)
        assert len(fake_git._commits) == 1  # type: ignore[attr-defined]
        amended_message = fake_git._commits[-1][1]  # type: ignore[attr-defined]
        assert amended_message == "Fix bug"
