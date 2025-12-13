"""Unit tests for core PR submission operation.

Tests the execute_core_submit() function which handles git push + gh pr create
without requiring Graphite.
"""

from pathlib import Path

import pytest

from erk_shared.context.testing import context_for_test
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.pr.submit import execute_core_submit
from erk_shared.integrations.pr.types import CoreSubmitError, CoreSubmitResult


class TestExecuteCoreSubmit:
    """Tests for execute_core_submit function."""

    def test_returns_error_when_github_not_authenticated(self, tmp_path: Path) -> None:
        """Test that unauthenticated GitHub returns error."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=False)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        events = list(execute_core_submit(ctx, tmp_path, "Title", "Body"))

        # Find the completion event
        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, CoreSubmitError)
        assert result.error_type == "github_auth_failed"
        assert "GitHub CLI is not authenticated" in result.message

    def test_returns_error_when_not_on_branch(self, tmp_path: Path) -> None:
        """Test that detached HEAD state returns error."""
        git = FakeGit(
            current_branches={tmp_path: None},  # Detached HEAD
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        events = list(execute_core_submit(ctx, tmp_path, "Title", "Body"))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, CoreSubmitError)
        assert result.error_type == "no_branch"

    def test_returns_error_when_no_commits_ahead(self, tmp_path: Path) -> None:
        """Test that having no commits ahead of trunk returns error."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 0},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        events = list(execute_core_submit(ctx, tmp_path, "Title", "Body"))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, CoreSubmitError)
        assert result.error_type == "no_commits"

    def test_creates_new_pr_when_none_exists(self, tmp_path: Path) -> None:
        """Test successful PR creation when no PR exists for the branch."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        events = list(execute_core_submit(ctx, tmp_path, "Title", "Body"))

        # Find progress events
        progress_events = [e for e in events if isinstance(e, ProgressEvent)]
        assert len(progress_events) > 0  # Should have multiple progress events

        # Find the completion event
        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, CoreSubmitResult)
        assert result.success is True
        assert result.was_created is True
        assert result.pr_number == 999  # FakeGitHub returns 999
        assert result.branch_name == "feature-branch"

        # Verify GitHub was called to create PR
        assert len(github.created_prs) == 1
        branch, title, body, base, draft = github.created_prs[0]
        assert branch == "feature-branch"
        assert title == "Title"
        assert base == "main"

        # Verify git push was called
        assert len(git._pushed_branches) == 1
        remote, branch_pushed, set_upstream = git._pushed_branches[0]
        assert remote == "origin"
        assert branch_pushed == "feature-branch"
        assert set_upstream is True

    def test_updates_existing_pr_when_found(self, tmp_path: Path) -> None:
        """Test that existing PR is updated instead of creating new one."""
        existing_pr = PRDetails(
            number=42,
            url="https://github.com/owner/repo/pull/42",
            title="Existing PR",
            body="Existing body",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature-branch",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
            labels=("bug",),
        )
        # Create the PullRequestInfo for branch lookup
        pr_info = PullRequestInfo(
            number=42,
            state="OPEN",
            url="https://github.com/owner/repo/pull/42",
            is_draft=False,
            title="Existing PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
        )
        github = FakeGitHub(
            authenticated=True,
            prs={"feature-branch": pr_info},
            pr_details={42: existing_pr},
        )

        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        events = list(execute_core_submit(ctx, tmp_path, "New Title", "New Body"))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, CoreSubmitResult)
        assert result.success is True
        assert result.was_created is False  # Updated existing
        assert result.pr_number == 42
        assert result.branch_name == "feature-branch"

        # Should NOT have created a new PR
        assert len(github.created_prs) == 0

    def test_commits_uncommitted_changes(self, tmp_path: Path) -> None:
        """Test that uncommitted changes are committed before push."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 1},
            file_statuses={tmp_path: ([], ["modified.py"], [])},  # Has uncommitted changes
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        list(execute_core_submit(ctx, tmp_path, "Title", "Body"))

        # Should have committed WIP changes
        assert len(git._commits) == 1
        cwd, message, _files = git._commits[0]
        assert cwd == tmp_path
        assert "WIP" in message

    def test_includes_issue_link_when_present(self, tmp_path: Path) -> None:
        """Test that issue reference from .impl/issue.json is included in PR."""
        # Create .impl/issue.json
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_file = impl_dir / "issue.json"
        issue_file.write_text(
            """{
                "issue_number": 123,
                "issue_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z"
            }""",
            encoding="utf-8",
        )

        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        events = list(execute_core_submit(ctx, tmp_path, "Title", "Body"))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        result = completion[0].result
        assert isinstance(result, CoreSubmitResult)
        assert result.issue_number == 123

        # PR body should contain closing text
        assert len(github.created_prs) == 1
        _, _, body, _, _ = github.created_prs[0]
        assert "Closes #123" in body

    def test_emits_progress_events(self, tmp_path: Path) -> None:
        """Test that progress events are emitted throughout the operation."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        events = list(execute_core_submit(ctx, tmp_path, "Title", "Body"))

        progress_events = [e for e in events if isinstance(e, ProgressEvent)]
        # Should have multiple progress events for each step
        assert len(progress_events) >= 5  # Auth, branch, commits, push, PR

        # Check some specific progress messages
        messages = [e.message for e in progress_events]
        assert any("authentication" in m.lower() for m in messages)
        assert any("branch" in m.lower() for m in messages)

    def test_returns_error_when_push_rejected_non_fast_forward(self, tmp_path: Path) -> None:
        """Test that non-fast-forward push rejection returns user-friendly error."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
            push_to_remote_raises=RuntimeError(
                "Failed to push branch 'feature-branch' to remote 'origin'\n"
                "stderr: error: failed to push some refs to 'origin'\n"
                "hint: Updates were rejected because the tip of your current branch is behind\n"
                "hint: its remote counterpart. If you want to integrate the remote changes,\n"
                "hint: use 'git pull' before pushing again.\n"
                "hint: See the 'Note about fast-forwards' in 'git push --help' for details.\n"
                "To github.com:owner/repo.git\n"
                " ! [rejected]        feature-branch -> feature-branch (non-fast-forward)"
            ),
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        events = list(execute_core_submit(ctx, tmp_path, "Title", "Body"))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, CoreSubmitError)
        assert result.error_type == "branch_diverged"
        assert "git pull --rebase" in result.message
        assert "feature-branch" in result.message

    def test_returns_error_when_push_rejected_generic(self, tmp_path: Path) -> None:
        """Test that generic rejected push returns user-friendly error."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
            push_to_remote_raises=RuntimeError(
                "Failed to push branch 'feature-branch'\n"
                "stderr: ! [rejected] feature-branch -> feature-branch (fetch first)"
            ),
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        events = list(execute_core_submit(ctx, tmp_path, "Title", "Body"))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, CoreSubmitError)
        assert result.error_type == "branch_diverged"
        assert "diverged from remote" in result.message

    def test_reraises_non_push_rejection_errors(self, tmp_path: Path) -> None:
        """Test that non-rejection errors are re-raised."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
            push_to_remote_raises=RuntimeError("Network connection failed"),
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        with pytest.raises(RuntimeError, match="Network connection failed"):
            list(execute_core_submit(ctx, tmp_path, "Title", "Body"))
