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
        objective_number=None,
        use_graphite=False,
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
    """The script includes a usage comment with flags notation."""
    script = render_land_execution_script(
        pr_number=456,
        branch="my-branch",
        worktree_path=None,
        is_current_branch=False,
        objective_number=None,
        use_graphite=False,
        target_path=Path("/repo"),
    )

    assert "# Usage: source land.sh <pr_number> <branch> [flags...]" in script


def test_render_land_execution_script_includes_shift_and_passthrough() -> None:
    """Script shifts positional args and passes remaining flags via $@."""
    script = render_land_execution_script(
        pr_number=123,
        branch="feature-branch",
        worktree_path=None,
        is_current_branch=False,
        objective_number=None,
        use_graphite=False,
        target_path=Path("/repo"),
    )

    # Should shift past PR number and branch
    assert "shift 2" in script

    # Should pass remaining flags to land-execute
    assert '"$@"' in script


def test_render_land_execution_script_bakes_in_static_flags() -> None:
    """Static flags are baked into the script at generation time."""
    script = render_land_execution_script(
        pr_number=123,
        branch="feature-branch",
        worktree_path=Path("/worktrees/feature"),
        is_current_branch=True,
        objective_number=42,
        use_graphite=True,
        target_path=Path("/repo"),
    )

    # These should be hardcoded in the script
    assert "--worktree-path=/worktrees/feature" in script
    assert "--is-current-branch" in script
    assert "--objective-number=42" in script
    assert "--use-graphite" in script


def test_render_land_execution_script_without_static_flags() -> None:
    """Script omits static flags when not needed."""
    script = render_land_execution_script(
        pr_number=123,
        branch="feature-branch",
        worktree_path=None,
        is_current_branch=False,
        objective_number=None,
        use_graphite=False,
        target_path=Path("/repo"),
    )

    assert "--worktree-path" not in script
    assert "--is-current-branch" not in script
    assert "--objective-number" not in script
    assert "--use-graphite" not in script


def test_render_land_execution_script_does_not_bake_user_flags() -> None:
    """User-controllable flags (--up, --no-pull, --no-delete) are NOT baked in.

    These flags are passed through via "$@" at execution time, not baked
    into the script at generation time.
    """
    script = render_land_execution_script(
        pr_number=123,
        branch="feature-branch",
        worktree_path=None,
        is_current_branch=False,
        objective_number=None,
        use_graphite=False,
        target_path=Path("/repo"),
    )

    # User flags should NOT be hardcoded - they come from "$@"
    assert "--no-pull" not in script
    assert "--no-delete" not in script
    assert "--up" not in script
    assert "--target-child" not in script


def test_render_land_execution_script_includes_cd_command() -> None:
    """Script includes cd command with target path."""
    script = render_land_execution_script(
        pr_number=123,
        branch="feature-branch",
        worktree_path=None,
        is_current_branch=False,
        objective_number=None,
        use_graphite=False,
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
        objective_number=None,
        use_graphite=False,
        target_path=Path("/repo"),
    )

    assert script.startswith("# erk land deferred execution\n")
