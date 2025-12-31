"""Unit tests for repository discovery with GitHub identity extraction."""

from pathlib import Path

from erk.core.repo_discovery import RepoContext, discover_repo_or_sentinel, in_erk_repo
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit


def test_discover_repo_extracts_github_identity_https(tmp_path: Path):
    """Test that GitHub identity is extracted from HTTPS remote URL."""
    repo_root = tmp_path / "test-repo"
    erk_root = tmp_path / ".erk"

    # Configure FakeGit with a GitHub HTTPS remote
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main", is_root=True)]},
        git_common_dirs={repo_root: repo_root / ".git"},
        existing_paths={repo_root, repo_root / ".git"},
        remote_urls={(repo_root, "origin"): "https://github.com/dagster-io/erk.git"},
    )

    result = discover_repo_or_sentinel(repo_root, erk_root, git_ops)

    assert isinstance(result, RepoContext)
    assert result.github is not None
    assert result.github.owner == "dagster-io"
    assert result.github.repo == "erk"


def test_discover_repo_extracts_github_identity_ssh(tmp_path: Path):
    """Test that GitHub identity is extracted from SSH remote URL."""
    repo_root = tmp_path / "test-repo"
    erk_root = tmp_path / ".erk"

    # Configure FakeGit with a GitHub SSH remote
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main", is_root=True)]},
        git_common_dirs={repo_root: repo_root / ".git"},
        existing_paths={repo_root, repo_root / ".git"},
        remote_urls={(repo_root, "origin"): "git@github.com:dagster-io/erk.git"},
    )

    result = discover_repo_or_sentinel(repo_root, erk_root, git_ops)

    assert isinstance(result, RepoContext)
    assert result.github is not None
    assert result.github.owner == "dagster-io"
    assert result.github.repo == "erk"


def test_discover_repo_no_github_identity_non_github_remote(tmp_path: Path):
    """Test that GitHub identity is None for non-GitHub remotes."""
    repo_root = tmp_path / "test-repo"
    erk_root = tmp_path / ".erk"

    # Configure FakeGit with a non-GitHub remote
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main", is_root=True)]},
        git_common_dirs={repo_root: repo_root / ".git"},
        existing_paths={repo_root, repo_root / ".git"},
        remote_urls={(repo_root, "origin"): "https://gitlab.com/user/repo.git"},
    )

    result = discover_repo_or_sentinel(repo_root, erk_root, git_ops)

    assert isinstance(result, RepoContext)
    assert result.github is None


def test_discover_repo_no_github_identity_no_remote(tmp_path: Path):
    """Test that GitHub identity is None when no remote exists."""
    repo_root = tmp_path / "test-repo"
    erk_root = tmp_path / ".erk"

    # Configure FakeGit without any remote URL
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main", is_root=True)]},
        git_common_dirs={repo_root: repo_root / ".git"},
        existing_paths={repo_root, repo_root / ".git"},
        remote_urls={},  # No remote configured
    )

    result = discover_repo_or_sentinel(repo_root, erk_root, git_ops)

    assert isinstance(result, RepoContext)
    assert result.github is None


def test_discover_repo_in_worktree_returns_worktree_root(tmp_path: Path):
    """Test that discover_repo returns the worktree root, not main repo root.

    When running in a git worktree, RepoContext.root should be the worktree
    directory (where git commands should run), not the main repository.
    RepoContext.main_repo_root should still point to the main repo for
    consistent metadata paths and operations that need the root worktree.
    """
    # Setup: main repo at /code/erk, worktree at /.erk/repos/erk/worktrees/feature
    main_repo = tmp_path / "code" / "erk"
    worktree_path = tmp_path / ".erk" / "repos" / "erk" / "worktrees" / "feature"
    erk_root = tmp_path / ".erk"

    # Configure FakeGit:
    # - git_common_dir from worktree points to main repo's .git
    # - repository_root from worktree returns worktree path (like --show-toplevel)
    git_ops = FakeGit(
        worktrees={
            main_repo: [
                WorktreeInfo(path=main_repo, branch="main", is_root=True),
                WorktreeInfo(path=worktree_path, branch="feature", is_root=False),
            ]
        },
        git_common_dirs={worktree_path: main_repo / ".git"},
        repository_roots={worktree_path: worktree_path},  # --show-toplevel returns worktree
        existing_paths={worktree_path, main_repo, main_repo / ".git"},
        remote_urls={(main_repo, "origin"): "https://github.com/dagster-io/erk.git"},
    )

    # Act: discover repo from worktree
    result = discover_repo_or_sentinel(worktree_path, erk_root, git_ops)

    # Assert
    assert isinstance(result, RepoContext)
    # root should be the worktree (where git commands run)
    assert result.root == worktree_path
    # main_repo_root should point to the main repository
    assert result.main_repo_root == main_repo
    # repo_name should be from main repo for consistent metadata paths
    assert result.repo_name == "erk"


def test_discover_repo_in_main_repo_returns_main_repo_root(tmp_path: Path):
    """Test that discover_repo returns main repo root when in main repo.

    When running in the main repository (not a worktree), both root and
    main_repo_root should point to the same directory.
    """
    main_repo = tmp_path / "code" / "erk"
    erk_root = tmp_path / ".erk"

    git_ops = FakeGit(
        worktrees={main_repo: [WorktreeInfo(path=main_repo, branch="main", is_root=True)]},
        git_common_dirs={main_repo: main_repo / ".git"},
        repository_roots={main_repo: main_repo},
        existing_paths={main_repo, main_repo / ".git"},
        remote_urls={(main_repo, "origin"): "https://github.com/dagster-io/erk.git"},
    )

    result = discover_repo_or_sentinel(main_repo, erk_root, git_ops)

    assert isinstance(result, RepoContext)
    assert result.root == main_repo
    # In main repo, main_repo_root equals root
    assert result.main_repo_root == main_repo
    assert result.repo_name == "erk"


def test_in_erk_repo_returns_true_for_erk_repo(tmp_path: Path) -> None:
    """Test that in_erk_repo returns True when packages/erk-shared exists."""
    dev_indicator = tmp_path / "packages" / "erk-shared"
    dev_indicator.mkdir(parents=True)

    assert in_erk_repo(tmp_path) is True


def test_in_erk_repo_returns_false_for_regular_project(tmp_path: Path) -> None:
    """Test that in_erk_repo returns False for a regular project."""
    assert in_erk_repo(tmp_path) is False
