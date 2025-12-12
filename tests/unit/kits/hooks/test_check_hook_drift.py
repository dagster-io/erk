"""Tests for hook configuration drift detection."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.kit.check import (
    InstalledHook,
    _detect_hook_drift,
    _extract_hooks_for_kit,
    check,
)
from erk.kits.hooks.models import ClaudeSettings, HookDefinition, HookEntry, MatcherGroup
from erk.kits.io.state import save_project_config
from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.sources.bundled import BundledKitSource


def test_extract_hooks_for_kit_filters_correctly() -> None:
    """Test that _extract_hooks_for_kit only returns hooks for specified kit."""
    # Create settings with hooks from multiple kits
    settings = ClaudeSettings(
        hooks={
            "UserPromptSubmit": [
                MatcherGroup(
                    matcher="*",
                    hooks=[
                        HookEntry(
                            command=(
                                "ERK_KIT_ID=dignified-python "
                                "ERK_HOOK_ID=my-hook python3 /path/to/script.py"
                            ),
                            timeout=30,
                        ),
                        HookEntry(
                            command=(
                                "ERK_KIT_ID=other-kit "
                                "ERK_HOOK_ID=other-hook python3 /path/to/other.py"
                            ),
                            timeout=30,
                        ),
                    ],
                )
            ]
        }
    )

    # Create expected hooks for dignified-python
    expected_hooks = [
        HookDefinition(
            id="my-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="python3 /path/to/script.py",
            description="Test hook",
            timeout=30,
        )
    ]

    # Extract hooks for dignified-python
    hooks = _extract_hooks_for_kit(settings, "dignified-python", expected_hooks)

    assert len(hooks) == 1
    assert hooks[0].hook_id == "my-hook"
    assert "dignified-python" in hooks[0].command


def test_extract_hooks_for_kit_empty_settings() -> None:
    """Test _extract_hooks_for_kit with empty settings."""
    settings = ClaudeSettings()

    # Empty expected hooks is fine when no hooks are installed
    expected_hooks: list[HookDefinition] = []

    hooks = _extract_hooks_for_kit(settings, "any-kit", expected_hooks)

    assert len(hooks) == 0


def test_extract_hooks_for_kit_no_matching_kit() -> None:
    """Test _extract_hooks_for_kit when kit not found."""
    settings = ClaudeSettings(
        hooks={
            "UserPromptSubmit": [
                MatcherGroup(
                    matcher="*",
                    hooks=[
                        HookEntry(
                            command="ERK_KIT_ID=other-kit python3 /path/to/script.py",
                            timeout=30,
                        ),
                    ],
                )
            ]
        }
    )

    # Empty expected hooks is fine when no hooks match the kit
    expected_hooks: list[HookDefinition] = []

    hooks = _extract_hooks_for_kit(settings, "dignified-python", expected_hooks)

    assert len(hooks) == 0


def test_extract_hooks_invalid_format_uppercase() -> None:
    """Test that _extract_hooks_for_kit rejects hook IDs with uppercase letters."""
    settings = ClaudeSettings(
        hooks={
            "UserPromptSubmit": [
                MatcherGroup(
                    matcher="*",
                    hooks=[
                        HookEntry(
                            command=(
                                "ERK_KIT_ID=test-kit "
                                "ERK_HOOK_ID=Invalid-Hook python3 /path/to/script.py"
                            ),
                            timeout=30,
                        ),
                    ],
                )
            ]
        }
    )

    expected_hooks = [
        HookDefinition(
            id="valid-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="python3 /path/to/script.py",
            description="Test hook",
            timeout=30,
        )
    ]

    try:
        _extract_hooks_for_kit(settings, "test-kit", expected_hooks)
        raise AssertionError("Expected ValueError for uppercase in hook ID")
    except ValueError as e:
        assert "Invalid hook ID format" in str(e)
        assert "Invalid-Hook" in str(e)
        assert "^[a-z0-9-]+$" in str(e)


def test_extract_hooks_invalid_format_spaces() -> None:
    """Test that _extract_hooks_for_kit rejects hook IDs with spaces."""
    settings = ClaudeSettings(
        hooks={
            "UserPromptSubmit": [
                MatcherGroup(
                    matcher="*",
                    hooks=[
                        HookEntry(
                            command=(
                                "ERK_KIT_ID=test-kit ERK_HOOK_ID=my hook python3 /path/to/script.py"
                            ),
                            timeout=30,
                        ),
                    ],
                )
            ]
        }
    )

    expected_hooks = [
        HookDefinition(
            id="valid-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="python3 /path/to/script.py",
            description="Test hook",
            timeout=30,
        )
    ]

    try:
        _extract_hooks_for_kit(settings, "test-kit", expected_hooks)
        raise AssertionError("Expected ValueError for spaces in hook ID")
    except ValueError as e:
        # The regex \S+ stops at the space, extracting just "my"
        # This is then validated against the manifest (not found error)
        assert "not found in manifest" in str(e) or "Invalid hook ID format" in str(e)


def test_extract_hooks_invalid_format_special_chars() -> None:
    """Test that _extract_hooks_for_kit rejects hook IDs with special characters."""
    settings = ClaudeSettings(
        hooks={
            "UserPromptSubmit": [
                MatcherGroup(
                    matcher="*",
                    hooks=[
                        HookEntry(
                            command=(
                                "ERK_KIT_ID=test-kit "
                                "ERK_HOOK_ID=my@hook! python3 /path/to/script.py"
                            ),
                            timeout=30,
                        ),
                    ],
                )
            ]
        }
    )

    expected_hooks = [
        HookDefinition(
            id="valid-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="python3 /path/to/script.py",
            description="Test hook",
            timeout=30,
        )
    ]

    try:
        _extract_hooks_for_kit(settings, "test-kit", expected_hooks)
        raise AssertionError("Expected ValueError for special characters in hook ID")
    except ValueError as e:
        assert "Invalid hook ID format" in str(e)
        assert "my@hook!" in str(e)


def test_extract_hooks_id_not_in_manifest() -> None:
    """Test that _extract_hooks_for_kit rejects hook IDs not in manifest."""
    settings = ClaudeSettings(
        hooks={
            "UserPromptSubmit": [
                MatcherGroup(
                    matcher="*",
                    hooks=[
                        HookEntry(
                            command=(
                                "ERK_KIT_ID=test-kit "
                                "ERK_HOOK_ID=unknown-hook python3 /path/to/script.py"
                            ),
                            timeout=30,
                        ),
                    ],
                )
            ]
        }
    )

    expected_hooks = [
        HookDefinition(
            id="valid-hook-1",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="python3 /path/to/script.py",
            description="Test hook 1",
            timeout=30,
        ),
        HookDefinition(
            id="valid-hook-2",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="python3 /path/to/script.py",
            description="Test hook 2",
            timeout=30,
        ),
    ]

    try:
        _extract_hooks_for_kit(settings, "test-kit", expected_hooks)
        raise AssertionError("Expected ValueError for hook ID not in manifest")
    except ValueError as e:
        assert "not found in manifest" in str(e)
        assert "unknown-hook" in str(e)
        assert "'valid-hook-1'" in str(e)
        assert "'valid-hook-2'" in str(e)


def test_extract_hooks_empty_manifest_with_hooks() -> None:
    """Test extracting hooks when expected_hooks is empty list."""
    settings = ClaudeSettings(
        hooks={
            "UserPromptSubmit": [
                MatcherGroup(
                    matcher="*",
                    hooks=[
                        HookEntry(
                            command=(
                                "ERK_KIT_ID=test-kit "
                                "ERK_HOOK_ID=some-hook python3 /path/to/script.py"
                            ),
                            timeout=30,
                        ),
                    ],
                )
            ]
        }
    )

    expected_hooks: list[HookDefinition] = []

    try:
        _extract_hooks_for_kit(settings, "test-kit", expected_hooks)
        raise AssertionError("Expected ValueError when hooks found but none expected")
    except ValueError as e:
        assert "not found in manifest" in str(e)
        assert "some-hook" in str(e)


def test_detect_hook_drift_no_drift() -> None:
    """Test _detect_hook_drift when hooks match expectations."""
    expected_hooks = [
        HookDefinition(
            id="compliance-reminder-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run dignified-python compliance-reminder-hook",
            description="Test hook",
            timeout=30,
        )
    ]

    installed_hooks = [
        InstalledHook(
            hook_id="compliance-reminder-hook",
            command=(
                "ERK_KIT_ID=dignified-python "
                "ERK_HOOK_ID=compliance-reminder-hook "
                "dot-agent run dignified-python compliance-reminder-hook"
            ),
            timeout=30,
            lifecycle="UserPromptSubmit",
            matcher="*",
        )
    ]

    result = _detect_hook_drift("dignified-python", expected_hooks, installed_hooks)

    assert result is None


def test_detect_hook_drift_missing_hook() -> None:
    """Test _detect_hook_drift detects missing hook."""
    expected_hooks = [
        HookDefinition(
            id="compliance-reminder-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run dignified-python compliance-reminder-hook",
            description="Test hook",
            timeout=30,
        )
    ]

    installed_hooks: list[InstalledHook] = []

    result = _detect_hook_drift("dignified-python", expected_hooks, installed_hooks)

    assert result is not None
    assert len(result.issues) == 1
    assert result.issues[0].severity == "error"
    assert "Missing hook" in result.issues[0].message
    assert result.issues[0].expected == "compliance-reminder-hook"


def test_detect_hook_drift_outdated_command_format() -> None:
    """Test _detect_hook_drift detects outdated command format."""
    expected_hooks = [
        HookDefinition(
            id="compliance-reminder-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run dignified-python compliance-reminder-hook",
            description="Test hook",
            timeout=30,
        )
    ]

    installed_hooks = [
        InstalledHook(
            hook_id="compliance-reminder-hook",
            command="ERK_KIT_ID=dignified-python python3 /path/to/script.py",
            timeout=30,
            lifecycle="UserPromptSubmit",
            matcher="*",
        )
    ]

    result = _detect_hook_drift("dignified-python", expected_hooks, installed_hooks)

    assert result is not None
    assert len(result.issues) == 1
    assert result.issues[0].severity == "warning"
    assert "Command mismatch" in result.issues[0].message


def test_detect_hook_drift_obsolete_hook() -> None:
    """Test _detect_hook_drift detects obsolete hook."""
    expected_hooks: list[HookDefinition] = []

    installed_hooks = [
        InstalledHook(
            hook_id="old-hook",
            command="ERK_KIT_ID=dignified-python python3 /path/to/old.py",
            timeout=30,
            lifecycle="UserPromptSubmit",
            matcher="*",
        )
    ]

    result = _detect_hook_drift("dignified-python", expected_hooks, installed_hooks)

    assert result is not None
    assert len(result.issues) == 1
    assert result.issues[0].severity == "warning"
    assert "Obsolete hook" in result.issues[0].message


def test_detect_hook_drift_hook_id_mismatch() -> None:
    """Test _detect_hook_drift detects hook ID mismatch (old vs new ID)."""
    expected_hooks = [
        HookDefinition(
            id="compliance-reminder-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run dignified-python compliance-reminder-hook",
            description="Test hook",
            timeout=30,
        )
    ]

    # Installed hook has old ID
    installed_hooks = [
        InstalledHook(
            hook_id="suggest-dignified-python",
            command="ERK_KIT_ID=dignified-python python3 /path/to/script.py",
            timeout=30,
            lifecycle="UserPromptSubmit",
            matcher="*",
        )
    ]

    result = _detect_hook_drift("dignified-python", expected_hooks, installed_hooks)

    assert result is not None
    # Should detect missing (new ID) and obsolete (old ID)
    assert len(result.issues) == 2
    assert any("Missing hook" in issue.message for issue in result.issues)
    assert any("Obsolete hook" in issue.message for issue in result.issues)


def test_detect_hook_drift_multiple_issues() -> None:
    """Test _detect_hook_drift with multiple drift issues."""
    expected_hooks = [
        HookDefinition(
            id="hook-1",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run test-kit hook-1",
            description="Hook 1",
            timeout=30,
        ),
        HookDefinition(
            id="hook-2",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run test-kit hook-2",
            description="Hook 2",
            timeout=30,
        ),
    ]

    installed_hooks = [
        InstalledHook(
            hook_id="hook-1",
            command="ERK_KIT_ID=test-kit python3 /path/to/hook1.py",
            timeout=30,
            lifecycle="UserPromptSubmit",
            matcher="*",
        ),
        InstalledHook(
            hook_id="old-hook",
            command="ERK_KIT_ID=test-kit python3 /path/to/old.py",
            timeout=30,
            lifecycle="UserPromptSubmit",
            matcher="*",
        ),
    ]

    result = _detect_hook_drift("test-kit", expected_hooks, installed_hooks)

    assert result is not None
    # Missing hook-2, outdated format for hook-1, obsolete old-hook
    assert len(result.issues) == 3


def test_check_command_no_hook_drift(tmp_path: Path) -> None:
    """Test check command when no hook drift detected."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create settings.json with no hooks
        settings_path = claude_dir / "settings.json"
        settings_path.write_text("{}", encoding="utf-8")

        # Create kit.yaml artifact file
        kit_yaml_path = claude_dir / "kit.yaml"
        kit_yaml_path.write_text("name: test-kit\nversion: 1.0.0\n", encoding="utf-8")

        # Create config with bundled kit
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    artifacts=[".claude/kit.yaml"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check, ["--verbose"])

        assert result.exit_code == 0
        assert "All checks passed" in result.output


def test_check_command_skip_non_bundled_kits(tmp_path: Path) -> None:
    """Test check command skips non-bundled kits for hook validation."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create settings.json with hook for non-bundled kit
        settings_data = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "command": ("ERK_KIT_ID=package-kit python3 /path/to/script.py"),
                                "timeout": 30,
                            }
                        ],
                    }
                ]
            }
        }
        settings_path = claude_dir / "settings.json"
        settings_path.write_text(json.dumps(settings_data), encoding="utf-8")

        # Create kit.yaml artifact file
        kit_yaml_path = claude_dir / "kit.yaml"
        kit_yaml_path.write_text("name: package-kit\nversion: 1.0.0\n", encoding="utf-8")

        # Create config with package kit (not bundled)
        config = ProjectConfig(
            version="1",
            kits={
                "package-kit": InstalledKit(
                    kit_id="package-kit",
                    version="1.0.0",
                    source_type="package",
                    artifacts=[".claude/kit.yaml"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check, ["--verbose"])

        # Should pass - non-bundled kits are skipped
        assert result.exit_code == 0
        assert "All checks passed" in result.output


def test_check_command_skip_kit_without_hooks_field(tmp_path: Path) -> None:
    """Test check command skips kits with no hooks field in manifest."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create settings.json
        settings_path = claude_dir / "settings.json"
        settings_path.write_text("{}", encoding="utf-8")

        # Create a mock bundled kit without hooks field
        mock_kit_dir = tmp_path / "mock_bundled_kit"
        mock_kit_dir.mkdir()

        manifest_content = """name: test-kit
version: 1.0.0
description: Test kit
artifacts:
  command:
  - commands/kit.yaml
"""

        manifest_path = mock_kit_dir / "kit.yaml"
        manifest_path.write_text(manifest_content, encoding="utf-8")

        # Create bundled artifact file
        bundled_commands_dir = mock_kit_dir / "commands"
        bundled_commands_dir.mkdir()
        (bundled_commands_dir / "kit.yaml").write_text(manifest_content, encoding="utf-8")

        # Create local artifact file (must match bundled for sync check to pass)
        local_commands_dir = claude_dir / "commands"
        local_commands_dir.mkdir()
        (local_commands_dir / "kit.yaml").write_text(manifest_content, encoding="utf-8")

        # Create config
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    artifacts=[".claude/commands/kit.yaml"],
                ),
            },
        )
        save_project_config(project_dir, config)

        # Monkey patch BundledKitSource
        original_get_path = BundledKitSource._get_bundled_kit_path

        def mock_get_path(self: BundledKitSource, source: str) -> Path | None:
            if source == "test-kit":
                return mock_kit_dir
            return original_get_path(self, source)

        BundledKitSource._get_bundled_kit_path = mock_get_path

        result = runner.invoke(check, ["--verbose"])

        # Restore original method
        BundledKitSource._get_bundled_kit_path = original_get_path

        # Should pass - kits without hooks field are skipped
        assert result.exit_code == 0
        assert "All checks passed" in result.output


def test_check_command_detects_hook_drift_integration(tmp_path: Path) -> None:
    """Integration test: check command detects actual hook drift."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create settings.json with old hook reference
        settings_data = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "command": (
                                    "ERK_KIT_ID=test-kit "
                                    "ERK_HOOK_ID=old-hook python3 /path/to/old_hook.py"
                                ),
                                "timeout": 30,
                            }
                        ],
                    }
                ]
            }
        }
        settings_path = claude_dir / "settings.json"
        settings_path.write_text(json.dumps(settings_data), encoding="utf-8")

        # Create a mock bundled kit with hooks field
        mock_kit_dir = tmp_path / "mock_bundled_kit"
        mock_kit_dir.mkdir()

        manifest_path = mock_kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: test-kit
version: 1.0.0
description: Test kit
artifacts: {}
hooks:
  - id: new-hook
    lifecycle: UserPromptSubmit
    matcher: "*"
    invocation: dot-agent run test-kit new-hook
    description: New hook
    timeout: 30
""",
            encoding="utf-8",
        )

        # Create config
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    artifacts=[],
                ),
            },
        )
        save_project_config(project_dir, config)

        # Monkey patch BundledKitSource
        original_get_path = BundledKitSource._get_bundled_kit_path

        def mock_get_path(self: BundledKitSource, source: str) -> Path | None:
            if source == "test-kit":
                return mock_kit_dir
            return original_get_path(self, source)

        BundledKitSource._get_bundled_kit_path = mock_get_path

        result = runner.invoke(check, ["--verbose"])

        # Restore original method
        BundledKitSource._get_bundled_kit_path = original_get_path

        # Should detect drift
        assert result.exit_code == 1
        assert "test-kit" in result.output
        # Extraction fails because old-hook is not in manifest (only new-hook is expected)
        assert "not found in manifest" in result.output or "Some checks failed" in result.output


def test_check_command_no_settings_file(tmp_path: Path) -> None:
    """Test check command when settings.json doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory but no settings.json
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create kit.yaml artifact file
        kit_yaml_path = claude_dir / "kit.yaml"
        kit_yaml_path.write_text("name: test-kit\nversion: 1.0.0\n", encoding="utf-8")

        # Create config with bundled kit
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    artifacts=[".claude/kit.yaml"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check, ["--verbose"])

        # Should pass - no settings.json means no hooks to validate
        assert result.exit_code == 0
        assert "All checks passed" in result.output


def test_detect_hook_drift_matcher_mismatch() -> None:
    """Test _detect_hook_drift detects matcher field mismatch."""
    expected_hooks = [
        HookDefinition(
            id="compliance-hook",
            lifecycle="UserPromptSubmit",
            matcher="*.py",
            invocation="dot-agent run test-kit compliance-hook",
            description="Test hook",
            timeout=30,
        )
    ]

    installed_hooks = [
        InstalledHook(
            hook_id="compliance-hook",
            command=(
                "ERK_KIT_ID=test-kit "
                "ERK_HOOK_ID=compliance-hook "
                "dot-agent run test-kit compliance-hook"
            ),
            timeout=30,
            lifecycle="UserPromptSubmit",
            matcher="*",
        )
    ]

    result = _detect_hook_drift("test-kit", expected_hooks, installed_hooks)

    assert result is not None
    assert len(result.issues) == 1
    assert result.issues[0].severity == "warning"
    assert "Matcher mismatch" in result.issues[0].message
    assert result.issues[0].expected == "*.py"
    assert result.issues[0].actual == "*"


def test_detect_hook_drift_matcher_none_normalized() -> None:
    """Test _detect_hook_drift normalizes None matcher to '*'."""
    expected_hooks = [
        HookDefinition(
            id="compliance-hook",
            lifecycle="UserPromptSubmit",
            matcher=None,
            invocation="dot-agent run test-kit compliance-hook",
            description="Test hook",
            timeout=30,
        )
    ]

    installed_hooks = [
        InstalledHook(
            hook_id="compliance-hook",
            command=(
                "ERK_KIT_ID=test-kit "
                "ERK_HOOK_ID=compliance-hook "
                "dot-agent run test-kit compliance-hook"
            ),
            timeout=30,
            lifecycle="UserPromptSubmit",
            matcher="*",
        )
    ]

    result = _detect_hook_drift("test-kit", expected_hooks, installed_hooks)

    # Should have no drift - None is normalized to "*"
    assert result is None


def test_check_command_detects_matcher_drift(tmp_path: Path) -> None:
    """Integration test: check command detects matcher drift and doesn't fail."""
    runner = CliRunner()
    # SAFETY: isolated_filesystem creates a temporary directory for this test
    # All file operations below are isolated and won't affect real project files
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # SAFE: Path.cwd() here returns the isolated temp directory, not real CWD
        project_dir = Path.cwd()

        # SAFE: Creating directories in isolated temp filesystem only
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create settings.json with matcher="*"
        settings_data = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "command": (
                                    "ERK_KIT_ID=test-kit "
                                    "ERK_HOOK_ID=compliance-hook "
                                    "dot-agent run test-kit compliance-hook"
                                ),
                                "timeout": 30,
                            }
                        ],
                    }
                ]
            }
        }
        settings_path = claude_dir / "settings.json"
        # SAFE: Writing to isolated temp directory only
        settings_path.write_text(json.dumps(settings_data), encoding="utf-8")

        # Create a mock bundled kit with matcher="*.py" in hooks field
        # SAFE: tmp_path is a pytest fixture providing isolated temp directory
        mock_kit_dir = tmp_path / "mock_bundled_kit"
        mock_kit_dir.mkdir()

        manifest_path = mock_kit_dir / "kit.yaml"
        # SAFE: Writing to isolated temp directory only
        manifest_path.write_text(
            """name: test-kit
version: 1.0.0
description: Test kit
artifacts: {}
hooks:
  - id: compliance-hook
    lifecycle: UserPromptSubmit
    matcher: "*.py"
    invocation: dot-agent run test-kit compliance-hook
    description: Compliance hook
    timeout: 30
""",
            encoding="utf-8",
        )

        # Create config
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    artifacts=[],
                ),
            },
        )
        # SAFE: save_project_config writes to project_dir which is isolated temp directory
        # This creates dot-agent.toml in the temp directory, not real project
        save_project_config(project_dir, config)

        # Monkey patch BundledKitSource
        original_get_path = BundledKitSource._get_bundled_kit_path

        def mock_get_path(self: BundledKitSource, source: str) -> Path | None:
            if source == "test-kit":
                return mock_kit_dir
            return original_get_path(self, source)

        BundledKitSource._get_bundled_kit_path = mock_get_path

        result = runner.invoke(check, ["--verbose"])

        # Restore original method
        BundledKitSource._get_bundled_kit_path = original_get_path

        # Matcher mismatch is a warning, check should fail
        assert result.exit_code == 1
        assert "test-kit" in result.output
        assert "Matcher mismatch" in result.output
        assert "*.py" in result.output
        assert "*" in result.output
        assert "Some checks failed" in result.output
