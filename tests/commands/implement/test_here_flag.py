"""Tests for --here flag in implement command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.git.fake import FakeGit
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


class TestHereAndForceMutualExclusion:
    """Tests for --here and --force mutual exclusivity."""

    def test_here_and_force_are_mutually_exclusive(self) -> None:
        """Test that --here and --force cannot be used together."""
        plan_issue = create_sample_plan_issue()

        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                local_branches={env.cwd: ["main"]},
                default_branches={env.cwd: "main"},
            )
            store, _ = create_plan_store_with_plans({"42": plan_issue})
            ctx = build_workspace_test_context(env, git=git, plan_store=store)

            result = runner.invoke(implement, ["#42", "--here", "--force", "--dry-run"], obj=ctx)

            assert result.exit_code != 0
            assert "--here and --force are mutually exclusive" in result.output


class TestHereWithDryRun:
    """Tests for --here flag with --dry-run."""

    def test_here_dry_run_from_issue_shows_current_directory(self) -> None:
        """Test --here --dry-run shows current directory for issue mode."""
        plan_issue = create_sample_plan_issue()

        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                local_branches={env.cwd: ["main"]},
                default_branches={env.cwd: "main"},
            )
            store, _ = create_plan_store_with_plans({"42": plan_issue})
            ctx = build_workspace_test_context(env, git=git, plan_store=store)

            result = runner.invoke(implement, ["#42", "--here", "--dry-run"], obj=ctx)

            assert result.exit_code == 0
            assert "Dry-run mode" in result.output
            assert "Would run in current directory" in result.output
            assert "/erk:system:impl-execute" in result.output

            # Verify no worktree was created
            assert len(git.added_worktrees) == 0

    def test_here_dry_run_from_file_shows_current_directory(self) -> None:
        """Test --here --dry-run shows current directory for file mode."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                local_branches={env.cwd: ["main"]},
                default_branches={env.cwd: "main"},
            )
            ctx = build_workspace_test_context(env, git=git)

            # Create plan file
            plan_file = env.cwd / "feature-plan.md"
            plan_file.write_text("# Feature Plan\n\nImplement feature.", encoding="utf-8")

            result = runner.invoke(implement, [str(plan_file), "--here", "--dry-run"], obj=ctx)

            assert result.exit_code == 0
            assert "Dry-run mode" in result.output
            assert "Would run in current directory" in result.output

            # Verify plan file still exists (wasn't deleted in dry-run)
            assert plan_file.exists()


class TestHereFromIssue:
    """Tests for --here flag with GitHub issue mode."""

    def test_here_from_issue_creates_impl_folder_in_cwd(self) -> None:
        """Test --here from issue creates .impl/ in current directory."""
        plan_issue = create_sample_plan_issue()

        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                local_branches={env.cwd: ["main"]},
                default_branches={env.cwd: "main"},
            )
            store, _ = create_plan_store_with_plans({"42": plan_issue})
            ctx = build_workspace_test_context(env, git=git, plan_store=store)

            result = runner.invoke(implement, ["#42", "--here", "--script"], obj=ctx)

            assert result.exit_code == 0
            assert "Created .impl/ folder" in result.output
            assert "Saved issue reference" in result.output

            # Verify .impl/ folder was created in cwd
            impl_dir = env.cwd / ".impl"
            assert impl_dir.exists()
            assert (impl_dir / "plan.md").exists()
            assert (impl_dir / "issue.json").exists()

            # Verify no worktree was created (should stay in cwd)
            assert len(git.added_worktrees) == 0

    def test_here_from_issue_with_url(self) -> None:
        """Test --here works with GitHub issue URL."""
        plan_issue = create_sample_plan_issue()

        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                local_branches={env.cwd: ["main"]},
                default_branches={env.cwd: "main"},
            )
            store, _ = create_plan_store_with_plans({"42": plan_issue})
            ctx = build_workspace_test_context(env, git=git, plan_store=store)

            result = runner.invoke(
                implement,
                ["https://github.com/owner/repo/issues/42", "--here", "--script"],
                obj=ctx,
            )

            assert result.exit_code == 0
            assert "Created .impl/ folder" in result.output

            # Verify .impl/ folder was created in cwd
            impl_dir = env.cwd / ".impl"
            assert impl_dir.exists()


class TestHereFromFile:
    """Tests for --here flag with plan file mode."""

    def test_here_from_file_creates_impl_folder_in_cwd(self) -> None:
        """Test --here from file creates .impl/ in current directory."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                local_branches={env.cwd: ["main"]},
                default_branches={env.cwd: "main"},
            )
            ctx = build_workspace_test_context(env, git=git)

            # Create plan file
            plan_content = "# Feature Plan\n\nImplement feature X."
            plan_file = env.cwd / "feature-plan.md"
            plan_file.write_text(plan_content, encoding="utf-8")

            result = runner.invoke(implement, [str(plan_file), "--here", "--script"], obj=ctx)

            assert result.exit_code == 0
            assert "Created .impl/ folder" in result.output

            # Verify .impl/ folder was created in cwd
            impl_dir = env.cwd / ".impl"
            assert impl_dir.exists()
            assert (impl_dir / "plan.md").exists()

            # Read plan content to verify
            impl_plan_content = (impl_dir / "plan.md").read_text(encoding="utf-8")
            assert "Feature Plan" in impl_plan_content

    def test_here_from_file_does_not_delete_plan_file(self) -> None:
        """Test --here does NOT delete the original plan file (unlike normal mode)."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                local_branches={env.cwd: ["main"]},
                default_branches={env.cwd: "main"},
            )
            ctx = build_workspace_test_context(env, git=git)

            # Create plan file
            plan_file = env.cwd / "feature-plan.md"
            plan_file.write_text("# Feature Plan\n\nImplement feature.", encoding="utf-8")

            result = runner.invoke(implement, [str(plan_file), "--here", "--script"], obj=ctx)

            assert result.exit_code == 0

            # Verify plan file STILL exists (not deleted like in normal mode)
            assert plan_file.exists()


class TestHereWithScriptMode:
    """Tests for --here flag with --script mode."""

    def test_here_script_mode_outputs_activation_script(self) -> None:
        """Test --here --script generates activation script."""
        plan_issue = create_sample_plan_issue()

        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                local_branches={env.cwd: ["main"]},
                default_branches={env.cwd: "main"},
            )
            store, _ = create_plan_store_with_plans({"42": plan_issue})
            ctx = build_workspace_test_context(env, git=git, plan_store=store)

            result = runner.invoke(implement, ["#42", "--here", "--script"], obj=ctx)

            assert result.exit_code == 0

            # Verify script path is output
            assert result.stdout
            script_path = Path(result.stdout.strip())
            assert script_path.exists()

    def test_here_script_with_submit_includes_all_commands(self) -> None:
        """Test --here --script --submit includes CI and submit commands."""
        plan_issue = create_sample_plan_issue()

        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                local_branches={env.cwd: ["main"]},
                default_branches={env.cwd: "main"},
            )
            store, _ = create_plan_store_with_plans({"42": plan_issue})
            ctx = build_workspace_test_context(env, git=git, plan_store=store)

            result = runner.invoke(implement, ["#42", "--here", "--script", "--submit"], obj=ctx)

            assert result.exit_code == 0

            # Verify script content includes all three commands
            assert result.stdout
            script_path = Path(result.stdout.strip())
            script_content = script_path.read_text(encoding="utf-8")

            assert "/erk:system:impl-execute" in script_content
            assert "/fast-ci" in script_content
            assert "/gt:pr-submit" in script_content

    def test_here_script_with_dangerous_flag(self) -> None:
        """Test --here --script --dangerous includes permission flag."""
        plan_issue = create_sample_plan_issue()

        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(
                git_common_dirs={env.cwd: env.git_dir},
                local_branches={env.cwd: ["main"]},
                default_branches={env.cwd: "main"},
            )
            store, _ = create_plan_store_with_plans({"42": plan_issue})
            ctx = build_workspace_test_context(env, git=git, plan_store=store)

            result = runner.invoke(implement, ["#42", "--here", "--script", "--dangerous"], obj=ctx)

            assert result.exit_code == 0

            # Verify script content includes dangerous flag
            assert result.stdout
            script_path = Path(result.stdout.strip())
            script_content = script_path.read_text(encoding="utf-8")

            assert "--dangerously-skip-permissions" in script_content
