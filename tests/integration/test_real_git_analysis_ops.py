"""Integration tests for RealGitAnalysisOps.

Tests verify real git analysis operations against actual git repositories.
"""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.analysis_ops.real import RealGitAnalysisOps
from tests.integration.conftest import init_git_repo


def test_get_diff_to_branch_excludes_diverged_master_changes(tmp_path: Path) -> None:
    """Three-dot diff shows only feature branch changes, not diverged base changes.

    When a feature branch diverges from main (main has new commits the branch
    doesn't have), get_diff_to_branch should only show the feature branch's
    own changes. With two-dot diff this would include the inverse of main's
    new commits as spurious deletions.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Create feature branch from initial commit
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True)

    # Add a file on the feature branch
    feature_file = repo / "feature.txt"
    feature_file.write_text("feature work\n")
    subprocess.run(["git", "add", "feature.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add feature file"], cwd=repo, check=True)

    # Go back to main and add a DIFFERENT file (diverge)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True)
    main_file = repo / "main-only.txt"
    main_file.write_text("main work\n")
    subprocess.run(["git", "add", "main-only.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add main-only file"], cwd=repo, check=True)

    # Switch back to feature branch
    subprocess.run(["git", "checkout", "feature"], cwd=repo, check=True)

    # Act
    ops = RealGitAnalysisOps()
    diff = ops.get_diff_to_branch(repo, "main")

    # Assert: diff should contain the feature branch's file
    assert "feature.txt" in diff

    # Assert: diff should NOT contain main-only.txt
    # With two-dot diff (branch..HEAD), main-only.txt would appear as a deletion
    # because two-dot compares tree states directly. Three-dot (branch...HEAD)
    # diffs from merge-base, so main's diverged commits are excluded.
    assert "main-only.txt" not in diff
