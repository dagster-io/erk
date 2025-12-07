"""Integration test to verify kit CLI command names match between kit.yaml and decorators.

This test ensures that all kit CLI commands in the erk kit have explicit @click.command(name="...")
decorators that match their registration names in kit.yaml. This prevents runtime loading failures
where the kit loader can't find commands due to name mismatches.
"""

import importlib.util
import inspect
from pathlib import Path

import click
import pytest
import yaml


def load_erk_kit_manifest() -> dict:
    """Load the erk kit.yaml manifest.

    Returns:
        Parsed kit.yaml as dict
    """
    kit_yaml_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "dot_agent_kit"
        / "data"
        / "kits"
        / "erk"
        / "kit.yaml"
    )

    if not kit_yaml_path.exists():
        msg = f"Kit manifest not found at {kit_yaml_path}"
        raise FileNotFoundError(msg)

    with kit_yaml_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_python_module(module_path: Path):
    """Dynamically load a Python module from path.

    Args:
        module_path: Path to the Python file

    Returns:
        Loaded module object
    """
    import sys

    # Generate unique module name to avoid conflicts
    module_name = f"_temp_module_{module_path.stem}"

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    # Register module in sys.modules BEFORE exec_module to support
    # dataclasses with `from __future__ import annotations`
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        # Clean up to avoid polluting sys.modules
        sys.modules.pop(module_name, None)


def extract_click_command_name(module) -> str | None:
    """Extract the name parameter from @click.command() decorator in module.

    Args:
        module: Loaded Python module

    Returns:
        Command name if explicit name= parameter exists, None otherwise
    """
    # Find all click.Command instances in the module
    for _name, obj in inspect.getmembers(module):
        if isinstance(obj, click.Command):
            # Click commands have a .name attribute
            return obj.name

    return None


def test_erk_kit_command_names_match_decorators():
    """Verify all erk kit CLI commands have matching names in decorators and kit.yaml.

    This test:
    1. Loads all commands from erk kit.yaml
    2. For each command, loads the Python module
    3. Extracts the Click command name from the decorator
    4. Verifies it matches the expected kebab-case name from kit.yaml

    Fails with clear message showing which commands have mismatches.
    """
    # Load kit manifest
    manifest = load_erk_kit_manifest()
    kit_cli_commands = manifest.get("kit_cli_commands", [])

    if not kit_cli_commands:
        pytest.skip("No kit CLI commands defined in erk kit.yaml")

    # Base directory for kit commands
    kit_base_dir = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "dot_agent_kit"
        / "data"
        / "kits"
        / "erk"
    )

    mismatches = []

    # Check each command
    for cmd_def in kit_cli_commands:
        expected_name = cmd_def["name"]
        relative_path = cmd_def["path"]

        # Construct full path to command module
        module_path = kit_base_dir / relative_path

        if not module_path.exists():
            mismatches.append(
                {
                    "command": expected_name,
                    "error": "module_not_found",
                    "message": f"Module not found at {module_path}",
                }
            )
            continue

        # Load the module
        try:
            module = load_python_module(module_path)
            if module is None:
                mismatches.append(
                    {
                        "command": expected_name,
                        "error": "module_load_failed",
                        "message": f"Failed to load module at {module_path}",
                    }
                )
                continue
        except Exception as e:
            mismatches.append(
                {
                    "command": expected_name,
                    "error": "module_import_error",
                    "message": f"Import error: {e}",
                }
            )
            continue

        # Extract Click command name
        actual_name = extract_click_command_name(module)

        if actual_name is None:
            mismatches.append(
                {
                    "command": expected_name,
                    "error": "no_click_command",
                    "message": f"No Click command found in {relative_path}",
                }
            )
            continue

        # Verify names match
        if actual_name != expected_name:
            message = (
                f"Command name mismatch in {relative_path}: "
                f"expected '{expected_name}', got '{actual_name}'"
            )
            mismatches.append(
                {
                    "command": expected_name,
                    "error": "name_mismatch",
                    "expected": expected_name,
                    "actual": actual_name,
                    "message": message,
                }
            )

    # Fail with detailed message if any mismatches found
    if mismatches:
        error_message = "Kit CLI command name mismatches found:\n\n"
        for mismatch in mismatches:
            error_message += f"  • {mismatch['command']}: {mismatch['message']}\n"

        error_message += "\n"
        error_message += "Fix: Add explicit name= parameter to @click.command() decorators:\n"
        error_message += '  @click.command(name="kebab-case-name")\n'

        pytest.fail(error_message)


def test_all_command_files_are_registered():
    """Verify all kit CLI command files have entries in kit.yaml.

    Prevents forgetting to register new commands - catches the error
    at CI time rather than at runtime.
    """
    manifest = load_erk_kit_manifest()
    registered_paths = {cmd["path"] for cmd in manifest.get("kit_cli_commands", [])}

    kit_base_dir = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "dot_agent_kit"
        / "data"
        / "kits"
        / "erk"
    )
    command_dir = kit_base_dir / "kit_cli_commands" / "erk"

    if not command_dir.exists():
        pytest.skip(f"Command directory not found: {command_dir}")

    unregistered = []
    for py_file in sorted(command_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        relative_path = f"kit_cli_commands/erk/{py_file.name}"
        if relative_path not in registered_paths:
            unregistered.append(py_file.name)

    if unregistered:
        error_msg = "Unregistered kit CLI command files found:\n\n"
        for filename in unregistered:
            error_msg += f"  • {filename}\n"
        error_msg += "\nFix: Add entries to kit.yaml kit_cli_commands section"
        pytest.fail(error_msg)
