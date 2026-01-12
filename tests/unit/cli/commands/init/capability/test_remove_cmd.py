"""Tests for erk init capability remove command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_capability_remove_removes_capability() -> None:
    """Test that remove command removes an installed capability."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Pre-create the capability directories and files
        docs_dir = env.cwd / "docs" / "learned"
        docs_dir.mkdir(parents=True)
        (docs_dir / "README.md").write_text("# Test", encoding="utf-8")
        skill_dir = env.cwd / ".claude" / "skills" / "learned-docs"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

        # Verify capability is installed
        assert (env.cwd / "docs" / "learned").exists()

        result = runner.invoke(cli, ["init", "capability", "remove", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "learned-docs" in result.output
        assert "Removed" in result.output

        # Verify capability was removed
        assert not (env.cwd / "docs" / "learned").exists()
        assert not (env.cwd / ".claude" / "skills" / "learned-docs").exists()


def test_capability_remove_not_installed() -> None:
    """Test that removing a not-installed capability shows warning."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "remove", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Not installed" in result.output


def test_capability_remove_unknown_name_fails() -> None:
    """Test that remove with unknown capability name fails with helpful error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "remove", "nonexistent"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Unknown capability: nonexistent" in result.output
        assert "Available capabilities:" in result.output


def test_capability_remove_required_capability_blocked() -> None:
    """Test that removing a required capability is blocked."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "remove", "erk-hooks"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Cannot remove required capability" in result.output


def test_capability_remove_multiple() -> None:
    """Test that remove command can remove multiple capabilities at once."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Pre-create learned-docs capability
        docs_dir = env.cwd / "docs" / "learned"
        docs_dir.mkdir(parents=True)
        skill_dir = env.cwd / ".claude" / "skills" / "learned-docs"
        skill_dir.mkdir(parents=True)

        # Pre-create devrun-agent capability
        agent_file = env.cwd / ".claude" / "agents" / "devrun.md"
        agent_file.parent.mkdir(parents=True, exist_ok=True)
        agent_file.write_text("# Devrun agent", encoding="utf-8")

        result = runner.invoke(
            cli, ["init", "capability", "remove", "learned-docs", "devrun-agent"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "learned-docs" in result.output
        assert "devrun-agent" in result.output

        # Verify both were removed
        assert not (env.cwd / "docs" / "learned").exists()
        assert not (env.cwd / ".claude" / "agents" / "devrun.md").exists()


def test_capability_remove_requires_repo() -> None:
    """Test that remove command fails outside a git repository for project capability."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # FakeGit returns None for git_common_dir when not in a repo
        git_ops = FakeGit(git_common_dirs={})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "remove", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Not in a git repository" in result.output


def test_capability_remove_requires_at_least_one_name() -> None:
    """Test that remove command requires at least one capability name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "remove"], obj=test_ctx)

        # Click should fail because NAMES is required
        assert result.exit_code == 2
        assert "Missing argument" in result.output or "NAMES" in result.output
