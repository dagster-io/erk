"""Debug logging utilities for erk.

DEPRECATED: Import from erk_shared.debug instead.
This module is a re-export shim for backwards compatibility.
"""

# Re-export for backwards compatibility (explicit re-export syntax per PEP 484)
from erk_shared.debug import debug_log as debug_log
from erk_shared.debug import is_debug as is_debug
