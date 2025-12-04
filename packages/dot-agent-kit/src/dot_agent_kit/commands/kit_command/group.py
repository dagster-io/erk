"""Run commands from bundled kits."""

import importlib
import traceback
from pathlib import Path
from typing import Any

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.io.manifest import load_kit_manifest
from dot_agent_kit.models.kit import KitManifest
from dot_agent_kit.sources.bundled import BundledKitSource

# Path configuration for kit loading
# Resolved relative to this file's location
KITS_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "kits"

# Module prefix for dynamic command imports
KITS_MODULE_PREFIX = "dot_agent_kit.data.kits"


@click.group()
@click.pass_context
def kit_command_group(ctx: click.Context) -> None:
    """Run kit cli commands from bundled kits.

    Lists available kits with kit cli commands. Use 'dot-agent kit-command <kit_id> --help'
    to see available kit cli commands for a specific kit.
    """


class LazyKitGroup(click.Group):
    """Click group that loads kit commands lazily on first access."""

    def __init__(
        self,
        kit_name: str,
        kit_dir: Path,
        manifest: KitManifest,
        debug: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize lazy kit group.

        Args:
            kit_name: Internal kit directory name
            kit_dir: Path to kit directory
            manifest: Kit manifest
            debug: Whether to show full tracebacks
            **kwargs: Additional arguments passed to click.Group
        """
        super().__init__(**kwargs)
        self._kit_name = kit_name
        self._kit_dir = kit_dir
        self._manifest = manifest
        self._debug = debug
        self._loaded = False

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List available commands, loading them if needed."""
        if not self._loaded:
            self._load_commands(ctx)
        return super().list_commands(ctx)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Get a command by name, loading commands if needed."""
        if not self._loaded:
            self._load_commands(ctx)
        return super().get_command(ctx, cmd_name)

    def _load_commands(self, ctx: click.Context) -> None:
        """Load all commands for this kit."""
        if self._loaded:
            return

        self._loaded = True

        # Get debug flag from context if available
        debug = self._debug
        if ctx.obj and hasattr(ctx.obj, "debug"):
            debug = ctx.obj.debug

        # Track successful command loads for validation
        commands_before = len(self.commands)

        for command_def in self._manifest.kit_cli_commands:
            # Validate command definition
            validation_errors = command_def.validate()
            if validation_errors:
                kit_name = self._manifest.name
                cmd_name = command_def.name
                error_msg = f"Invalid command '{cmd_name}' in kit '{kit_name}':\n"
                for error in validation_errors:
                    error_msg += f"  - {error}\n"
                user_output(error_msg)
                if debug:
                    raise click.ClickException(error_msg)
                continue

            # Check that command file exists
            command_file = self._kit_dir / command_def.path
            if not command_file.exists():
                error_msg = (
                    f"Warning: Command file not found for '{command_def.name}' "
                    f"in kit '{self._manifest.name}': {command_file}\n"
                )
                user_output(error_msg)
                if debug:
                    raise click.ClickException(error_msg)
                continue

            # Convert path to module path using pathlib
            command_path = Path(command_def.path)
            module_parts = command_path.with_suffix("").parts
            module_path_str = ".".join(module_parts)
            full_module_path = f"{KITS_MODULE_PREFIX}.{self._kit_name}.{module_path_str}"

            # Import the module
            try:
                module = importlib.import_module(full_module_path)
            except ImportError as e:
                error_msg = (
                    f"Warning: Failed to import command '{command_def.name}' "
                    f"from kit '{self._manifest.name}': {e}\n"
                )
                user_output(error_msg)
                if debug:
                    user_output(traceback.format_exc())
                continue

            # Get the command function (convert hyphenated name to snake_case)
            function_name = command_def.name.replace("-", "_")
            if not hasattr(module, function_name):
                error_msg = (
                    f"Warning: Command '{command_def.name}' in kit '{self._manifest.name}' "
                    f"does not have expected function '{function_name}' "
                    f"in module {full_module_path}\n"
                )
                user_output(error_msg)
                if debug:
                    raise click.ClickException(error_msg)
                continue

            command_func = getattr(module, function_name)

            # Add the command to the kit's group
            # Note: Schema documentation is handled by the @json_output decorator
            self.add_command(command_func, name=command_def.name)

        # Validate that at least one command was successfully loaded
        commands_loaded = len(self.commands) - commands_before
        if commands_loaded == 0:
            warning = (
                f"Warning: Kit '{self._manifest.name}' loaded 0 commands "
                f"(all {len(self._manifest.kit_cli_commands)} command(s) failed to load)\n"
            )
            user_output(warning)


def _load_single_kit_commands(
    kit_name: str, kit_dir: Path, manifest: KitManifest, debug: bool = False
) -> click.Group | None:
    """Load commands for a single kit with error isolation.

    Args:
        kit_name: Internal kit directory name
        kit_dir: Path to kit directory
        manifest: Kit manifest
        debug: Whether to show full tracebacks

    Returns:
        Click group for kit, or None if kit failed to load
    """
    try:
        # Skip kits without kit cli commands (silently - this is expected)
        if not manifest.kit_cli_commands:
            return None

        # Validate kit directory exists
        if not kit_dir.exists():
            error_msg = f"Warning: Kit directory not found: {kit_dir}\n"
            user_output(error_msg)
            if debug:
                raise click.ClickException(error_msg)
            return None

        # Create lazy loading group for this kit
        kit_group = LazyKitGroup(
            kit_name=kit_name,
            kit_dir=kit_dir,
            manifest=manifest,
            debug=debug,
            name=manifest.name,
            help=manifest.description,
        )

        return kit_group

    except Exception as e:
        error_msg = f"Warning: Failed to load kit '{manifest.name}': {e}\n"
        user_output(error_msg)
        if debug:
            user_output(traceback.format_exc())
            raise
        return None


def _load_kit_commands() -> None:
    """Dynamically load commands from all kits with commands."""
    source = BundledKitSource()
    available_kits = source.list_available()

    # Check data directory exists
    if not KITS_DATA_DIR.exists():
        user_output(f"Warning: Kits data directory not found: {KITS_DATA_DIR}\n")
        return

    for kit_name in available_kits:
        try:
            kit_dir = KITS_DATA_DIR / kit_name
            manifest_path = kit_dir / "kit.yaml"

            if not manifest_path.exists():
                continue

            manifest = load_kit_manifest(manifest_path)

            # Load kit commands with error isolation
            kit_group = _load_single_kit_commands(
                kit_name=kit_name, kit_dir=kit_dir, manifest=manifest, debug=False
            )

            # Skip if kit failed to load or has no commands
            if kit_group is None:
                continue

            # Add the kit's group to the kit_command group
            kit_command_group.add_command(kit_group)

        except Exception as e:
            # Isolate individual kit failures - continue processing other kits
            error_msg = f"Warning: Failed to load kit '{kit_name}': {e}\n"
            user_output(error_msg)
            # Note: Debug mode tracebacks handled by _load_single_kit_commands
            continue


# Load all kit commands when module is imported
_load_kit_commands()
