"""Tests for kit command loading with error isolation and lazy loading."""

from pathlib import Path
from typing import Literal, TypedDict

import click
import pytest

from dot_agent_kit.cli.schema_formatting import (
    format_schema_for_help,
    format_type_for_schema,
    format_typeddict_for_schema,
    is_typeddict,
)
from dot_agent_kit.commands.kit_command.group import (
    LazyKitGroup,
    _load_single_kit_commands,
)
from dot_agent_kit.models.kit import KitCliCommandDefinition, KitManifest

# ============================================================================
# Test TypedDicts for schema formatting tests
# ============================================================================


class SuccessResult(TypedDict):
    """Success result."""

    success: Literal[True]
    value: int


class ErrorResult(TypedDict):
    """Error result."""

    success: Literal[False]
    error: Literal["not_found", "invalid"]
    message: str


class SimpleResult(TypedDict):
    """Simple result with basic types."""

    name: str
    count: int
    enabled: bool
    items: list[str]


# ============================================================================
# Tests for format_type_for_schema
# ============================================================================


def test_format_type_basic_str() -> None:
    """Test formatting basic str type."""
    assert format_type_for_schema(str) == "str"


def test_format_type_basic_int() -> None:
    """Test formatting basic int type."""
    assert format_type_for_schema(int) == "int"


def test_format_type_basic_bool() -> None:
    """Test formatting basic bool type."""
    assert format_type_for_schema(bool) == "bool"


def test_format_type_basic_float() -> None:
    """Test formatting basic float type."""
    assert format_type_for_schema(float) == "float"


def test_format_type_literal_true() -> None:
    """Test formatting Literal[True]."""
    assert format_type_for_schema(Literal[True]) == "true"


def test_format_type_literal_false() -> None:
    """Test formatting Literal[False]."""
    assert format_type_for_schema(Literal[False]) == "false"


def test_format_type_literal_string() -> None:
    """Test formatting Literal with string value."""
    assert format_type_for_schema(Literal["error"]) == '"error"'


def test_format_type_literal_multiple_strings() -> None:
    """Test formatting Literal with multiple string values."""
    result = format_type_for_schema(Literal["not_found", "invalid"])
    assert result == '"not_found" | "invalid"'


def test_format_type_union() -> None:
    """Test formatting Union type."""
    result = format_type_for_schema(str | int)
    assert result == "str | int"


def test_format_type_list() -> None:
    """Test formatting list type."""
    assert format_type_for_schema(list[str]) == "list[str]"


def test_format_type_dict() -> None:
    """Test formatting dict type."""
    assert format_type_for_schema(dict[str, int]) == "dict[str, int]"


# ============================================================================
# Tests for is_typeddict
# ============================================================================


def test_is_typeddict_with_typeddict() -> None:
    """Test is_typeddict returns True for TypedDict."""
    assert is_typeddict(SuccessResult) is True


def test_is_typeddict_with_regular_class() -> None:
    """Test is_typeddict returns False for regular class."""

    class RegularClass:
        pass

    assert is_typeddict(RegularClass) is False


def test_is_typeddict_with_dict() -> None:
    """Test is_typeddict returns False for plain dict."""
    assert is_typeddict(dict) is False


# ============================================================================
# Tests for format_typeddict_for_schema
# ============================================================================


def test_format_typeddict_with_success_true() -> None:
    """Test formatting TypedDict with success=True."""
    lines = format_typeddict_for_schema(SuccessResult)
    assert "  SuccessResult (success=true):" in lines
    assert "    success: true" in lines
    assert "    value: int" in lines


def test_format_typeddict_with_success_false() -> None:
    """Test formatting TypedDict with success=False."""
    lines = format_typeddict_for_schema(ErrorResult)
    assert "  ErrorResult (success=false):" in lines
    assert "    success: false" in lines
    assert '    error: "not_found" | "invalid"' in lines
    assert "    message: str" in lines


def test_format_typeddict_simple() -> None:
    """Test formatting TypedDict without success field."""
    lines = format_typeddict_for_schema(SimpleResult)
    assert "  SimpleResult:" in lines
    assert "    name: str" in lines
    assert "    count: int" in lines
    assert "    enabled: bool" in lines
    assert "    items: list[str]" in lines


# ============================================================================
# Tests for format_schema_for_help
# ============================================================================


def test_format_schema_single_typeddict() -> None:
    """Test formatting schema with single TypedDict."""
    result = format_schema_for_help(SimpleResult)
    assert "Output Schema:" in result
    assert "SimpleResult:" in result
    assert "name: str" in result


def test_format_schema_union_typeddicts() -> None:
    """Test formatting schema with Union of TypedDicts."""
    result = format_schema_for_help(SuccessResult | ErrorResult)
    assert "Output Schema:" in result
    assert "SuccessResult (success=true):" in result
    assert "ErrorResult (success=false):" in result


def test_format_schema_includes_all_fields() -> None:
    """Test that all fields are included in schema output."""
    result = format_schema_for_help(ErrorResult)
    assert "success: false" in result
    assert 'error: "not_found" | "invalid"' in result
    assert "message: str" in result


@pytest.fixture
def valid_manifest() -> KitManifest:
    """Create a valid kit manifest with kit cli commands."""
    return KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        kit_cli_commands=[
            KitCliCommandDefinition(
                name="test-command",
                path="kit_cli_commands/test-kit/test_command.py",
                description="A test command",
            )
        ],
    )


@pytest.fixture
def empty_manifest() -> KitManifest:
    """Create a kit manifest with no kit cli commands."""
    return KitManifest(
        name="empty-kit",
        version="1.0.0",
        description="Empty kit",
        artifacts={},
        kit_cli_commands=[],
    )


@pytest.fixture
def invalid_command_manifest() -> KitManifest:
    """Create a manifest with invalid kit cli command definition."""
    return KitManifest(
        name="invalid-kit",
        version="1.0.0",
        description="Invalid kit",
        artifacts={},
        kit_cli_commands=[
            KitCliCommandDefinition(
                name="INVALID_NAME",  # Uppercase not allowed
                path="kit_cli_commands/invalid-kit/test.py",
                description="Invalid command",
            )
        ],
    )


def test_load_valid_kit(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test loading a valid kit with all commands successfully."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "kit_cli_commands" / "test-kit"
    commands_dir.mkdir(parents=True)

    # Create the command file
    (commands_dir / "test_command.py").write_text(
        """import click

@click.command()
def test_command():
    '''Test command.'''
    click.echo('Hello')
""",
        encoding="utf-8",
    )

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=valid_manifest, debug=False
    )

    assert kit_group is not None
    assert isinstance(kit_group, LazyKitGroup)
    assert kit_group.name == "test-kit"


def test_load_kit_with_invalid_command_name(
    tmp_path: Path, invalid_command_manifest: KitManifest
) -> None:
    """Test loading kit with invalid command name logs error and continues."""
    kit_dir = tmp_path / "invalid-kit"
    kit_dir.mkdir()

    kit_group = _load_single_kit_commands(
        kit_name="invalid-kit",
        kit_dir=kit_dir,
        manifest=invalid_command_manifest,
        debug=False,
    )

    # Kit group is created but commands won't load
    assert kit_group is not None


def test_load_kit_with_missing_file(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test loading kit when command file doesn't exist."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    # Note: NOT creating the commands directory or file

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=valid_manifest, debug=False
    )

    # Kit group is created but command won't load
    assert kit_group is not None


def test_load_kit_with_import_error(tmp_path: Path) -> None:
    """Test loading kit when Python import fails."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "kit_cli_commands" / "test-kit"
    commands_dir.mkdir(parents=True)

    # Create a file with a syntax error
    (commands_dir / "test_command.py").write_text(
        """import click

this is not valid python syntax!!!
""",
        encoding="utf-8",
    )

    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        kit_cli_commands=[
            KitCliCommandDefinition(
                name="test-command",
                path="kit_cli_commands/test-kit/test_command.py",
                description="Test command",
            )
        ],
    )

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    # Kit group is created but command won't load
    assert kit_group is not None


def test_load_kit_with_missing_function(tmp_path: Path) -> None:
    """Test loading kit when function not found in module."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "kit_cli_commands" / "test-kit"
    commands_dir.mkdir(parents=True)

    # Create file without the expected function
    (commands_dir / "test_command.py").write_text(
        """import click

# Missing the test_command function!
""",
        encoding="utf-8",
    )

    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        kit_cli_commands=[
            KitCliCommandDefinition(
                name="test-command",
                path="kit_cli_commands/test-kit/test_command.py",
                description="Test command",
            )
        ],
    )

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    # Kit group is created but command won't load
    assert kit_group is not None


def test_empty_kit_not_registered(tmp_path: Path, empty_manifest: KitManifest) -> None:
    """Test that kits with no commands return None."""
    kit_dir = tmp_path / "empty-kit"
    kit_dir.mkdir()

    kit_group = _load_single_kit_commands(
        kit_name="empty-kit", kit_dir=kit_dir, manifest=empty_manifest, debug=False
    )

    assert kit_group is None


def test_kit_directory_missing(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test loading kit when kit directory doesn't exist."""
    kit_dir = tmp_path / "nonexistent-kit"
    # Note: NOT creating the directory

    kit_group = _load_single_kit_commands(
        kit_name="nonexistent-kit", kit_dir=kit_dir, manifest=valid_manifest, debug=False
    )

    assert kit_group is None


def test_lazy_loading_defers_import(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test that lazy loading doesn't import commands until accessed."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "kit_cli_commands" / "test-kit"
    commands_dir.mkdir(parents=True)

    # Create the command file
    (commands_dir / "test_command.py").write_text(
        """import click

@click.command()
def test_command():
    '''Test command.'''
    click.echo('Hello')
""",
        encoding="utf-8",
    )

    kit_group = LazyKitGroup(
        kit_name="test-kit",
        kit_dir=kit_dir,
        manifest=valid_manifest,
        debug=False,
        name="test-kit",
        help="Test kit",
    )

    # Commands should not be loaded yet
    assert not kit_group._loaded

    # Create a mock context
    ctx = click.Context(click.Command("test"))
    ctx.obj = {"debug": False}

    # Access commands - this triggers loading
    kit_group.list_commands(ctx)

    # Now commands should be loaded
    assert kit_group._loaded


def test_debug_flag_shows_traceback(tmp_path: Path) -> None:
    """Test that debug mode shows full traceback on errors."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()

    # Create manifest with invalid command
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        kit_cli_commands=[
            KitCliCommandDefinition(
                name="INVALID",  # Invalid name
                path="kit_cli_commands/test-kit/test.py",
                description="Test",
            )
        ],
    )

    kit_group = LazyKitGroup(
        kit_name="test-kit",
        kit_dir=kit_dir,
        manifest=manifest,
        debug=True,
        name="test-kit",
        help="Test kit",
    )

    ctx = click.Context(click.Command("test"))
    ctx.obj = {"debug": True}

    # In debug mode, validation errors should raise
    with pytest.raises(click.ClickException):
        kit_group._load_commands(ctx)


def test_path_construction_simple(tmp_path: Path) -> None:
    """Test path construction for simple single-level path."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "kit_cli_commands" / "test-kit"
    commands_dir.mkdir(parents=True)

    (commands_dir / "simple.py").write_text(
        """import click

@click.command()
def simple():
    '''Simple command.'''
    pass
""",
        encoding="utf-8",
    )

    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        kit_cli_commands=[
            KitCliCommandDefinition(
                name="simple",
                path="kit_cli_commands/test-kit/simple.py",
                description="Simple command",
            )
        ],
    )

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    assert kit_group is not None


def test_path_construction_nested(tmp_path: Path) -> None:
    """Test path construction for nested multi-level path."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    nested_dir = kit_dir / "kit_cli_commands" / "test-kit" / "a" / "b" / "c"
    nested_dir.mkdir(parents=True)

    (nested_dir / "nested.py").write_text(
        """import click

@click.command()
def nested():
    '''Nested command.'''
    pass
""",
        encoding="utf-8",
    )

    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        kit_cli_commands=[
            KitCliCommandDefinition(
                name="nested",
                path="kit_cli_commands/test-kit/a/b/c/nested.py",
                description="Nested command",
            )
        ],
    )

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    assert kit_group is not None


def test_all_commands_fail_to_load_shows_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Test that warning is shown when all commands fail to load."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "kit_cli_commands" / "test-kit"
    commands_dir.mkdir(parents=True)

    # Create file without the expected function
    (commands_dir / "broken_command.py").write_text(
        """import click

# Missing the broken_command function!
""",
        encoding="utf-8",
    )

    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        kit_cli_commands=[
            KitCliCommandDefinition(
                name="broken-command",
                path="kit_cli_commands/test-kit/broken_command.py",
                description="Broken command",
            )
        ],
    )

    kit_group = LazyKitGroup(
        kit_name="test-kit",
        kit_dir=kit_dir,
        manifest=manifest,
        debug=False,
        name="test-kit",
        help="Test kit",
    )

    ctx = click.Context(click.Command("test"))
    ctx.obj = {"debug": False}

    # Trigger lazy loading
    kit_group.list_commands(ctx)

    # Verify warning was shown
    captured = capsys.readouterr()
    assert "loaded 0 commands" in captured.err
    assert "all 1 command(s) failed to load" in captured.err


def test_kit_discovery_isolates_manifest_parse_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that manifest parse errors don't prevent other kits from loading."""
    from dot_agent_kit.commands.kit_command.group import (
        _load_kit_commands,
        kit_command_group,
    )

    # Create a mock BundledKitSource that returns two kits
    class MockSource:
        def list_available(self) -> list[str]:
            return ["good-kit", "bad-kit"]

    # Create kit directories
    kits_dir = tmp_path / "kits"
    kits_dir.mkdir()

    good_kit_dir = kits_dir / "good-kit"
    good_kit_dir.mkdir()
    bad_kit_dir = kits_dir / "bad-kit"
    bad_kit_dir.mkdir()

    # Good kit with valid manifest and command
    (good_kit_dir / "kit.yaml").write_text(
        """name: good-kit
version: 1.0.0
description: Good kit
kit_cli_commands:
  - name: good-command
    path: kit_cli_commands/good-kit/good.py
    description: Good command
""",
        encoding="utf-8",
    )
    good_commands_dir = good_kit_dir / "kit_cli_commands" / "good-kit"
    good_commands_dir.mkdir(parents=True)
    (good_commands_dir / "good.py").write_text(
        """import click

@click.command()
def good_command():
    '''Good command.'''
    click.echo('Good')
""",
        encoding="utf-8",
    )

    # Bad kit with invalid YAML (will cause parse error)
    (bad_kit_dir / "kit.yaml").write_text(
        """name: bad-kit
version: 1.0.0
description: Bad kit
kit_cli_commands:
  - this is not valid YAML syntax!!!
    invalid indentation here
""",
        encoding="utf-8",
    )

    # Monkeypatch the module to use our test directory
    from dot_agent_kit.commands.kit_command import group as group_module

    monkeypatch.setattr(group_module, "BundledKitSource", MockSource)
    monkeypatch.setattr(group_module, "KITS_DATA_DIR", kits_dir)

    # Clear any previously loaded commands
    kit_command_group.commands.clear()

    # This should not raise - bad kit should be isolated
    _load_kit_commands()

    # Good kit should have been loaded despite bad kit failure
    assert "good-kit" in kit_command_group.commands
    assert "bad-kit" not in kit_command_group.commands


def test_kit_discovery_isolates_add_command_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that errors from add_command don't prevent other kits from loading."""
    from dot_agent_kit.commands.kit_command.group import _load_kit_commands, kit_command_group

    # Create kit directories
    kits_dir = tmp_path / "kits"
    kits_dir.mkdir()

    kit1_dir = kits_dir / "kit1"
    kit1_dir.mkdir()
    kit2_dir = kits_dir / "kit2"
    kit2_dir.mkdir()

    # Both kits have valid manifests
    for kit_name, kit_dir in [("kit1", kit1_dir), ("kit2", kit2_dir)]:
        (kit_dir / "kit.yaml").write_text(
            f"""name: {kit_name}
version: 1.0.0
description: Test kit {kit_name}
kit_cli_commands:
  - name: test-command
    path: kit_cli_commands/{kit_name}/test.py
    description: Test command
""",
            encoding="utf-8",
        )
        commands_dir = kit_dir / "kit_cli_commands" / kit_name
        commands_dir.mkdir(parents=True)
        (commands_dir / "test.py").write_text(
            """import click

@click.command()
def test_command():
    '''Test command.'''
    click.echo('Test')
""",
            encoding="utf-8",
        )

    # Mock BundledKitSource
    class MockSource:
        def list_available(self) -> list[str]:
            return ["kit1", "kit2"]

    # Monkeypatch
    from dot_agent_kit.commands.kit_command import group as group_module

    monkeypatch.setattr(group_module, "BundledKitSource", MockSource)
    monkeypatch.setattr(group_module, "KITS_DATA_DIR", kits_dir)

    # Simulate add_command failure for kit1
    original_add_command = kit_command_group.add_command
    call_count = [0]

    def failing_add_command(cmd: click.Command) -> None:
        call_count[0] += 1
        if call_count[0] == 1:
            # First call fails (kit1)
            raise click.ClickException("Name conflict")
        # Second call succeeds (kit2)
        original_add_command(cmd)

    monkeypatch.setattr(kit_command_group, "add_command", failing_add_command)

    # Clear any previously loaded commands
    kit_command_group.commands.clear()

    # This should not raise - kit1 failure should be isolated
    _load_kit_commands()

    # kit2 should have been loaded despite kit1 failure
    assert "kit2" in kit_command_group.commands
