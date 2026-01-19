"""Fake implementation of Shell for testing.

This is a thin shim that re-exports from erk_shared.gateway.shell.
All implementations are in erk_shared for sharing with erk-kits.
"""

from erk_shared.gateway.shell.fake import FakeShell as FakeShell
