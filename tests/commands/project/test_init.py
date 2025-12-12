"""Tests for the project init command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_project_init_creates_project_toml() -> None:
    """Test that project init creates .erk/project.toml."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up a project subdirectory
        project_dir = env.cwd / "python_modules" / "my-project"
        project_dir.mkdir(parents=True)

        git_ops = FakeGit(git_common_dirs={project_dir: env.git_dir})

        test_ctx = env.build_context(
            git=git_ops,
            cwd=project_dir,  # We're in the project subdirectory
        )

        result = runner.invoke(cli, ["project", "init"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Initialized project" in result.output
        assert "my-project" in result.output

        # Verify file was created
        project_toml = project_dir / ".erk" / "project.toml"
        assert project_toml.exists()
        content = project_toml.read_text(encoding="utf-8")
        assert "[env]" in content
        assert "[post_create]" in content


def test_project_init_fails_if_already_exists() -> None:
    """Test that project init fails if project.toml already exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up a project subdirectory with existing project.toml
        project_dir = env.cwd / "python_modules" / "my-project"
        erk_dir = project_dir / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "project.toml").write_text("# existing", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={project_dir: env.git_dir})

        test_ctx = env.build_context(
            git=git_ops,
            cwd=project_dir,
        )

        result = runner.invoke(cli, ["project", "init"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already initialized" in result.output


def test_project_init_fails_at_repo_root() -> None:
    """Test that project init fails when run at repo root."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(
            git=git_ops,
            cwd=env.cwd,  # At repo root
        )

        result = runner.invoke(cli, ["project", "init"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Cannot initialize project at repository root" in result.output
