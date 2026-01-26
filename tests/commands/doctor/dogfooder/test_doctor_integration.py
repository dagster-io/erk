"""Integration tests for doctor command with dogfooder features."""

from click.testing import CliRunner

from erk.cli.commands.doctor import doctor_cmd
from erk_shared.gateway.git.fake import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_doctor_shows_early_dogfooder_section_with_flag() -> None:
    """Test that doctor shows Early Dogfooder section when --dogfooder flag passed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create deprecated pyproject.toml config
        pyproject_path = env.cwd / "pyproject.toml"
        pyproject_path.write_text(
            """
[tool.dot-agent]
some_setting = true
""",
            encoding="utf-8",
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        # Early Dogfooder checks are now opt-in via --dogfooder flag
        result = runner.invoke(doctor_cmd, ["--dogfooder"], obj=ctx)

        # Should show Early Dogfooder section when flag is passed
        assert "Early Dogfooder" in result.output
        assert "deprecated" in result.output.lower()
        assert "[tool.erk]" in result.output


def test_doctor_hides_early_dogfooder_section_by_default() -> None:
    """Test that doctor hides Early Dogfooder section by default even with deprecated config."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create deprecated pyproject.toml config
        pyproject_path = env.cwd / "pyproject.toml"
        pyproject_path.write_text(
            """
[tool.dot-agent]
some_setting = true
""",
            encoding="utf-8",
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        # Without --dogfooder flag, section should not appear
        result = runner.invoke(doctor_cmd, [], obj=ctx)

        # Early Dogfooder section should NOT appear by default
        assert "Early Dogfooder" not in result.output
