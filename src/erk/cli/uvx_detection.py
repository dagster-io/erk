"""Detection for uvx (uv tool run) invocation.

This module detects when erk is running via 'uvx erk' or 'uv tool run erk',
which prevents shell integration from working properly.
"""

import sys
from pathlib import Path


def is_running_via_uvx() -> bool:
    """Detect if running via uvx/uv tool run (best effort, not officially supported).

    Detection strategy:
    1. Check pyvenv.cfg for uv marker - if absent, not a uv-created venv
    2. Check if prefix path contains ephemeral cache markers (uvx uses cache, not tool dir)

    Note: uvx environments are ephemeral (live in cache directory), while
    `uv tool install` environments are persistent. We only want to detect uvx.

    Returns:
        True if running via uvx, False otherwise
    """
    prefix = Path(sys.prefix)

    # Check pyvenv.cfg for uv marker
    pyvenv_cfg = prefix / "pyvenv.cfg"
    if pyvenv_cfg.exists():
        content = pyvenv_cfg.read_text(encoding="utf-8")
        if "uv = " not in content:
            return False  # Not a uv-created venv

    # uvx environments are ephemeral (in cache), not persistent (in UV_TOOL_DIR)
    prefix_str = str(prefix)
    ephemeral_markers = (
        "/uv/archive-v",  # uvx ephemeral environments
        "/.cache/uv/",
        "/cache/uv/",
    )
    return any(marker in prefix_str for marker in ephemeral_markers)


def get_uvx_warning_message() -> str:
    """Get the warning message to display when running via uvx.

    Returns:
        Multi-line warning message explaining the issue and fix
    """
    return """Running via 'uvx erk' - shell integration won't work properly

Shell integration commands like 'erk up', 'erk checkout', and 'erk pr land' need to
change your shell's directory and activate virtual environments, which doesn't work
when running in uvx's isolated subprocess.

To fix this:
  1. Install erk in uv's tools: uv tool install erk
  2. Set up shell integration: erk init --shell

Commands will execute, but directory changes won't affect your shell."""
