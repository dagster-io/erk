"""Detection for uvx (uv tool run) invocation.

This module detects when erk is running via 'uvx erk' or 'uv tool run erk',
which prevents shell integration from working properly.
"""

import os
import sys


def is_running_via_uvx() -> bool:
    """Detect if erk was invoked via 'uvx erk' or 'uv tool run erk'.

    Detection strategy:
    1. Check if sys.prefix contains uv cache markers (cache/uv, .cache/uv)
    2. Check if VIRTUAL_ENV contains uv cache markers
    3. Check for UV_TOOL_DIR or UV_CACHE_DIR environment variables

    Returns:
        True if running via uvx, False otherwise
    """
    # Pattern markers that indicate a uv tool/uvx environment
    uv_cache_patterns = ("/cache/uv/", "/.cache/uv/", "\\cache\\uv\\")

    # Check sys.prefix for uv cache markers
    prefix = sys.prefix
    for pattern in uv_cache_patterns:
        if pattern in prefix:
            return True

    # Check VIRTUAL_ENV environment variable
    virtual_env = os.environ.get("VIRTUAL_ENV", "")
    for pattern in uv_cache_patterns:
        if pattern in virtual_env:
            return True

    # Check for UV_TOOL_DIR or UV_CACHE_DIR environment variables
    # These indicate uv is managing tools
    if "UV_TOOL_DIR" in os.environ or "UV_CACHE_DIR" in os.environ:
        return True

    return False


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
