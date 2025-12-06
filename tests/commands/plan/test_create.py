"""Tests for plan create command."""

from click.testing import CliRunner
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.metadata import find_metadata_block

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
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Created plan #1" in result.output
        assert "https://github.com/test-owner/test-repo/issues/1" in result.output
        assert "View:       erk get 1" in result.output
        assert "Implement:  erk implement 1" in result.output
        assert "Submit:     erk submit 1" in result.output

        # Verify issue was created with correct data
        assert len(issues.created_issues) == 1
        title, body, labels = issues.created_issues[0]
        assert title == "Test Feature [erk-plan]"
        assert "erk-plan" in labels

        # Verify Schema V2 format: metadata in body
        assert "plan-header" in body
        # Note: worktree_name is set later when worktree is actually created

        # Verify plan content was added as first comment
        assert len(issues.added_comments) == 1
        comment_number, comment_body = issues.added_comments[0]
        assert comment_number == 1
        assert plan_content in comment_body
        assert "plan-body" in comment_body


def test_create_from_stdin() -> None:
    """Test creating a plan from stdin."""
    # Arrange
    plan_content = "# Stdin Feature\n\nImplementation from stdin"

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "create"], input=plan_content, obj=ctx)

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Created plan #1" in result.output

        # Verify title was extracted from H1 (with [erk-plan] suffix)
        title, body, labels = issues.created_issues[0]
        assert title == "Stdin Feature [erk-plan]"


def test_create_extracts_h1_title(tmp_path) -> None:
    """Test automatic title extraction from H1."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_content = "# Auto Extracted Title\n\nContent here"
    plan_file.write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0
        title, body, labels = issues.created_issues[0]
        assert title == "Auto Extracted Title [erk-plan]"


def test_create_with_explicit_title(tmp_path) -> None:
    """Test overriding auto-extracted title with explicit --title flag."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_content = "# Auto Title\n\nThis will be overridden"
    plan_file.write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(
            cli, ["plan", "create", "--file", str(plan_file), "--title", "Custom Title"], obj=ctx
        )

        # Assert
        assert result.exit_code == 0
        title, body, labels = issues.created_issues[0]
        assert title == "Custom Title [erk-plan]"


def test_create_with_additional_labels(tmp_path) -> None:
    """Test adding multiple custom labels."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_content = "# Bug Fix\n\nFix critical bug"
    plan_file.write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(
            cli,
            ["plan", "create", "--file", str(plan_file), "--label", "bug", "--label", "urgent"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        title, body, labels = issues.created_issues[0]
        assert "erk-plan" in labels
        assert "bug" in labels
        assert "urgent" in labels


def test_create_fails_with_no_input() -> None:
    """Test error when no input provided (empty stdin)."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

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
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

        # Act (provide both file and stdin - file should take precedence)
        result = runner.invoke(
            cli,
            ["plan", "create", "--file", str(plan_file)],
            input="# Stdin Title\n\nStdin content should be ignored",
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Verify the file content was used, not stdin (with [erk-plan] suffix)
        title, body, labels = issues.created_issues[0]
        assert title == "File Title [erk-plan]"


def test_create_ensures_label_exists(tmp_path) -> None:
    """Test that erk-plan label is created if it doesn't exist."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Feature\n\nDetails", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(labels=set())  # No labels exist initially
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify label was created
        assert len(issues.created_labels) == 1
        label, description, color = issues.created_labels[0]
        assert label == "erk-plan"
        assert description == "Implementation plan for manual execution"
        assert color == "0E8A16"


def test_create_uses_current_schema(tmp_path) -> None:
    """Test that created issue uses current schema format (metadata body + plan comment)."""
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_content = "# Schema Test\n\nPlan content"
    plan_file.write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify schema structure
        title, body, labels = issues.created_issues[0]

        # Issue body should contain plan-header metadata block
        header_block = find_metadata_block(body, "plan-header")
        assert header_block is not None
        assert header_block.data["schema_version"] == "2"
        assert "created_at" in header_block.data
        assert "created_by" in header_block.data
        # Note: worktree_name is set later when worktree is actually created

        # First comment should contain plan-body metadata block
        comment_number, comment_body = issues.added_comments[0]
        assert comment_number == 1
        assert "plan-body" in comment_body
        assert plan_content in comment_body


def test_create_with_empty_file(tmp_path) -> None:
    """Test error when plan file is empty."""
    # Arrange
    plan_file = tmp_path / "empty.md"
    plan_file.write_text("", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

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
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

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
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0
        title, body, labels = issues.created_issues[0]
        assert title == "H2 Title [erk-plan]"


def test_create_does_not_include_worktree_name(tmp_path) -> None:
    """Test that worktree_name is NOT included at issue creation time.

    worktree_name is now set later when the actual worktree is created,
    not at issue creation time.
    """
    # Arrange
    plan_file = tmp_path / "plan.md"
    plan_content = "# My Cool Feature!\n\nDetails"
    plan_file.write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "create", "--file", str(plan_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify worktree_name is NOT in the header
        title, body, labels = issues.created_issues[0]
        header_block = find_metadata_block(body, "plan-header")
        assert header_block is not None
        assert "worktree_name" not in header_block.data
