"""Fake implementation of Completion for testing.

This is a thin shim that re-exports from erk_shared.gateways.completion.
All implementations are in erk_shared for sharing with dot-agent-kit.
"""

# Re-export FakeCompletion from erk_shared
from erk_shared.gateways.completion import FakeCompletion as FakeCompletion
