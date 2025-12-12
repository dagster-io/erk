"""Fake implementation of Shell for testing.

This is a thin shim that re-exports from erk_shared.integrations.shell.
All implementations are in erk_shared for sharing with erk-kits.
"""

# Re-export FakeShell from erk_shared
from erk_shared.integrations.shell import FakeShell as FakeShell
