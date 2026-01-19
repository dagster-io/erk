"""Tests for render_land_execution_script()."""

from pathlib import Path

from erk.cli.commands.land_cmd import render_land_execution_script


def test_render_land_execution_script_uses_shell_variables_for_pr_and_branch() -> None:
    """The script uses $PR_NUMBER and $BRANCH from positional arguments."""
    script = render_land_execution_script(
        pr_number=123,
        branch="feature-branch",
        worktree_path=None,
        is_current_branch=False,
        target_child_branch=None,
        objective_number=None,
        use_graphite=False,
        pull_flag=True,
        no_delete=False,
        target_path=Path("/repo"),
    )

    # Should contain shell variable definitions
    assert 'PR_NUMBER="${1:?Error: PR number required}"' in script
    assert 'BRANCH="${2:?Error: Branch name required}"' in script

    # Should use shell variables in the command, not hardcoded values
    assert '--pr-number="$PR_NUMBER"' in script
    assert '--branch="$BRANCH"' in script

    # Should NOT contain hardcoded values
    assert "--pr-number=123" not in script
    assert "--branch=feature-branch" not in script


def test_render_land_execution_script_includes_usage_comment() -> None:
    """The script includes a usage comment."""
    script = render_land_execution_script(
        pr_number=456,
        branch="my-branch",
        worktree_path=None,
        is_current_branch=False,
        target_child_branch=None,
        objective_number=None,
        use_graphite=False,
        pull_flag=True,
        no_delete=False,
        target_path=Path("/repo"),
    )

    assert "# Usage: source land.sh <pr_number> <branch>" in script


def test_render_land_execution_script_includes_optional_flags() -> None:
    """Optional flags are still hardcoded (not parameterized)."""
    script = render_land_execution_script(
        pr_number=123,
        branch="feature-branch",
        worktree_path=Path("/worktrees/feature"),
        is_current_branch=True,
        target_child_branch="child-branch",
        objective_number=42,
        use_graphite=True,
        pull_flag=False,
        no_delete=True,
        target_path=Path("/repo"),
    )

    # Optional flags should be hardcoded
    assert "--worktree-path=/worktrees/feature" in script
    assert "--is-current-branch" in script
    assert "--target-child=child-branch" in script
    assert "--objective-number=42" in script
    assert "--use-graphite" in script
    assert "--no-pull" in script
    assert "--no-delete" in script


def test_render_land_execution_script_without_optional_flags() -> None:
    """Script omits optional flags when not needed."""
    script = render_land_execution_script(
        pr_number=123,
        branch="feature-branch",
        worktree_path=None,
        is_current_branch=False,
        target_child_branch=None,
        objective_number=None,
        use_graphite=False,
        pull_flag=True,  # True means omit --no-pull
        no_delete=False,
        target_path=Path("/repo"),
    )

    assert "--worktree-path" not in script
    assert "--is-current-branch" not in script
    assert "--target-child" not in script
    assert "--objective-number" not in script
    assert "--use-graphite" not in script
    assert "--no-pull" not in script
    assert "--no-delete" not in script


def test_render_land_execution_script_includes_cd_command() -> None:
    """Script includes cd command with target path."""
    script = render_land_execution_script(
        pr_number=123,
        branch="feature-branch",
        worktree_path=None,
        is_current_branch=False,
        target_child_branch=None,
        objective_number=None,
        use_graphite=False,
        pull_flag=True,
        no_delete=False,
        target_path=Path("/path/to/target"),
    )

    assert "cd /path/to/target" in script


def test_render_land_execution_script_has_header_comment() -> None:
    """Script starts with header comment."""
    script = render_land_execution_script(
        pr_number=123,
        branch="feature-branch",
        worktree_path=None,
        is_current_branch=False,
        target_child_branch=None,
        objective_number=None,
        use_graphite=False,
        pull_flag=True,
        no_delete=False,
        target_path=Path("/repo"),
    )

    assert script.startswith("# erk land deferred execution\n")
