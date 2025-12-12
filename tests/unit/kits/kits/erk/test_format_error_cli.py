"""Unit tests for format-error kit CLI command."""

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.format_error import format_error


def test_format_error_single_action() -> None:
    """Test error formatting with single action."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "File not found",
            "--details",
            "The configuration file config.yaml does not exist",
            "--action",
            "Create the configuration file",
        ],
    )

    assert result.exit_code == 0
    output = result.output

    # Check error header
    assert "❌ Error: File not found" in output

    # Check details
    assert "Details: The configuration file config.yaml does not exist" in output

    # Check action header (singular)
    assert "Suggested action:" in output

    # Check numbered action
    assert "1. Create the configuration file" in output


def test_format_error_multiple_actions() -> None:
    """Test error formatting with multiple actions."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Plan content is too minimal",
            "--details",
            "Plan has only 50 characters (minimum 100 required)",
            "--action",
            "Provide a more detailed implementation plan",
            "--action",
            "Include specific tasks, steps, or phases",
            "--action",
            "Use headers and lists to structure the plan",
        ],
    )

    assert result.exit_code == 0
    output = result.output

    # Check error header
    assert "❌ Error: Plan content is too minimal" in output

    # Check details
    assert "Details: Plan has only 50 characters (minimum 100 required)" in output

    # Check actions header (plural)
    assert "Suggested actions:" in output

    # Check all numbered actions
    assert "1. Provide a more detailed implementation plan" in output
    assert "2. Include specific tasks, steps, or phases" in output
    assert "3. Use headers and lists to structure the plan" in output


def test_format_error_two_actions() -> None:
    """Test error formatting with exactly two actions."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Git repository not found",
            "--details",
            "No .git directory found in current path",
            "--action",
            "Initialize git repository with git init",
            "--action",
            "Navigate to the correct project directory",
        ],
    )

    assert result.exit_code == 0
    output = result.output

    assert "❌ Error: Git repository not found" in output
    assert "Suggested actions:" in output
    assert "1. Initialize git repository with git init" in output
    assert "2. Navigate to the correct project directory" in output


def test_format_error_long_text() -> None:
    """Test error formatting with long text in brief, details, and actions."""
    runner = CliRunner()
    long_brief = "Very long error description that exceeds normal expectations"
    long_details = (
        "This is a very detailed error message that provides extensive context about what "
        "went wrong, including multiple sentences with specific information about the failure "
        "condition and relevant system state at the time of the error."
    )
    long_action1 = (
        "First suggested action with extensive detail about exactly what steps need to be "
        "taken to resolve the issue, including specific commands and configuration changes "
        "required"
    )
    long_action2 = (
        "Second suggested action providing alternative approach with complete implementation "
        "guidance"
    )

    result = runner.invoke(
        format_error,
        [
            "--brief",
            long_brief,
            "--details",
            long_details,
            "--action",
            long_action1,
            "--action",
            long_action2,
        ],
    )

    assert result.exit_code == 0
    output = result.output

    assert long_brief in output
    assert long_details in output
    assert long_action1 in output
    assert long_action2 in output


def test_format_error_unicode_content() -> None:
    """Test error formatting handles unicode content."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "配置文件错误",
            "--details",
            "无法读取配置文件，文件格式不正确",
            "--action",
            "检查配置文件语法",
            "--action",
            "参考示例配置文件",
        ],
    )

    assert result.exit_code == 0
    output = result.output

    assert "配置文件错误" in output
    assert "无法读取配置文件" in output
    assert "检查配置文件语法" in output
    assert "参考示例配置文件" in output


def test_format_error_output_structure() -> None:
    """Test error output has correct structure with blank lines."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Test error",
            "--details",
            "Test details",
            "--action",
            "Test action",
        ],
    )

    assert result.exit_code == 0
    lines = result.output.split("\n")

    # Find key lines
    error_line_idx = next(i for i, line in enumerate(lines) if "❌ Error:" in line)
    details_line_idx = next(i for i, line in enumerate(lines) if "Details:" in line)
    action_header_idx = next(i for i, line in enumerate(lines) if "Suggested action" in line)

    # Check blank line exists between error and details
    assert lines[error_line_idx + 1].strip() == ""

    # Check blank line exists between details and actions
    assert lines[details_line_idx + 1].strip() == ""

    # Check structure order
    assert error_line_idx < details_line_idx < action_header_idx


def test_format_error_emoji_present() -> None:
    """Test error output includes error emoji."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Simple error",
            "--details",
            "Simple details",
            "--action",
            "Simple action",
        ],
    )

    assert result.exit_code == 0
    assert "❌" in result.output


def test_format_error_action_numbering() -> None:
    """Test actions are numbered sequentially starting from 1."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Test",
            "--details",
            "Test",
            "--action",
            "First",
            "--action",
            "Second",
            "--action",
            "Third",
        ],
    )

    assert result.exit_code == 0
    output = result.output

    lines = output.split("\n")
    action_lines = [line for line in lines if line.strip().startswith(("1.", "2.", "3."))]

    assert len(action_lines) == 3
    assert "1. First" in action_lines[0]
    assert "2. Second" in action_lines[1]
    assert "3. Third" in action_lines[2]
