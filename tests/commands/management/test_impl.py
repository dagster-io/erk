from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.shell_integration import hidden_shell_cmd
from erk.cli.shell_utils import render_cd_script
from erk.core.context import context_for_test
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation, GlobalConfig
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.naming import WORKTREE_DATE_SUFFIX_FORMAT
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _get_current_date_suffix() -> str:
    """Get the current date suffix for plan-derived worktrees."""
    return datetime.now().strftime(WORKTREE_DATE_SUFFIX_FORMAT)


def test_create_with_plan_file() -> None:
    """Test creating a worktree from a plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a plan file in root worktree
        plan_file = env.root_worktree / "Add_Auth_Feature.md"
        plan_content = "# Auth Feature Plan\n\n- Add login\n- Add signup\n"
        plan_file.write_text(plan_content, encoding="utf-8")

        # Configure FakeGit with root worktree only
        git_ops = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create test context using env.build_context() helper
        test_ctx = env.build_context(git=git_ops)

        # Run erk create with --from-plan-file
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", "Add_Auth_Feature.md", "--no-post"],
            obj=test_ctx,
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # --from-plan-file flag adds date suffix in format -YY-MM-DD-HHMM
        date_suffix = _get_current_date_suffix()
        expected_name = f"add-auth-feature-{date_suffix}"

        # Verify worktree was created with sanitized name and date suffix
        worktree_path = env.erk_root / "repos" / "repo" / "worktrees" / expected_name
        assert worktree_path.exists()
        assert worktree_path.is_dir()

        # Verify impl folder was created with plan.md
        impl_folder = worktree_path / ".impl"
        assert impl_folder.exists()
        assert (impl_folder / "plan.md").exists()
        assert (impl_folder / "plan.md").read_text(encoding="utf-8") == plan_content

        # Verify original plan file was moved (not copied)
        assert not plan_file.exists()

        # Verify .env was created
        assert (worktree_path / ".env").exists()


def test_create_with_plan_name_sanitization() -> None:
    """Test that plan filename gets properly sanitized for worktree name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a plan file with underscores and mixed case
        plan_file = env.root_worktree / "MY_COOL_Plan_File.md"
        plan_file.write_text("# Cool Plan\n", encoding="utf-8")

        # Configure FakeGit with root worktree only
        git_ops = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create test context using env.build_context() helper
        test_ctx = env.build_context(git=git_ops)

        # Run erk create with --from-plan-file
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", "MY_COOL_Plan_File.md", "--no-post"],
            obj=test_ctx,
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # --from-plan-file flag adds date suffix in format -YY-MM-DD-HHMM
        date_suffix = _get_current_date_suffix()
        expected_name = f"my-cool-file-{date_suffix}"

        # Verify worktree name is lowercase with hyphens, "plan" removed, and date suffix added
        worktree_path = env.erk_root / "repos" / "repo" / "worktrees" / expected_name
        assert worktree_path.exists()

        # Verify impl folder was created
        assert (worktree_path / ".impl" / "plan.md").exists()
        assert not plan_file.exists()


def test_create_with_both_name_and_plan_file_fails() -> None:
    """Test that providing both NAME and --from-plan-file is an error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a plan file
        plan_file = env.root_worktree / "plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        # Configure FakeGit with root worktree only
        git_ops = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with erk_root
        global_config = GlobalConfig.test(
            env.erk_root, use_graphite=False, shell_setup_complete=False
        )
        global_config_ops = FakeErkInstallation(config=global_config)

        # Create test context
        test_ctx = context_for_test(
            git=git_ops,
            erk_installation=global_config_ops,
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.root_worktree,
        )

        # Run erk create with both NAME and --from-plan-file
        result = runner.invoke(
            cli, ["wt", "create", "myname", "--from-plan-file", "plan.md"], obj=test_ctx
        )

        # Should fail
        assert result.exit_code != 0
        assert "Cannot specify both NAME and --from-plan-file" in result.output


def test_create_rejects_reserved_name_root() -> None:
    """Test that 'root' is rejected as a reserved worktree name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Configure FakeGit with root worktree only
        git_ops = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with erk_root
        global_config = GlobalConfig.test(
            env.erk_root, use_graphite=False, shell_setup_complete=False
        )
        global_config_ops = FakeErkInstallation(config=global_config)

        # Create test context
        test_ctx = context_for_test(
            git=git_ops,
            erk_installation=global_config_ops,
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.root_worktree,
        )

        # Try to create a worktree named "root"
        result = runner.invoke(cli, ["wt", "create", "root", "--no-post"], obj=test_ctx)

        # Should fail with reserved name error
        assert result.exit_code != 0
        assert "root" in result.output.lower() and "reserved" in result.output.lower(), (
            f"Expected error about 'root' being reserved, got: {result.output}"
        )

        # Verify worktree was not created
        worktree_path = env.erk_root / "repos" / "repo" / "worktrees" / "root"
        assert not worktree_path.exists()


def test_create_rejects_reserved_name_root_case_insensitive() -> None:
    """Test that 'ROOT', 'Root', etc. are also rejected (case-insensitive)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Configure FakeGit with root worktree only
        git_ops = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with erk_root
        global_config = GlobalConfig.test(
            env.erk_root, use_graphite=False, shell_setup_complete=False
        )
        global_config_ops = FakeErkInstallation(config=global_config)

        # Create test context
        test_ctx = context_for_test(
            git=git_ops,
            erk_installation=global_config_ops,
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.root_worktree,
        )

        # Test various cases of "root"
        for name_variant in ["ROOT", "Root", "RoOt"]:
            result = runner.invoke(cli, ["wt", "create", name_variant, "--no-post"], obj=test_ctx)

            # Should fail with reserved name error
            assert result.exit_code != 0, f"Expected failure for name '{name_variant}'"
            error_msg = (
                f"Expected error about 'root' being reserved for '{name_variant}', "
                f"got: {result.output}"
            )
            assert "reserved" in result.output.lower(), error_msg


def test_create_rejects_main_as_worktree_name() -> None:
    """Test that 'main' is rejected as a worktree name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Configure FakeGit with root worktree only
        git_ops = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
            trunk_branches={env.root_worktree: "main"},
        )

        # Create global config with erk_root
        global_config = GlobalConfig.test(
            env.erk_root, use_graphite=False, shell_setup_complete=False
        )
        global_config_ops = FakeErkInstallation(config=global_config)

        # Create test context
        test_ctx = context_for_test(
            git=git_ops,
            erk_installation=global_config_ops,
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.root_worktree,
        )

        # Try to create a worktree named "main"
        result = runner.invoke(cli, ["wt", "create", "main", "--no-post"], obj=test_ctx)

        # Should fail with error suggesting to use root
        assert result.exit_code != 0
        assert "main" in result.output.lower()
        assert "erk br co root" in result.output

        # Verify worktree was not created
        worktree_path = env.erk_root / "repos" / "repo" / "worktrees" / "main"
        assert not worktree_path.exists()


def test_create_rejects_master_as_worktree_name() -> None:
    """Test that 'master' is rejected as a worktree name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Configure FakeGit with root worktree only
        # Set trunk_branches to "master" so it gets rejected
        git_ops = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="master", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "master"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "master"},
            trunk_branches={env.root_worktree: "master"},
        )

        # Create global config with erk_root
        global_config = GlobalConfig.test(
            env.erk_root, use_graphite=False, shell_setup_complete=False
        )
        global_config_ops = FakeErkInstallation(config=global_config)

        # Create test context
        test_ctx = context_for_test(
            git=git_ops,
            erk_installation=global_config_ops,
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.root_worktree,
        )

        # Try to create a worktree named "master"
        result = runner.invoke(cli, ["wt", "create", "master", "--no-post"], obj=test_ctx)

        # Should fail with error suggesting to use root
        assert result.exit_code != 0
        assert "master" in result.output.lower()
        assert "erk br co root" in result.output

        # Verify worktree was not created
        worktree_path = env.erk_root / "repos" / "repo" / "worktrees" / "master"
        assert not worktree_path.exists()


def test_render_cd_script() -> None:
    """Test that render_cd_script generates proper shell code."""
    worktree_path = Path("/example/erks/repo/my-worktree")
    script = render_cd_script(
        worktree_path,
        comment="erk create - cd to new worktree",
        success_message="✓ Went to new worktree.",
    )

    assert "# erk create - cd to new worktree" in script
    assert f"cd '{worktree_path}'" in script
    assert 'echo "✓ Went to new worktree."' in script


def test_create_with_script_flag() -> None:
    """Test that --script flag outputs cd script instead of regular messages."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Configure FakeGit with root worktree only
        git_ops = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create test context using env.build_context() helper
        test_ctx = env.build_context(git=git_ops)

        # Run erk create with --script flag
        result = runner.invoke(
            cli, ["wt", "create", "test-worktree", "--no-post", "--script"], obj=test_ctx
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify worktree was created
        worktree_path = env.erk_root / "repos" / "repo" / "worktrees" / "test-worktree"
        assert worktree_path.exists()

        # Output should be a temp file path
        script_path = Path(result.output.strip())
        assert script_path.exists()
        assert script_path.name.startswith("erk-create-")
        assert script_path.name.endswith(".sh")

        # Verify script content contains activation keywords (not simple cd)
        # Since worktree_path != repo_root, render_navigation_script uses full activation
        script_content = script_path.read_text(encoding="utf-8")

        # Check for activation script indicators (uv sync, venv activation, .env loading)
        assert "uv sync" in script_content or "# cd to new worktree" in script_content
        assert str(worktree_path) in script_content

        # Cleanup
        script_path.unlink(missing_ok=True)


def test_hidden_shell_cmd_checkout_passthrough_on_help() -> None:
    """Shell integration command signals passthrough for help.

    Note: The 'create' top-level alias was removed. Now testing the 'checkout'
    command help passthrough behavior instead, which is still active in shell
    integration.
    """
    runner = CliRunner()
    result = runner.invoke(hidden_shell_cmd, ["checkout", "--help"])

    assert result.exit_code == 0
    assert result.output.strip() == "__ERK_PASSTHROUGH__"


def test_hidden_shell_cmd_checkout_error_no_passthrough(tmp_path: Path) -> None:
    """Shell integration command does NOT passthrough on errors.

    When a shell-integrated command fails, we don't passthrough because that would
    run the command again WITHOUT --script, showing misleading errors instead of
    the actual failure reason.

    Note: The 'create' top-level alias was removed. Now testing the 'checkout'
    command error behavior instead, which is still active in shell integration.
    """
    runner = CliRunner()

    # Mock subprocess.run to simulate command failure without spawning real subprocess
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""

    with patch("erk.cli.shell_integration.handler.subprocess.run", return_value=mock_result):
        # Try to checkout - subprocess mock returns failure
        result = runner.invoke(hidden_shell_cmd, ["checkout", "test-branch"])

        # Should fail with non-zero exit code but NOT passthrough
        # Passthrough would run command again without --script, showing wrong error
        assert result.exit_code != 0
        # No passthrough marker - error is handled directly by shell integration
        assert "__ERK_PASSTHROUGH__" not in result.output
