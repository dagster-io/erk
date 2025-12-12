"""Tests for kit script loading with error isolation and lazy loading."""

from pathlib import Path

import click
import pytest

from erk.cli.commands.kit_exec.group import (
    LazyKitGroup,
    _load_single_kit_scripts,
)
from erk.kits.models.kit import KitManifest, ScriptDefinition


@pytest.fixture
def valid_manifest() -> KitManifest:
    """Create a valid kit manifest with scripts."""
    return KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        scripts=[
            ScriptDefinition(
                name="test-command",
                path="scripts/test-kit/test_command.py",
                description="A test command",
            )
        ],
    )


@pytest.fixture
def empty_manifest() -> KitManifest:
    """Create a kit manifest with no scripts."""
    return KitManifest(
        name="empty-kit",
        version="1.0.0",
        description="Empty kit",
        artifacts={},
        scripts=[],
    )


@pytest.fixture
def invalid_script_manifest() -> KitManifest:
    """Create a manifest with invalid script definition."""
    return KitManifest(
        name="invalid-kit",
        version="1.0.0",
        description="Invalid kit",
        artifacts={},
        scripts=[
            ScriptDefinition(
                name="INVALID_NAME",  # Uppercase not allowed
                path="scripts/invalid-kit/test.py",
                description="Invalid script",
            )
        ],
    )


def test_load_valid_kit(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test loading a valid kit with all scripts successfully."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    scripts_dir = kit_dir / "scripts" / "test-kit"
    scripts_dir.mkdir(parents=True)

    # Create the script file
    (scripts_dir / "test_command.py").write_text(
        """import click

@click.command()
def test_command():
    '''Test command.'''
    click.echo('Hello')
""",
        encoding="utf-8",
    )

    kit_group = _load_single_kit_scripts(
        kit_name="test-kit", kit_dir=kit_dir, manifest=valid_manifest, debug=False
    )

    assert kit_group is not None
    assert isinstance(kit_group, LazyKitGroup)
    assert kit_group.name == "test-kit"


def test_load_kit_with_invalid_script_name(
    tmp_path: Path, invalid_script_manifest: KitManifest
) -> None:
    """Test loading kit with invalid script name logs error and continues."""
    kit_dir = tmp_path / "invalid-kit"
    kit_dir.mkdir()

    kit_group = _load_single_kit_scripts(
        kit_name="invalid-kit",
        kit_dir=kit_dir,
        manifest=invalid_script_manifest,
        debug=False,
    )

    # Kit group is created but scripts won't load
    assert kit_group is not None


def test_load_kit_with_missing_file(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test loading kit when script file doesn't exist."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    # Note: NOT creating the scripts directory or file

    kit_group = _load_single_kit_scripts(
        kit_name="test-kit", kit_dir=kit_dir, manifest=valid_manifest, debug=False
    )

    # Kit group is created but script won't load
    assert kit_group is not None


def test_load_kit_with_import_error(tmp_path: Path) -> None:
    """Test loading kit when Python import fails."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    scripts_dir = kit_dir / "scripts" / "test-kit"
    scripts_dir.mkdir(parents=True)

    # Create a file with a syntax error
    (scripts_dir / "test_command.py").write_text(
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
        scripts=[
            ScriptDefinition(
                name="test-command",
                path="scripts/test-kit/test_command.py",
                description="Test script",
            )
        ],
    )

    kit_group = _load_single_kit_scripts(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    # Kit group is created but script won't load
    assert kit_group is not None


def test_load_kit_with_missing_function(tmp_path: Path) -> None:
    """Test loading kit when function not found in module."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    scripts_dir = kit_dir / "scripts" / "test-kit"
    scripts_dir.mkdir(parents=True)

    # Create file without the expected function
    (scripts_dir / "test_command.py").write_text(
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
        scripts=[
            ScriptDefinition(
                name="test-command",
                path="scripts/test-kit/test_command.py",
                description="Test script",
            )
        ],
    )

    kit_group = _load_single_kit_scripts(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    # Kit group is created but script won't load
    assert kit_group is not None


def test_empty_kit_not_registered(tmp_path: Path, empty_manifest: KitManifest) -> None:
    """Test that kits with no scripts return None."""
    kit_dir = tmp_path / "empty-kit"
    kit_dir.mkdir()

    kit_group = _load_single_kit_scripts(
        kit_name="empty-kit", kit_dir=kit_dir, manifest=empty_manifest, debug=False
    )

    assert kit_group is None


def test_kit_directory_missing(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test loading kit when kit directory doesn't exist."""
    kit_dir = tmp_path / "nonexistent-kit"
    # Note: NOT creating the directory

    kit_group = _load_single_kit_scripts(
        kit_name="nonexistent-kit", kit_dir=kit_dir, manifest=valid_manifest, debug=False
    )

    assert kit_group is None


def test_lazy_loading_defers_import(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test that lazy loading doesn't import scripts until accessed."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    scripts_dir = kit_dir / "scripts" / "test-kit"
    scripts_dir.mkdir(parents=True)

    # Create the script file
    (scripts_dir / "test_command.py").write_text(
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

    # Scripts should not be loaded yet
    assert not kit_group._loaded

    # Create a mock context
    ctx = click.Context(click.Command("test"))
    ctx.obj = {"debug": False}

    # Access scripts - this triggers loading
    kit_group.list_commands(ctx)

    # Now scripts should be loaded
    assert kit_group._loaded


def test_debug_flag_shows_traceback(tmp_path: Path) -> None:
    """Test that debug mode shows full traceback on errors."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()

    # Create manifest with invalid script
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        scripts=[
            ScriptDefinition(
                name="INVALID",  # Invalid name
                path="scripts/test-kit/test.py",
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
        kit_group._load_scripts(ctx)


def test_path_construction_simple(tmp_path: Path) -> None:
    """Test path construction for simple single-level path."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    scripts_dir = kit_dir / "scripts" / "test-kit"
    scripts_dir.mkdir(parents=True)

    (scripts_dir / "simple.py").write_text(
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
        scripts=[
            ScriptDefinition(
                name="simple",
                path="scripts/test-kit/simple.py",
                description="Simple script",
            )
        ],
    )

    kit_group = _load_single_kit_scripts(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    assert kit_group is not None


def test_path_construction_nested(tmp_path: Path) -> None:
    """Test path construction for nested multi-level path."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    nested_dir = kit_dir / "scripts" / "test-kit" / "a" / "b" / "c"
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
        scripts=[
            ScriptDefinition(
                name="nested",
                path="scripts/test-kit/a/b/c/nested.py",
                description="Nested script",
            )
        ],
    )

    kit_group = _load_single_kit_scripts(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    assert kit_group is not None


def test_all_scripts_fail_to_load_shows_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Test that warning is shown when all scripts fail to load."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    scripts_dir = kit_dir / "scripts" / "test-kit"
    scripts_dir.mkdir(parents=True)

    # Create file without the expected function
    (scripts_dir / "broken_command.py").write_text(
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
        scripts=[
            ScriptDefinition(
                name="broken-command",
                path="scripts/test-kit/broken_command.py",
                description="Broken script",
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
    assert "loaded 0 scripts" in captured.err
    assert "all 1 script(s) failed to load" in captured.err


def test_kit_discovery_isolates_manifest_parse_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that manifest parse errors don't prevent other kits from loading."""
    from erk.cli.commands.kit_exec.group import (
        _load_kit_scripts,
        kit_exec_group,
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

    # Good kit with valid manifest and script
    (good_kit_dir / "kit.yaml").write_text(
        """name: good-kit
version: 1.0.0
description: Good kit
scripts:
  - name: good-command
    path: scripts/good-kit/good.py
    description: Good script
""",
        encoding="utf-8",
    )
    good_scripts_dir = good_kit_dir / "scripts" / "good-kit"
    good_scripts_dir.mkdir(parents=True)
    (good_scripts_dir / "good.py").write_text(
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
scripts:
  - this is not valid YAML syntax!!!
    invalid indentation here
""",
        encoding="utf-8",
    )

    # Monkeypatch the module to use our test directory
    from erk.cli.commands.kit_exec import group as group_module

    monkeypatch.setattr(group_module, "BundledKitSource", MockSource)
    monkeypatch.setattr(group_module, "_kits_data_dir", lambda: kits_dir)

    # Clear any previously loaded scripts
    kit_exec_group.commands.clear()

    # This should not raise - bad kit should be isolated
    _load_kit_scripts()

    # Good kit should have been loaded despite bad kit failure
    assert "good-kit" in kit_exec_group.commands
    assert "bad-kit" not in kit_exec_group.commands


def test_kit_discovery_isolates_add_command_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that errors from add_command don't prevent other kits from loading."""
    from erk.cli.commands.kit_exec.group import _load_kit_scripts, kit_exec_group

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
scripts:
  - name: test-command
    path: scripts/{kit_name}/test.py
    description: Test script
""",
            encoding="utf-8",
        )
        scripts_dir = kit_dir / "scripts" / kit_name
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "test.py").write_text(
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
    from erk.cli.commands.kit_exec import group as group_module

    monkeypatch.setattr(group_module, "BundledKitSource", MockSource)
    monkeypatch.setattr(group_module, "_kits_data_dir", lambda: kits_dir)

    # Simulate add_command failure for kit1
    original_add_command = kit_exec_group.add_command
    call_count = [0]

    def failing_add_command(cmd: click.Command) -> None:
        call_count[0] += 1
        if call_count[0] == 1:
            # First call fails (kit1)
            raise click.ClickException("Name conflict")
        # Second call succeeds (kit2)
        original_add_command(cmd)

    monkeypatch.setattr(kit_exec_group, "add_command", failing_add_command)

    # Clear any previously loaded scripts
    kit_exec_group.commands.clear()

    # This should not raise - kit1 failure should be isolated
    _load_kit_scripts()

    # kit2 should have been loaded despite kit1 failure
    assert "kit2" in kit_exec_group.commands
