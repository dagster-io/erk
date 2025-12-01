"""Tests for plan create command."""

from click.testing import CliRunner
from erk_shared.plan_store.fake import FakePlanStore

from erk.cli.cli import cli
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_create_from_file(tmp_path) -> None:
    """Test creating a plan from a file."""
    # Arrange
    plan_file = tmp_path / "test-plan.md"
    plan_content = "# Test Feature\n\nImplementation details here"
    plan_file.write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Created plan #1" in result.output
        assert "View:       erk get 1" in result.output
        assert "Implement:  erk implement 1" in result.output
        assert "Submit:     erk submit 1" in result.output

        # Verify plan was created with correct data via plan_store
        assert len(plan_store.created_plans) == 1
        plan = plan_store.get_plan(env.cwd, "1")
        assert plan.url.startswith("https://github.com/")
        assert "Test Feature" in plan.title
        assert plan.body == plan_content


def test_create_from_stdin() -> None:
    """Test creating a plan from stdin."""
    # Arrange
    plan_content = "# Stdin Feature\n\nImplementation from stdin"

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "create"], input=plan_content, obj=ctx)

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Created plan #1" in result.output

        # Verify title was extracted from H1
        plan = plan_store.get_plan(env.cwd, "1")
        assert "Stdin Feature" in plan.title


def test_create_extracts_h1_title(tmp_path) -> None:
    """Test automatic title extraction from H1."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_content = "# Auto Extracted Title\n\nContent here"
    plan_file.write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0
        plan = plan_store.get_plan(env.cwd, "1")
        assert "Auto Extracted Title" in plan.title


def test_create_with_explicit_title(tmp_path) -> None:
    """Test overriding auto-extracted title with explicit --title flag."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_content = "# Auto Title\n\nThis will be overridden"
    plan_file.write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(
            cli, ["plan", "create", "--file", str(plan_file), "--title", "Custom Title"], obj=ctx
        )

        # Assert
        assert result.exit_code == 0
        plan = plan_store.get_plan(env.cwd, "1")
        assert "Custom Title" in plan.title


def test_create_with_additional_labels(tmp_path) -> None:
    """Test adding multiple custom labels."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_content = "# Bug Fix\n\nFix critical bug"
    plan_file.write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(
            cli,
            ["plan", "create", "--file", str(plan_file), "--label", "bug", "--label", "urgent"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        plan = plan_store.get_plan(env.cwd, "1")
        # Verify custom labels were added
        assert "bug" in plan.labels
        assert "urgent" in plan.labels


def test_create_fails_with_no_input() -> None:
    """Test error when no input provided (empty stdin)."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act (CliRunner provides empty stdin by default, not TTY)
        # Empty stdin will be read successfully but content will be empty
        result = runner.invoke(cli, ["plan", "create"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        # Empty stdin content results in "empty" error
        assert "empty" in result.output.lower()


def test_create_with_file_ignores_stdin(tmp_path) -> None:
    """Test that --file takes precedence over stdin when both are provided."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# File Title\n\nFile content", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act (provide both file and stdin - file should take precedence)
        result = runner.invoke(
            cli,
            ["plan", "create", "--file", str(plan_file)],
            input="# Stdin Title\n\nStdin content should be ignored",
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Verify the file content was used, not stdin
        plan = plan_store.get_plan(env.cwd, "1")
        assert "File Title" in plan.title


def test_create_ensures_required_labels_exist(tmp_path) -> None:
    """Test that required labels are created if they don't exist."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Feature\n\nDetails", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify ensure_label was called (labels dict populated)
        assert len(plan_store.labels) > 0


def test_create_with_empty_file(tmp_path) -> None:
    """Test error when plan file is empty."""
    # Arrange
    plan_file = tmp_path / "empty.md"
    plan_file.write_text("", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "empty" in result.output.lower()


def test_create_with_nonexistent_file() -> None:
    """Test error when plan file doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", "/nonexistent/plan.md"], obj=ctx)

        # Assert
        # Click's Path(exists=True) validation causes exit code 2 (usage error)
        assert result.exit_code == 2
        assert "Error" in result.output or "does not exist" in result.output.lower()


def test_create_with_h2_title_fallback(tmp_path) -> None:
    """Test title extraction fallback to H2 when no H1 present."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_content = "## H2 Title\n\nContent here"
    plan_file.write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0
        plan = plan_store.get_plan(env.cwd, "1")
        assert "H2 Title" in plan.title
