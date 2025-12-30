"""Bundled kit helpers."""

from pathlib import Path

import erk_kits


def list_bundled_kits() -> list[str]:
    """List all bundled kit names.

    Returns:
        List of kit names that have a kit.yaml manifest file.
    """
    kits_dir = erk_kits.get_kits_dir()
    if not kits_dir.exists():
        return []

    return [d.name for d in kits_dir.iterdir() if d.is_dir() and (d / "kit.yaml").exists()]


def get_bundled_kit_path(kit_name: str) -> Path | None:
    """Get the path to a bundled kit by name.

    Args:
        kit_name: The name of the kit to find.

    Returns:
        Path to the kit directory, or None if not found.
    """
    kit_path = erk_kits.get_kits_dir() / kit_name
    if kit_path.exists():
        return kit_path
    return None
