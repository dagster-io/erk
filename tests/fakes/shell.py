"""Fake implementation of Shell for testing.

All implementations are in erk_shared for sharing with erk-kits.
This is a thin shim that re-exports from erk_shared.gateways.shell.
All implementations are in erk_shared for sharing with dot-agent-kit.
"""

# Re-export FakeShell from erk_shared
from erk_shared.gateways.shell import FakeShell as FakeShell
