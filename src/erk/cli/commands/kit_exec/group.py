"""Execute scripts from bundled kits."""

import importlib
import traceback
from functools import cache
from pathlib import Path
from typing import Any

import click

import erk_kits
from erk.kits.cli.output import user_output
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.models.kit import KitManifest
from erk.kits.sources.bundled import BundledKitSource


@cache
def _kits_data_dir() -> Path:
    """Return path to the bundled kits data directory."""
    return erk_kits.get_kits_dir()


# Module prefix for dynamic command imports
KITS_MODULE_PREFIX = "erk_kits.data.kits"


@click.group()
@click.pass_context
def kit_exec_group(ctx: click.Context) -> None:
    """Execute scripts from bundled kits.

    Lists available kits with scripts. Use 'erk kit exec <kit_id> --help'
    to see available scripts for a specific kit.
    """


class LazyKitGroup(click.Group):
    """Click group that loads kit scripts lazily on first access."""

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
        """List available scripts, loading them if needed."""
        if not self._loaded:
            self._load_scripts(ctx)
        return super().list_commands(ctx)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Get a script by name, loading scripts if needed."""
        if not self._loaded:
            self._load_scripts(ctx)
        return super().get_command(ctx, cmd_name)

    def _load_scripts(self, ctx: click.Context) -> None:
        """Load all scripts for this kit."""
        if self._loaded:
            return

        self._loaded = True

        # Get debug flag from context if available
        debug = self._debug
        if ctx.obj and hasattr(ctx.obj, "debug"):
            debug = ctx.obj.debug

        # Track successful script loads for validation
        scripts_before = len(self.commands)

        for script_def in self._manifest.scripts:
            # Validate script definition
            validation_errors = script_def.validate()
            if validation_errors:
                kit_name = self._manifest.name
                script_name = script_def.name
                error_msg = f"Invalid script '{script_name}' in kit '{kit_name}':\n"
                for error in validation_errors:
                    error_msg += f"  - {error}\n"
                user_output(error_msg)
                if debug:
                    raise click.ClickException(error_msg)
                continue

            # Check that script file exists
            script_file = self._kit_dir / script_def.path
            if not script_file.exists():
                error_msg = (
                    f"Warning: Script file not found for '{script_def.name}' "
                    f"in kit '{self._manifest.name}': {script_file}\n"
                )
                user_output(error_msg)
                if debug:
                    raise click.ClickException(error_msg)
                continue

            # Convert path to module path using pathlib
            script_path = Path(script_def.path)
            module_parts = script_path.with_suffix("").parts
            module_path_str = ".".join(module_parts)
            full_module_path = f"{KITS_MODULE_PREFIX}.{self._kit_name}.{module_path_str}"

            # Import the module
            try:
                module = importlib.import_module(full_module_path)
            except ImportError as e:
                error_msg = (
                    f"Warning: Failed to import script '{script_def.name}' "
                    f"from kit '{self._manifest.name}': {e}\n"
                )
                user_output(error_msg)
                if debug:
                    user_output(traceback.format_exc())
                continue

            # Get the script function (convert hyphenated name to snake_case)
            function_name = script_def.name.replace("-", "_")
            if not hasattr(module, function_name):
                error_msg = (
                    f"Warning: Script '{script_def.name}' in kit '{self._manifest.name}' "
                    f"does not have expected function '{function_name}' "
                    f"in module {full_module_path}\n"
                )
                user_output(error_msg)
                if debug:
                    raise click.ClickException(error_msg)
                continue

            script_func = getattr(module, function_name)

            # Add the script to the kit's group
            self.add_command(script_func, name=script_def.name)

        # Validate that at least one script was successfully loaded
        scripts_loaded = len(self.commands) - scripts_before
        if scripts_loaded == 0:
            warning = (
                f"Warning: Kit '{self._manifest.name}' loaded 0 scripts "
                f"(all {len(self._manifest.scripts)} script(s) failed to load)\n"
            )
            user_output(warning)


def _load_single_kit_scripts(
    kit_name: str, kit_dir: Path, manifest: KitManifest, debug: bool = False
) -> click.Group | None:
    """Load scripts for a single kit with error isolation.

    Args:
        kit_name: Internal kit directory name
        kit_dir: Path to kit directory
        manifest: Kit manifest
        debug: Whether to show full tracebacks

    Returns:
        Click group for kit, or None if kit failed to load
    """
    try:
        # Skip kits without scripts (silently - this is expected)
        if not manifest.scripts:
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


def _load_kit_scripts() -> None:
    """Dynamically load scripts from all kits with scripts."""
    source = BundledKitSource()
    available_kits = source.list_available()

    kits_data_dir = _kits_data_dir()

    # Check data directory exists
    if not kits_data_dir.exists():
        user_output(f"Warning: Kits data directory not found: {kits_data_dir}\n")
        return

    for kit_name in available_kits:
        try:
            kit_dir = kits_data_dir / kit_name
            manifest_path = kit_dir / "kit.yaml"

            if not manifest_path.exists():
                continue

            manifest = load_kit_manifest(manifest_path)

            # Load kit scripts with error isolation
            kit_group = _load_single_kit_scripts(
                kit_name=kit_name, kit_dir=kit_dir, manifest=manifest, debug=False
            )

            # Skip if kit failed to load or has no scripts
            if kit_group is None:
                continue

            # Add the kit's group to the kit_exec group
            kit_exec_group.add_command(kit_group)

        except Exception as e:
            # Isolate individual kit failures - continue processing other kits
            error_msg = f"Warning: Failed to load kit '{kit_name}': {e}\n"
            user_output(error_msg)
            # Note: Debug mode tracebacks handled by _load_single_kit_scripts
            continue


# Load all kit scripts when module is imported
_load_kit_scripts()
