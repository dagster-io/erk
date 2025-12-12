"""Bundled kit data for erk.

This package provides paths to bundled kit data files.
It is a minimal, pure-data package with no runtime dependencies.
"""

from functools import cache
from pathlib import Path

__version__ = "0.2.1"


@cache
def get_data_dir() -> Path:
    """Return path to the data directory."""
    return Path(__file__).parent / "data"


@cache
def get_kits_dir() -> Path:
    """Return path to the bundled kits directory."""
    return get_data_dir() / "kits"


@cache
def get_templates_dir() -> Path:
    """Return path to the templates directory."""
    return get_data_dir() / "templates"


@cache
def get_registry_path() -> Path:
    """Return path to the kit registry file."""
    return get_data_dir() / "kits" / "registry.yaml"
