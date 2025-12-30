"""Tests for hook CLI commands."""

import json
import os
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.hook.group import hook_group


def create_test_hook_entry(
    hook_id: str = "test-hook",
    command: str = "echo test",
    timeout: int = 30,
) -> dict:
    """Factory for creating test hook entry dictionaries.

    Note: kit_id is no longer used in the new hook format.
    """
    # Encode metadata in command via environment variables
    command_with_metadata = f"ERK_HOOK_ID={hook_id} {command}"
    return {
        "command": command_with_metadata,
        "timeout": timeout,
    }


def create_test_settings(hooks_data: dict | None = None) -> dict:
    """Factory for creating test settings.json structure.

    Expected hooks_data format:
    {
        "lifecycle": [
            {
                "matcher": "pattern",
                "hooks": [hook_entry, ...]
            }
        ]
    }
    """
    if hooks_data is None:
        hooks_data = {}
    return {"hooks": hooks_data}


def write_settings_json(tmp_path: Path, settings_data: dict) -> Path:
    """Write settings.json to a temporary .claude directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = claude_dir / "settings.json"
    settings_path.write_text(json.dumps(settings_data, indent=2), encoding="utf-8")
    return settings_path


def invoke_in_dir(cli_runner: CliRunner, tmp_path: Path, command_group, args: list[str]):
    """Invoke a CLI command in a specific directory."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        return cli_runner.invoke(command_group, args)
    finally:
        os.chdir(original_cwd)


class TestHookListCommand:
    """Tests for 'hook list' command."""

    def test_no_settings_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test list command when no settings.json exists."""
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 0
        assert "No hooks installed." in result.output

    def test_single_hook(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test list command with a single hook."""
        hook_entry = create_test_hook_entry(hook_id="my-hook", command="echo hello")
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook_entry]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 0
        assert "my-hook" in result.output
        assert "pre:" in result.output

    def test_multiple_hooks_same_matcher(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test list command with multiple hooks in same matcher."""
        hook1 = create_test_hook_entry(hook_id="hook1")
        hook2 = create_test_hook_entry(hook_id="hook2")
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook1, hook2]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 0
        assert "hook1" in result.output
        assert "hook2" in result.output
        assert "pre:" in result.output

    def test_multiple_hooks_multiple_matchers(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test list command with hooks across different matchers."""
        hook1 = create_test_hook_entry(hook_id="hook1")
        hook2 = create_test_hook_entry(hook_id="hook2")
        settings = create_test_settings(
            {
                "pre": [
                    {"matcher": "**/*.py", "hooks": [hook1]},
                    {"matcher": "**/*.js", "hooks": [hook2]},
                ]
            }
        )
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 0
        assert "hook1" in result.output
        assert "hook2" in result.output
        assert "pre:" in result.output

    def test_multiple_hooks_multiple_lifecycles(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test list command with hooks across different lifecycles."""
        hook1 = create_test_hook_entry(hook_id="hook1")
        hook2 = create_test_hook_entry(hook_id="hook2")
        settings = create_test_settings(
            {
                "pre": [{"matcher": "**/*.py", "hooks": [hook1]}],
                "post": [{"matcher": "**/*.js", "hooks": [hook2]}],
            }
        )
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 0
        assert "hook1" in result.output
        assert "hook2" in result.output
        assert "pre:" in result.output
        assert "post:" in result.output

    def test_empty_hooks_object(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test list command with empty hooks object."""
        settings = create_test_settings({})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 0
        assert "No hooks installed." in result.output

    def test_empty_lifecycle(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test list command with empty lifecycle."""
        settings = create_test_settings({"pre": []})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 0
        assert "No hooks installed." in result.output

    def test_empty_matcher_group(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test list command with empty matcher group."""
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": []}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 0
        assert "No hooks installed." in result.output

    def test_invalid_json(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test list command with malformed JSON."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"
        settings_path.write_text("{invalid json", encoding="utf-8")

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 1
        assert "Error loading settings.json" in result.output

    def test_local_hook_without_dot_agent(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test list command with local hook (no _dot_agent field)."""
        # Local hook without _dot_agent field - this is valid
        local_hook = {"command": "echo test", "timeout": 30}
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [local_hook]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 0
        assert "local-hook" in result.output
        assert "pre:" in result.output

    def test_invalid_schema(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test list command with invalid Pydantic schema."""
        # Invalid hook: missing required command field
        invalid_hook = {"timeout": 30}
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [invalid_hook]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])

        assert result.exit_code == 1
        assert "Error loading settings.json" in result.output


class TestHookShowCommand:
    """Tests for 'hook show' command."""

    def test_show_existing_hook(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test show command for an existing hook."""
        hook_entry = create_test_hook_entry(
            hook_id="my-hook",
            command="echo hello world",
            timeout=45,
        )
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook_entry]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "my-hook"])

        assert result.exit_code == 0
        assert "Hook: my-hook" in result.output
        assert "Lifecycle: pre" in result.output
        assert "Matcher: **/*.py" in result.output
        assert "Timeout: 45s" in result.output
        expected_cmd = "ERK_HOOK_ID=my-hook echo hello world"
        assert f"Command: {expected_cmd}" in result.output

    def test_show_hook_in_post_lifecycle(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test show command for hook in post lifecycle."""
        hook_entry = create_test_hook_entry(hook_id="post-hook", command="cleanup")
        settings = create_test_settings({"post": [{"matcher": "**/*.js", "hooks": [hook_entry]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "post-hook"])

        assert result.exit_code == 0
        assert "Hook: post-hook" in result.output
        assert "Lifecycle: post" in result.output
        assert "Matcher: **/*.js" in result.output

    def test_show_nonexistent_hook(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test show command for hook that doesn't exist."""
        hook_entry = create_test_hook_entry(hook_id="existing-hook")
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook_entry]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "nonexistent-hook"])

        assert result.exit_code == 1
        assert "Hook 'nonexistent-hook' not found" in result.output

    def test_show_no_settings_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test show command when no settings.json exists."""
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "any-hook"])

        assert result.exit_code == 1
        assert "Hook 'any-hook' not found" in result.output

    def test_show_invalid_json(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test show command with malformed JSON."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"
        settings_path.write_text("{invalid json", encoding="utf-8")

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "any-hook"])

        assert result.exit_code == 1
        assert "Error loading settings.json" in result.output

    def test_show_case_sensitive(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that show command is case-sensitive."""
        hook_entry = create_test_hook_entry(hook_id="MyHook")
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook_entry]}]})
        write_settings_json(tmp_path, settings)

        # Try lowercase - should not find it
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "myhook"])
        assert result.exit_code == 1
        assert "not found" in result.output

        # Try correct case - should find it
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "MyHook"])
        assert result.exit_code == 0
        assert "Hook: MyHook" in result.output


class TestHookValidateCommand:
    """Tests for 'hook validate' command."""

    def test_validate_no_settings_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validate command when no settings.json exists."""
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])

        assert result.exit_code == 0
        assert "✓" in result.output
        assert "No settings.json file" in result.output
        assert "valid" in result.output

    def test_validate_valid_configuration(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validate command with valid configuration."""
        hook_entry = create_test_hook_entry(hook_id="my-hook")
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook_entry]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])

        assert result.exit_code == 0
        assert "✓" in result.output
        assert "Hooks configuration is valid" in result.output

    def test_validate_empty_hooks(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validate command with empty but valid hooks."""
        settings = create_test_settings({})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])

        assert result.exit_code == 0
        assert "✓" in result.output
        assert "Hooks configuration is valid" in result.output

    def test_validate_with_extra_fields(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validate command with extra fields (should be allowed)."""
        hook_entry = create_test_hook_entry(hook_id="my-hook")
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook_entry]}]})
        # Add extra top-level field
        settings["extra_field"] = "some_value"
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])

        assert result.exit_code == 0
        assert "✓" in result.output
        assert "Hooks configuration is valid" in result.output

    def test_validate_invalid_json(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validate command with malformed JSON."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"
        settings_path.write_text("{invalid json", encoding="utf-8")

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])

        assert result.exit_code == 1
        assert "✗" in result.output
        assert "Invalid JSON in settings.json" in result.output

    def test_validate_missing_required_field(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validate command with missing required field."""
        # Missing required command field
        invalid_hook = {"timeout": 30}
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [invalid_hook]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])

        assert result.exit_code == 1
        assert "✗" in result.output
        assert "Validation errors in settings.json:" in result.output

    def test_validate_invalid_field_type(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validate command with invalid field type."""
        # timeout should be int, not string
        invalid_hook = create_test_hook_entry()
        invalid_hook["timeout"] = "not-a-number"
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [invalid_hook]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])

        assert result.exit_code == 1
        assert "✗" in result.output
        assert "Validation errors in settings.json:" in result.output

    def test_validate_multiple_errors(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validate command reports all validation errors."""
        # Two invalid hooks with different errors
        hook1 = {"command": "echo test", "timeout": "bad"}  # Missing _dot_agent
        hook2 = {
            "command": "echo test2",
            "timeout": "also-bad",
            "_dot_agent": {"kit_id": "kit"},
        }  # Missing hook_id
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook1, hook2]}]})
        write_settings_json(tmp_path, settings)

        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])

        assert result.exit_code == 1
        assert "✗" in result.output
        assert "Validation errors in settings.json:" in result.output
        # Should have multiple error lines
        error_lines = [line for line in result.output.split("\n") if line.strip().startswith("")]
        assert len(error_lines) >= 2


class TestHookCommandsIntegration:
    """Integration tests for hook commands working together."""

    def test_list_show_validate_workflow(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test complete workflow: create hooks, list, show, validate."""
        # Create a settings file with multiple hooks
        hook1 = create_test_hook_entry(hook_id="hook1", command="echo first", timeout=30)
        hook2 = create_test_hook_entry(hook_id="hook2", command="echo second", timeout=60)
        settings = create_test_settings(
            {
                "pre": [{"matcher": "**/*.py", "hooks": [hook1]}],
                "post": [{"matcher": "**/*.js", "hooks": [hook2]}],
            }
        )
        write_settings_json(tmp_path, settings)

        # 1. Validate the configuration
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])
        assert result.exit_code == 0
        assert "✓" in result.output

        # 2. List all hooks
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])
        assert result.exit_code == 0
        assert "hook1" in result.output
        assert "hook2" in result.output
        assert "pre:" in result.output
        assert "post:" in result.output

        # 3. Show first hook
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "hook1"])
        assert result.exit_code == 0
        assert "Hook: hook1" in result.output
        assert "Lifecycle: pre" in result.output
        expected_cmd1 = "ERK_HOOK_ID=hook1 echo first"
        assert f"Command: {expected_cmd1}" in result.output
        assert "Timeout: 30s" in result.output

        # 4. Show second hook
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "hook2"])
        assert result.exit_code == 0
        assert "Hook: hook2" in result.output
        assert "Lifecycle: post" in result.output
        expected_cmd2 = "ERK_HOOK_ID=hook2 echo second"
        assert f"Command: {expected_cmd2}" in result.output
        assert "Timeout: 60s" in result.output

    def test_error_diagnosis_workflow(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test using validate to diagnose configuration errors."""
        # Create invalid configuration - missing required command field
        invalid_hook = {"timeout": 30}
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [invalid_hook]}]})
        write_settings_json(tmp_path, settings)

        # Validate should report the errors
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])
        assert result.exit_code == 1
        assert "✗" in result.output
        assert "Validation errors" in result.output

        # List should also fail with same error
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])
        assert result.exit_code == 1
        assert "Error loading settings.json" in result.output

        # Show should also fail
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "any:hook"])
        assert result.exit_code == 1
        assert "Error loading settings.json" in result.output

    def test_unicode_in_commands(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test hooks with unicode characters in commands."""
        hook_entry = create_test_hook_entry(hook_id="unicode-hook", command="echo 'Hello 世界 🌍'")
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook_entry]}]})
        write_settings_json(tmp_path, settings)

        # Validate
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["validate"])
        assert result.exit_code == 0

        # List
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])
        assert result.exit_code == 0
        assert "unicode-hook" in result.output

        # Show
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "unicode-hook"])
        assert result.exit_code == 0
        assert "echo 'Hello 世界 🌍'" in result.output

    def test_special_characters_in_identifiers(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test hooks with special characters in hook_id."""
        hook_entry = create_test_hook_entry(hook_id="my-special_hook.v1")
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook_entry]}]})
        write_settings_json(tmp_path, settings)

        # List
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])
        assert result.exit_code == 0
        assert "my-special_hook.v1" in result.output

        # Show
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", "my-special_hook.v1"])
        assert result.exit_code == 0
        assert "Hook: my-special_hook.v1" in result.output

    def test_very_long_hook_spec(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test hooks with very long identifiers."""
        long_hook_id = "very-long-hook-name-" + "y" * 100
        hook_entry = create_test_hook_entry(hook_id=long_hook_id)
        settings = create_test_settings({"pre": [{"matcher": "**/*.py", "hooks": [hook_entry]}]})
        write_settings_json(tmp_path, settings)

        # List
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["list"])
        assert result.exit_code == 0
        assert long_hook_id in result.output

        # Show
        result = invoke_in_dir(cli_runner, tmp_path, hook_group, ["show", long_hook_id])
        assert result.exit_code == 0
        assert f"Hook: {long_hook_id}" in result.output
