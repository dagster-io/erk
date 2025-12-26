"""Fake implementation of Completion for testing.

This is a thin shim that re-exports from erk_shared.gateway.completion.
All implementations are in erk_shared for sharing with erk-kits.
"""

# Re-export FakeCompletion from erk_shared
from erk_shared.gateway.completion import FakeCompletion as FakeCompletion
