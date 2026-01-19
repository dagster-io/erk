"""Fake implementation of Completion for testing.

This is a thin shim that re-exports from erk_shared.gateway.completion.
All implementations are in erk_shared for sharing with erk-kits.
"""

from erk_shared.gateway.completion.fake import FakeCompletion as FakeCompletion
