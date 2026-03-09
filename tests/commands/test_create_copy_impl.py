"""Tests for erk create --copy-plan flag."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.fakes.git import FakeGit
from erk_shared.gateway.git.abc import WorktreeInfo
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_create_copy_plan_success() -> None:
    """Test --copy-plan copies plan directory to new worktree."""
    from erk_shared.impl_folder import get_impl_dir

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Setup: Create branch-scoped impl folder in current worktree (at repo root)
        source_impl_dir = get_impl_dir(env.cwd, branch_name="main")
        source_impl_dir.mkdir(parents=True, exist_ok=True)
        (source_impl_dir / "plan.md").write_text("# Plan content", encoding="utf-8")
        progress_content = (
            "---\ncompleted_steps: 2\ntotal_steps: 5\n---\n\n"
            "- [x] Step 1\n- [x] Step 2\n- [ ] Step 3"
        )
        (source_impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

        # Setup: Configure git state
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
        )

        test_ctx = env.build_context(git=git)

        # Act: Create worktree with --copy-plan
        result = runner.invoke(
            cli,
            ["wt", "create", "new-feature", "--copy-plan"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: plan directory copied to new worktree at branch-scoped path
        new_wt_path = env.erk_root / "repos" / env.cwd.name / "worktrees" / "new-feature"
        new_wt_impl = get_impl_dir(new_wt_path, branch_name="new-feature")
        assert new_wt_impl.exists(), "impl directory should exist in new worktree"
        assert new_wt_impl.is_dir(), "impl should be a directory"

        # Assert: plan.md copied with correct content
        assert (new_wt_impl / "plan.md").exists(), "plan.md should be copied"
        plan_content = (new_wt_impl / "plan.md").read_text(encoding="utf-8")
        assert plan_content == "# Plan content", "plan.md content should match source"

        # Assert: progress.md copied with correct content
        assert (new_wt_impl / "progress.md").exists(), "progress.md should be copied"
        progress_content = (new_wt_impl / "progress.md").read_text(encoding="utf-8")
        assert "completed_steps: 2" in progress_content, "YAML front matter should be preserved"
        assert "- [x] Step 1" in progress_content, "Checkbox states should be preserved"
        assert "- [ ] Step 3" in progress_content, "Pending checkboxes should be preserved"

        # Assert: Success message in output
        assert "Copied" in result.output or "✓" in result.output


def test_create_copy_plan_missing_plan_error() -> None:
    """Test --copy-plan errors when current directory has no .impl/."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Setup: No .impl directory exists
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
        )

        test_ctx = env.build_context(git=git)

        # Act: Try to create worktree with --copy-plan
        result = runner.invoke(
            cli,
            ["wt", "create", "new-feature", "--copy-plan"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command failed with error
        assert result.exit_code != 0

        # Assert: Error message mentions missing implementation directory
        assert "No implementation directory found" in result.output
        assert str(env.cwd) in result.output


def test_create_copy_plan_mutual_exclusion_with_plan_file() -> None:
    """Test --copy-plan and --from-plan-file are mutually exclusive."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Setup: Create .impl directory and plan file
        plan_dir = env.cwd / ".impl"
        plan_dir.mkdir()
        (plan_dir / "plan.md").write_text("# Plan content", encoding="utf-8")

        plan_file = env.cwd / "my-plan.md"
        plan_file.write_text("# External plan", encoding="utf-8")

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
        )

        test_ctx = env.build_context(git=git)

        # Act: Try to use both --copy-plan and --from-plan-file
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", str(plan_file), "--copy-plan"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command failed with error
        assert result.exit_code != 0

        # Assert: Error message explains mutual exclusion
        assert "mutually exclusive" in result.output
        assert "--copy-plan" in result.output
        assert "--from-plan-file" in result.output


def test_create_copy_plan_preserves_progress() -> None:
    """Test --copy-plan preserves progress.md checkboxes exactly."""
    from erk_shared.impl_folder import get_impl_dir

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Setup: Create branch-scoped impl with mixed checkbox states at repo root
        plan_dir = get_impl_dir(env.cwd, branch_name="main")
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / "plan.md").write_text("# Plan", encoding="utf-8")

        original_progress = """---
completed_steps: 3
total_steps: 6
---

# Progress Tracking

- [x] 1. First step (complete)
- [x] 2. Second step (complete)
- [ ] 3. Third step (pending)
- [x] 4. Fourth step (complete)
- [ ] 5. Fifth step (pending)
- [ ] 6. Sixth step (pending)
"""
        (plan_dir / "progress.md").write_text(original_progress, encoding="utf-8")

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
        )

        test_ctx = env.build_context(git=git)

        # Act: Create worktree with --copy-plan
        result = runner.invoke(
            cli,
            ["wt", "create", "phase-2", "--copy-plan"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: progress.md copied with exact content
        new_wt_path = env.erk_root / "repos" / env.cwd.name / "worktrees" / "phase-2"
        new_wt_plan = get_impl_dir(new_wt_path, branch_name="phase-2")
        copied_progress = (new_wt_plan / "progress.md").read_text(encoding="utf-8")

        assert copied_progress == original_progress, "Progress should be copied exactly as-is"


def test_create_copy_plan_preserves_yaml_front_matter() -> None:
    """Test --copy-plan preserves YAML front matter in progress.md."""
    from erk_shared.impl_folder import get_impl_dir

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Setup: Create branch-scoped impl with YAML front matter at repo root
        plan_dir = get_impl_dir(env.cwd, branch_name="main")
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / "plan.md").write_text("# Plan", encoding="utf-8")

        original_progress = """---
completed_steps: 5
total_steps: 10
custom_field: some_value
---

# Progress

- [x] Step 1
- [ ] Step 2
"""
        (plan_dir / "progress.md").write_text(original_progress, encoding="utf-8")

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
        )

        test_ctx = env.build_context(git=git)

        # Act: Create worktree with --copy-plan
        result = runner.invoke(
            cli,
            ["wt", "create", "next-phase", "--copy-plan"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: YAML front matter preserved
        new_wt_path = env.erk_root / "repos" / env.cwd.name / "worktrees" / "next-phase"
        new_wt_plan = get_impl_dir(new_wt_path, branch_name="next-phase")
        copied_progress = (new_wt_plan / "progress.md").read_text(encoding="utf-8")

        assert "completed_steps: 5" in copied_progress, "completed_steps preserved"
        assert "total_steps: 10" in copied_progress, "total_steps preserved"
        assert "custom_field: some_value" in copied_progress, "Custom YAML fields preserved"
