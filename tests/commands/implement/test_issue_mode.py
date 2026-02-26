"""Tests for GitHub issue mode in implement command."""

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.gateway.git.fake import FakeGit
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.fakes.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def test_implement_from_plain_issue_number() -> None:
    """Test implementing from GitHub issue number without # prefix."""
    plan_issue = create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        executor = FakePromptExecutor(available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, prompt_executor=executor)

        # Test with plain number (no # prefix)
        result = runner.invoke(implement, ["123"], obj=ctx)

        assert result.exit_code == 0
        assert "✓ Created impl folder" in result.output

        # Verify branch-scoped impl folder exists with correct plan ID
        impl_dir = env.cwd / ".erk" / "impl-context" / "current"
        plan_ref_content = (impl_dir / "ref.json").read_text(encoding="utf-8")
        assert '"plan_id": "123"' in plan_ref_content


def test_implement_from_issue_number() -> None:
    """Test implementing from GitHub issue number with # prefix."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakePromptExecutor(available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, prompt_executor=executor)

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0
        assert "✓ Created impl folder" in result.output

        # Verify branch-scoped impl folder exists
        impl_path = env.cwd / ".erk" / "impl-context" / "current"
        assert impl_path.exists()
        assert (impl_path / "plan.md").exists()
        assert (impl_path / "ref.json").exists()


def test_implement_from_issue_url() -> None:
    """Test implementing from GitHub issue URL."""
    plan_issue = create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        executor = FakePromptExecutor(available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, prompt_executor=executor)

        url = "https://github.com/owner/repo/issues/123"
        result = runner.invoke(implement, [url], obj=ctx)

        assert result.exit_code == 0
        assert "✓ Created impl folder" in result.output

        # Verify ref.json contains correct plan ID
        impl_dir = env.cwd / ".erk" / "impl-context" / "current"
        plan_ref_content = (impl_dir / "ref.json").read_text(encoding="utf-8")
        assert '"plan_id": "123"' in plan_ref_content


def test_implement_creates_impl_folder_in_cwd() -> None:
    """Test that implement creates .impl/ folder in current directory."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakePromptExecutor(available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, prompt_executor=executor)

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0
        assert "✓ Created impl folder" in result.output

        # Verify branch-scoped impl was created in current directory
        impl_dir = env.cwd / ".erk" / "impl-context" / "current"
        assert impl_dir.exists()


def test_implement_from_issue_fails_when_not_found() -> None:
    """Test that command fails when issue doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#999", "--dry-run"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output


def test_implement_from_issue_dry_run() -> None:
    """Test dry-run mode for issue implementation."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would run in current directory" in result.output
        assert "Add Authentication Feature" in result.output

        # Verify no .impl/ created in dry-run
        assert not (env.cwd / ".impl").exists()


def test_auto_detect_fails_on_plnd_branch_without_plan_ref() -> None:
    """Branch names no longer encode issue numbers — auto-detect requires plan-ref.json."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "plnd/my-feature-01-16-1200"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "plnd/my-feature-01-16-1200"},
        )
        store, fake_github = create_plan_store_with_plans({"42": plan_issue})
        # Also register the PR under the real branch name so PlannedPRBackend
        # can resolve it via get_pr_for_branch during auto-detection.
        # (create_plan_store_with_plans registers under "plan-42")
        real_branch = "P42-my-feature-01-16-1200"
        fake_github._prs[real_branch] = fake_github._prs["plan-42"]
        fake_github._prs_by_branch[real_branch] = fake_github._pr_details[42]
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # TARGET omitted — cannot auto-detect without plan-ref.json
        result = runner.invoke(implement, ["--dry-run"], obj=ctx)

        assert result.exit_code != 0
        assert "Could not auto-detect plan number" in result.output


def test_auto_detect_fails_on_non_plan_branch() -> None:
    """Test error when TARGET omitted and not on a plan branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(implement, ["--dry-run"], obj=ctx)

        assert result.exit_code != 0
        assert "Could not auto-detect plan number" in result.output
        assert "feature-branch" in result.output
