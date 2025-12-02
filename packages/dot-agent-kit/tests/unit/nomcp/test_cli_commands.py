"""Tests for nomcp CLI commands (Layer 4: Business Logic Tests)."""

from pathlib import Path

import yaml
from click.testing import CliRunner

from dot_agent_kit.commands.nomcp.skill import generate


class TestSkillGenerateCommand:
    """Tests for the 'nomcp skill generate' command."""

    def test_generate_requires_kit_yaml(self, tmp_path: Path) -> None:
        """Command fails if kit.yaml doesn't exist."""
        runner = CliRunner()
        result = runner.invoke(generate, [str(tmp_path)])

        assert result.exit_code != 0
        assert "kit.yaml not found" in result.output

    def test_generate_creates_skill_md(self, tmp_path: Path) -> None:
        """Command generates SKILL.md from kit.yaml."""
        # Create kit.yaml
        kit_yaml = {
            "name": "test-kit",
            "version": "0.1.0",
            "kit_cli_commands": [
                {
                    "name": "search",
                    "path": "kit_cli_commands/test-kit/search.py",
                    "description": "Search for items",
                },
                {
                    "name": "get-item",
                    "path": "kit_cli_commands/test-kit/get_item.py",
                    "description": "Get an item by ID",
                },
            ],
        }
        (tmp_path / "kit.yaml").write_text(
            yaml.dump(kit_yaml),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(generate, [str(tmp_path)])

        assert result.exit_code == 0

        # Check SKILL.md was created
        skill_path = tmp_path / "skills" / "test-kit" / "SKILL.md"
        assert skill_path.exists()

        content = skill_path.read_text(encoding="utf-8")
        assert "test-kit" in content
        assert "dot-agent run test-kit search" in content
        assert "dot-agent run test-kit get-item" in content
        assert "Search for items" in content
        assert "Get an item by ID" in content

    def test_generate_with_custom_output(self, tmp_path: Path) -> None:
        """Command respects custom output path."""
        # Create kit.yaml
        kit_yaml = {
            "name": "test-kit",
            "version": "0.1.0",
            "kit_cli_commands": [],
        }
        (tmp_path / "kit.yaml").write_text(
            yaml.dump(kit_yaml),
            encoding="utf-8",
        )

        custom_output = tmp_path / "custom" / "MY_SKILL.md"

        runner = CliRunner()
        result = runner.invoke(generate, [str(tmp_path), "-o", str(custom_output)])

        assert result.exit_code == 0
        assert custom_output.exists()

    def test_generate_handles_empty_commands(self, tmp_path: Path) -> None:
        """Command handles kit with no commands."""
        kit_yaml = {
            "name": "empty-kit",
            "version": "0.1.0",
            "kit_cli_commands": [],
        }
        (tmp_path / "kit.yaml").write_text(
            yaml.dump(kit_yaml),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(generate, [str(tmp_path)])

        assert result.exit_code == 0
        assert "Warning: No kit_cli_commands" in result.output

    def test_generate_requires_kit_name(self, tmp_path: Path) -> None:
        """Command fails if kit.yaml has no name field."""
        kit_yaml = {
            "version": "0.1.0",
        }
        (tmp_path / "kit.yaml").write_text(
            yaml.dump(kit_yaml),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(generate, [str(tmp_path)])

        assert result.exit_code != 0
        assert "missing 'name'" in result.output


class TestInitCommandHelpers:
    """Tests for helper functions in the init command."""

    def test_sanitize_name_lowercases(self) -> None:
        """sanitize_name converts to lowercase."""
        from dot_agent_kit.commands.nomcp.init import _sanitize_name

        assert _sanitize_name("MyKit") == "mykit"
        assert _sanitize_name("ALLCAPS") == "allcaps"

    def test_sanitize_name_replaces_underscores(self) -> None:
        """sanitize_name replaces underscores with hyphens."""
        from dot_agent_kit.commands.nomcp.init import _sanitize_name

        assert _sanitize_name("my_kit_name") == "my-kit-name"

    def test_sanitize_name_removes_invalid_chars(self) -> None:
        """sanitize_name removes invalid characters."""
        from dot_agent_kit.commands.nomcp.init import _sanitize_name

        assert _sanitize_name("my.kit!name") == "mykitname"
        assert _sanitize_name("kit@123") == "kit123"

    def test_sanitize_name_removes_leading_numbers(self) -> None:
        """sanitize_name removes leading numbers/hyphens."""
        from dot_agent_kit.commands.nomcp.init import _sanitize_name

        assert _sanitize_name("123kit") == "kit"
        assert _sanitize_name("-my-kit") == "my-kit"

    def test_tool_name_to_command_name(self) -> None:
        """tool_name_to_command_name converts MCP tool names."""
        from dot_agent_kit.commands.nomcp.init import _tool_name_to_command_name

        assert _tool_name_to_command_name("searchRepositories") == "searchrepositories"
        assert _tool_name_to_command_name("get_file") == "get-file"
        assert _tool_name_to_command_name("CreateIssue") == "createissue"

    def test_tool_name_to_function_name(self) -> None:
        """tool_name_to_function_name converts to valid Python names."""
        from dot_agent_kit.commands.nomcp.init import _tool_name_to_function_name

        assert _tool_name_to_function_name("search-repos") == "search_repos"
        assert _tool_name_to_function_name("getFile") == "getfile"
        assert _tool_name_to_function_name("123invalid") == "cmd_123invalid"

    def test_mcp_type_to_python_type(self) -> None:
        """mcp_type_to_python_type converts MCP types."""
        from dot_agent_kit.commands.nomcp.init import _mcp_type_to_python_type

        assert _mcp_type_to_python_type("string") == "str"
        assert _mcp_type_to_python_type("integer") == "int"
        assert _mcp_type_to_python_type("number") == "float"
        assert _mcp_type_to_python_type("boolean") == "bool"
        assert _mcp_type_to_python_type("array") == "list"
        assert _mcp_type_to_python_type("object") == "dict"
        assert _mcp_type_to_python_type("unknown") == "str"  # Default

    def test_mcp_type_to_click_type(self) -> None:
        """mcp_type_to_click_type converts to Click types."""
        from dot_agent_kit.commands.nomcp.init import _mcp_type_to_click_type

        assert _mcp_type_to_click_type("string") == "str"
        assert _mcp_type_to_click_type("integer") == "int"
        assert _mcp_type_to_click_type("number") == "float"
        assert _mcp_type_to_click_type("boolean") == "bool"
        assert _mcp_type_to_click_type("unknown") == "str"  # Default
