"""Pool configuration for erk_slots.

This module is responsible for reading pool-related configuration
from .erk/config.toml independently of the core erk config system.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_POOL_SIZE = 4


@dataclass(frozen=True)
class PoolConfig:
    """Pool configuration read directly from .erk/config.toml."""

    pool_size: int  # Never None; uses DEFAULT_POOL_SIZE as fallback
    pool_checkout_commands: list[str]  # For future use (not executed yet)
    pool_checkout_shell: str | None


def load_pool_config(repo_root: Path) -> PoolConfig:
    """Load pool configuration from .erk/config.toml.

    Args:
        repo_root: Path to the repository root

    Returns:
        PoolConfig with DEFAULT_POOL_SIZE as fallback if not configured
    """
    config_path = repo_root / ".erk" / "config.toml"

    if not config_path.exists():
        return PoolConfig(
            pool_size=DEFAULT_POOL_SIZE,
            pool_checkout_commands=[],
            pool_checkout_shell=None,
        )

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    # Parse [pool] section
    pool = data.get("pool", {})
    pool_size = pool.get("max_slots")
    if pool_size is not None:
        pool_size = int(pool_size)
    else:
        pool_size = DEFAULT_POOL_SIZE

    # Parse [pool.checkout] section
    pool_checkout = pool.get("checkout", {})
    pool_checkout_commands = [str(x) for x in pool_checkout.get("commands", [])]
    pool_checkout_shell = pool_checkout.get("shell")
    if pool_checkout_shell is not None:
        pool_checkout_shell = str(pool_checkout_shell)

    return PoolConfig(
        pool_size=pool_size,
        pool_checkout_commands=pool_checkout_commands,
        pool_checkout_shell=pool_checkout_shell,
    )
