"""Unit tests for GraphiteBranchManager.

Tests branch operations including:
- delete_branch() with LBYL fallback to git when Graphite can't handle the branch
- create_branch() with Graphite tracking
- get_pr_for_branch() with GitHub fallback when not in Graphite cache
"""

from pathlib import Path

from erk_shared.gateway.branch_manager.graphite import GraphiteBranchManager
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata


def test_delete_branch_uses_graphite_when_tracked_and_not_diverged() -> None:
    """When branch is tracked and SHA matches, Graphite delete is used."""
    branch_sha = "abc123"
    repo_root = Path("/repo")

    fake_git = FakeGit(
        branch_heads={"feature-branch": branch_sha},
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite(
        branches={
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha=branch_sha,  # Same SHA - not diverged
            ),
        },
    )
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=FakeGitHub(),
    )
    manager.delete_branch(repo_root, "feature-branch")

    # Graphite delete was called
    assert fake_graphite.delete_branch_calls == [(repo_root, "feature-branch")]
    # Git delete was NOT called
    assert fake_git.deleted_branches == []


def test_delete_branch_falls_back_to_git_when_untracked() -> None:
    """When branch is not tracked by Graphite, git delete is used."""
    repo_root = Path("/repo")

    fake_git = FakeGit(
        branch_heads={"feature-branch": "abc123"},
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite(
        branches={},  # Branch not tracked
    )
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=FakeGitHub(),
    )
    manager.delete_branch(repo_root, "feature-branch")

    # Graphite delete was NOT called
    assert fake_graphite.delete_branch_calls == []
    # Git delete WAS called with force=True
    assert fake_git.deleted_branches == ["feature-branch"]


def test_delete_branch_uses_graphite_even_when_diverged() -> None:
    """When branch SHA differs from Graphite's cache, Graphite delete is STILL used.

    gt delete -f handles diverged branches gracefully - it cleans up metadata
    regardless of SHA mismatch. Previously this fell back to plain git which
    left orphaned Graphite metadata (bug fix).
    """
    repo_root = Path("/repo")

    fake_git = FakeGit(
        branch_heads={"feature-branch": "actual-sha-456"},
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite(
        branches={
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha="cached-sha-123",  # Different SHA - diverged
            ),
        },
    )
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=FakeGitHub(),
    )
    manager.delete_branch(repo_root, "feature-branch")

    # Graphite delete WAS called (gt delete -f handles diverged branches)
    assert fake_graphite.delete_branch_calls == [(repo_root, "feature-branch")]
    # Git delete was NOT called
    assert fake_git.deleted_branches == []


def test_delete_branch_uses_graphite_when_commit_sha_is_none() -> None:
    """When Graphite has no cached SHA, Graphite delete is still used.

    This can happen for branches that were just tracked but haven't been
    synced yet. We still try Graphite since it's tracked.
    """
    repo_root = Path("/repo")

    fake_git = FakeGit(
        branch_heads={"feature-branch": "abc123"},
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite(
        branches={
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha=None,  # No cached SHA
            ),
        },
    )
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=FakeGitHub(),
    )
    manager.delete_branch(repo_root, "feature-branch")

    # Graphite delete was called (branch is tracked)
    assert fake_graphite.delete_branch_calls == [(repo_root, "feature-branch")]
    # Git delete was NOT called
    assert fake_git.deleted_branches == []


def test_delete_branch_uses_graphite_when_git_branch_head_is_none() -> None:
    """When git can't find branch head, Graphite delete is still used.

    This might happen for edge cases where the branch exists but
    we can't determine its SHA. Since it's tracked, try Graphite.
    """
    repo_root = Path("/repo")

    fake_git = FakeGit(
        branch_heads={},  # No branch head known
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite(
        branches={
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha="cached-sha-123",
            ),
        },
    )
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=FakeGitHub(),
    )
    manager.delete_branch(repo_root, "feature-branch")

    # Graphite delete was called (branch is tracked and can't compare SHAs)
    assert fake_graphite.delete_branch_calls == [(repo_root, "feature-branch")]
    # Git delete was NOT called
    assert fake_git.deleted_branches == []


def test_create_branch_tracks_with_graphite() -> None:
    """create_branch() creates git branch and tracks with Graphite.

    This ensures branches created via BranchManager are tracked in Graphite
    for proper stack visualization and PR enhancement.
    """
    repo_root = Path("/repo")

    fake_git = FakeGit(
        current_branches={repo_root: "main"},
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite()
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=FakeGitHub(),
    )
    manager.create_branch(repo_root, "feature-branch", "main")

    # Git operations were called
    # created_branches is list of (cwd, branch_name, start_point, force) tuples
    assert fake_git.created_branches == [(repo_root, "feature-branch", "main", False)]
    # checked_out_branches is list of (cwd, branch_name) tuples
    assert fake_git.checked_out_branches == [
        (repo_root, "feature-branch"),
        (repo_root, "main"),
    ]

    # Graphite tracking was called
    assert fake_graphite.track_branch_calls == [(repo_root, "feature-branch", "main")]


# --- PR lookup with GitHub fallback tests ---


def test_get_pr_for_branch_returns_from_graphite_cache() -> None:
    """When PR is in Graphite cache, returns with from_fallback=False."""
    repo_root = Path("/repo")

    fake_git = FakeGit()
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite(
        pr_info={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Feature branch",
                checks_passing=True,
                owner="owner",
                repo="repo",
            ),
        },
    )
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()
    fake_github = FakeGitHub()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=fake_github,
    )
    result = manager.get_pr_for_branch(repo_root, "feature-branch")

    assert result is not None
    assert result.number == 123
    assert result.state == "OPEN"
    assert result.is_draft is False
    assert result.from_fallback is False


def test_get_pr_for_branch_falls_back_to_github_when_not_in_cache() -> None:
    """When branch PR not in Graphite cache, falls back to GitHub API."""
    repo_root = Path("/repo")

    fake_git = FakeGit(
        remote_urls={(repo_root, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite(
        pr_info={},  # Branch not in Graphite cache
    )
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()
    fake_github = FakeGitHub(
        prs_by_branch={
            "feature-branch": PRDetails(
                number=456,
                url="https://github.com/owner/repo/pull/456",
                title="Feature branch PR",
                body="",
                state="OPEN",
                is_draft=True,
                base_ref_name="main",
                head_ref_name="feature-branch",
                is_cross_repository=False,
                mergeable="UNKNOWN",
                merge_state_status="UNKNOWN",
                owner="owner",
                repo="repo",
            ),
        },
    )

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=fake_github,
    )
    result = manager.get_pr_for_branch(repo_root, "feature-branch")

    assert result is not None
    assert result.number == 456
    assert result.state == "OPEN"
    assert result.is_draft is True
    assert result.from_fallback is True


def test_get_pr_for_branch_returns_none_when_not_found_anywhere() -> None:
    """When branch has no PR in either Graphite cache or GitHub, returns None."""
    repo_root = Path("/repo")

    fake_git = FakeGit(
        remote_urls={(repo_root, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite(
        pr_info={},
    )
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()
    fake_github = FakeGitHub()  # No PRs configured

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=fake_github,
    )
    result = manager.get_pr_for_branch(repo_root, "no-pr-branch")

    assert result is None
