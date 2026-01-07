"""Integration tests for CLI version checking behavior."""

from click.testing import CliRunner

from erk.cli.cli import cli


def test_version_warning_silences_error_outside_git_repo() -> None:
    """Regression test: version warning should not error outside git repos.

    Uses LBYL pattern: get_git_common_dir() returns None for non-git dirs,
    allowing early return before get_repository_root() would raise RuntimeError.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Not in a git repo - get_git_common_dir returns None, early return
        result = runner.invoke(cli, ["--help"])

        # Should succeed without warning
        assert result.exit_code == 0
        assert "Failed to check version" not in result.output
