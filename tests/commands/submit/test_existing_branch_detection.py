"""Tests for existing branch detection and reuse in submit command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import (
    _find_existing_branches_for_issue,
    submit_cmd,
)
from erk.core.context import context_for_test
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_find_existing_branches_detects_matching_pattern(tmp_path: Path) -> None:
    """Test _find_existing_branches_for_issue finds P{issue}-* branches."""
    from erk_shared.gateway.git.fake import FakeGit

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        local_branches={
            repo_root: [
                "main",
                "P123-feature-01-23-0909",
                "P123-feature-01-23-0910",
                "P456-other-01-23-0909",
                "unrelated-branch",
            ]
        },
    )

    ctx = context_for_test(cwd=repo_root, git=fake_git)

    result = _find_existing_branches_for_issue(ctx, repo_root, 123)

    assert result == ["P123-feature-01-23-0909", "P123-feature-01-23-0910"]


def test_find_existing_branches_returns_empty_when_none_exist(tmp_path: Path) -> None:
    """Test _find_existing_branches_for_issue returns empty list when no matches."""
    from erk_shared.gateway.git.fake import FakeGit

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        local_branches={repo_root: ["main", "other-branch"]},
    )

    ctx = context_for_test(cwd=repo_root, git=fake_git)

    result = _find_existing_branches_for_issue(ctx, repo_root, 123)

    assert result == []


def test_submit_uses_existing_branch_when_user_confirms(tmp_path: Path) -> None:
    """Test submit reuses existing local branch when user confirms."""
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, fake_graphite, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
            "local_branches": {repo_root: ["main", "P123-implement-feature-x-01-23-0909"]},
        },
        graphite_kwargs={
            "branches": {
                "main": BranchMetadata.trunk("main"),
            },
        },
        use_graphite=True,
        # User confirms "use existing branch"
        confirm_responses=[True],
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Found existing local branch(es) for this issue" in result.output
    assert "P123-implement-feature-x-01-23-0909" in result.output
    assert "Using existing local branch" in result.output

    # Verify NO new branch was created (should reuse existing)
    assert len(fake_git.created_branches) == 0

    # Verify existing branch was tracked in Graphite
    assert len(fake_graphite.track_branch_calls) == 1
    tracked_repo, tracked_branch, parent = fake_graphite.track_branch_calls[0]
    assert tracked_branch == "P123-implement-feature-x-01-23-0909"
    assert parent == "main"


def test_submit_deletes_existing_and_creates_new_when_user_declines_reuse(
    tmp_path: Path,
) -> None:
    """Test submit deletes existing branches and creates new when user chooses."""
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, fake_graphite, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
            "local_branches": {repo_root: ["main", "P123-implement-feature-x-01-23-0909"]},
        },
        graphite_kwargs={
            "branches": {
                "main": BranchMetadata.trunk("main"),
            },
        },
        use_graphite=True,
        # User declines "use existing", then confirms "delete and create new"
        confirm_responses=[False, True],
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Found existing local branch(es) for this issue" in result.output
    assert "Deleted branch: P123-implement-feature-x-01-23-0909" in result.output

    # Verify old branch was deleted
    assert len(fake_git._deleted_branches) == 1
    assert fake_git._deleted_branches[0] == "P123-implement-feature-x-01-23-0909"

    # Verify new branch was created with current timestamp
    # (tuple is cwd, branch_name, start_point, force)
    assert len(fake_git.created_branches) == 1
    _, created_branch, _, _ = fake_git.created_branches[0]
    assert created_branch == "P123-implement-feature-x-01-15-1430"


def test_submit_aborts_when_user_declines_both_options(tmp_path: Path) -> None:
    """Test submit aborts when user declines both reuse and delete options."""
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, _, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
            "local_branches": {repo_root: ["main", "P123-implement-feature-x-01-23-0909"]},
        },
        # User declines "use existing", then declines "delete and create new"
        confirm_responses=[False, False],
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "Aborted." in result.output

    # Verify no branches were created or deleted
    assert len(fake_git.created_branches) == 0
    assert len(fake_git._deleted_branches) == 0


def test_submit_uses_newest_existing_branch_when_multiple_exist(tmp_path: Path) -> None:
    """Test submit offers newest existing branch when multiple exist."""
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, fake_graphite, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
            "local_branches": {
                repo_root: [
                    "main",
                    "P123-implement-feature-x-01-23-0900",  # Older
                    "P123-implement-feature-x-01-23-0905",  # Middle
                    "P123-implement-feature-x-01-23-0910",  # Newest
                ]
            },
        },
        graphite_kwargs={
            "branches": {
                "main": BranchMetadata.trunk("main"),
            },
        },
        use_graphite=True,
        # User confirms "use existing branch" (which will be the newest)
        confirm_responses=[True],
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify all three branches are shown
    assert "P123-implement-feature-x-01-23-0900" in result.output
    assert "P123-implement-feature-x-01-23-0905" in result.output
    assert "P123-implement-feature-x-01-23-0910" in result.output

    # Verify the newest branch is used (shown in confirmation prompt)
    # The prompt mentions the newest branch which is 0910
    assert "Using existing local branch" in result.output

    # Verify existing branch was tracked
    assert len(fake_graphite.track_branch_calls) == 1
    _, tracked_branch, _ = fake_graphite.track_branch_calls[0]
    assert tracked_branch == "P123-implement-feature-x-01-23-0910"


def test_submit_proceeds_normally_when_no_existing_branches(tmp_path: Path) -> None:
    """Test submit creates new branch when no existing branches match."""
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, _, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
            "local_branches": {repo_root: ["main"]},  # No P123-* branches
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    # No existing branch prompt should appear
    assert "Found existing local branch(es)" not in result.output
    assert "issue(s) submitted successfully!" in result.output

    # Verify new branch was created
    # (tuple is cwd, branch_name, start_point, force)
    assert len(fake_git.created_branches) == 1
    _, created_branch, _, _ = fake_git.created_branches[0]
    assert created_branch == "P123-implement-feature-x-01-15-1430"


def test_submit_deletes_multiple_existing_branches(tmp_path: Path) -> None:
    """Test submit deletes all existing branches when user chooses delete."""
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, _, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
            "local_branches": {
                repo_root: [
                    "main",
                    "P123-implement-feature-x-01-23-0900",
                    "P123-implement-feature-x-01-23-0905",
                ]
            },
        },
        # User declines reuse, confirms delete
        confirm_responses=[False, True],
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Deleted branch: P123-implement-feature-x-01-23-0900" in result.output
    assert "Deleted branch: P123-implement-feature-x-01-23-0905" in result.output

    # Verify both old branches were deleted
    assert len(fake_git._deleted_branches) == 2
    assert "P123-implement-feature-x-01-23-0900" in fake_git._deleted_branches
    assert "P123-implement-feature-x-01-23-0905" in fake_git._deleted_branches

    # Verify new branch was created
    assert len(fake_git.created_branches) == 1


def test_submit_force_deletes_existing_branches_and_creates_new(tmp_path: Path) -> None:
    """Test --force deletes existing branches without prompting."""
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, _, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
            "local_branches": {
                repo_root: [
                    "main",
                    "P123-implement-feature-x-01-23-0900",
                    "P123-implement-feature-x-01-23-0905",
                ]
            },
        },
        # NO confirm_responses - force mode should NOT prompt
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "-f"], obj=ctx)

    assert result.exit_code == 0, result.output
    # Should show force mode message
    assert "Deleting 2 existing branch(es) (--force mode)" in result.output
    # Should not show the interactive prompt message
    assert "Use existing branch" not in result.output

    # Verify both old branches were deleted
    assert len(fake_git._deleted_branches) == 2
    assert "P123-implement-feature-x-01-23-0900" in fake_git._deleted_branches
    assert "P123-implement-feature-x-01-23-0905" in fake_git._deleted_branches

    # Verify new branch was created
    assert len(fake_git.created_branches) == 1
    _, created_branch, _, _ = fake_git.created_branches[0]
    assert created_branch == "P123-implement-feature-x-01-15-1430"


def test_submit_force_creates_new_branch_when_none_exist(tmp_path: Path) -> None:
    """Test --force creates new branch normally when no existing branches."""
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, _, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
            "local_branches": {repo_root: ["main"]},  # No P123-* branches
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "-f"], obj=ctx)

    assert result.exit_code == 0, result.output
    # Should not show existing branch prompts
    assert "Found existing local branch(es)" not in result.output
    assert "Deleting" not in result.output
    assert "issue(s) submitted successfully!" in result.output

    # Verify new branch was created normally
    assert len(fake_git.created_branches) == 1
    _, created_branch, _, _ = fake_git.created_branches[0]
    assert created_branch == "P123-implement-feature-x-01-15-1430"
