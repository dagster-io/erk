"""Tests for CoreSubmitStrategy.

Tests the core PR submission strategy that uses git push + gh pr create.
"""

from pathlib import Path

from erk_shared.context.testing import context_for_test
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.core import CoreSubmitStrategy
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo


class TestCoreSubmitStrategy:
    """Tests for CoreSubmitStrategy."""

    def test_returns_error_when_github_not_authenticated(self, tmp_path: Path) -> None:
        """Test that unauthenticated GitHub returns error."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=False)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = CoreSubmitStrategy(plans_repo=None)
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyError)
        assert result.error_type == "github_auth_failed"

    def test_returns_error_when_not_on_branch(self, tmp_path: Path) -> None:
        """Test that detached HEAD state returns error."""
        git = FakeGit(
            current_branches={tmp_path: None},  # Detached HEAD
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = CoreSubmitStrategy(plans_repo=None)
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyError)
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

        strategy = CoreSubmitStrategy(plans_repo=None)
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyError)
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

        strategy = CoreSubmitStrategy(plans_repo=None)
        events = list(strategy.execute(ctx, tmp_path, force=False))

        # Find the completion event
        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyResult)
        assert result.pr_number == 999  # FakeGitHub returns 999
        assert result.branch_name == "feature-branch"
        assert result.base_branch == "main"
        assert result.was_created is True
        assert result.graphite_url is None  # Core never has Graphite URL

        # Verify GitHub was called to create PR
        assert len(github.created_prs) == 1

        # Verify git push was called
        assert len(git._pushed_branches) == 1

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

        strategy = CoreSubmitStrategy(plans_repo=None)
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyResult)
        assert result.pr_number == 42
        assert result.was_created is False  # Updated existing

        # Should NOT have created a new PR
        assert len(github.created_prs) == 0

    def test_returns_error_when_push_rejected(self, tmp_path: Path) -> None:
        """Test that push rejection returns user-friendly error."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
            push_to_remote_raises=RuntimeError(
                "Failed to push branch 'feature-branch'\n"
                "stderr: ! [rejected] feature-branch -> feature-branch (non-fast-forward)"
            ),
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = CoreSubmitStrategy(plans_repo=None)
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyError)
        assert result.error_type == "branch_diverged"

    def test_force_push_succeeds_when_diverged(self, tmp_path: Path) -> None:
        """Test that force flag allows push when branch has diverged."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = CoreSubmitStrategy(plans_repo=None)
        events = list(strategy.execute(ctx, tmp_path, force=True))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyResult)

        # Should have force pushed
        assert len(git._pushed_branches) == 1
        pushed = git._pushed_branches[0]
        assert pushed.force is True

    def test_includes_plans_repo_in_pr(self, tmp_path: Path) -> None:
        """Test that plans_repo is passed to execute_core_submit."""
        # Create .impl/issue.json
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_file = impl_dir / "issue.json"
        issue_file.write_text(
            """{
                "issue_number": 123,
                "issue_url": "https://github.com/owner/plans-repo/issues/123",
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

        strategy = CoreSubmitStrategy(plans_repo="owner/plans-repo")
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        result = completion[0].result
        assert isinstance(result, SubmitStrategyResult)

        # PR body should contain cross-repo closing text
        assert len(github.created_prs) == 1
        _, _, body, _, _ = github.created_prs[0]
        assert "owner/plans-repo#123" in body

    def test_emits_progress_events(self, tmp_path: Path) -> None:
        """Test that progress events are emitted throughout execution."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = CoreSubmitStrategy(plans_repo=None)
        events = list(strategy.execute(ctx, tmp_path, force=False))

        progress_events = [e for e in events if isinstance(e, ProgressEvent)]
        # Should have multiple progress events for each step
        assert len(progress_events) >= 5  # Auth, branch, commits, push, PR

        # Check some specific progress messages
        messages = [e.message for e in progress_events]
        assert any("authentication" in m.lower() for m in messages)
        assert any("branch" in m.lower() for m in messages)

    def test_graphite_url_is_always_none(self, tmp_path: Path) -> None:
        """Test that Core strategy never sets graphite_url."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            commits_ahead={(tmp_path, "main"): 2},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = CoreSubmitStrategy(plans_repo=None)
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        result = completion[0].result
        assert isinstance(result, SubmitStrategyResult)
        assert result.graphite_url is None  # Core never has Graphite URL
