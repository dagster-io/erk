"""Integration tests for CLI version checking behavior."""

from click.testing import CliRunner

from erk.cli.cli import cli


def test_version_warning_silences_error_outside_git_repo() -> None:
    """Regression test: version warning should not error outside git repos.

    Previously, RuntimeError from git.get_repository_root() was not caught,
    causing CLI commands to fail when run outside a git repository.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Not in a git repo - would trigger "not a git repository" error
        result = runner.invoke(cli, ["--help"])

        # Should succeed despite being outside a repo
        assert result.exit_code == 0
