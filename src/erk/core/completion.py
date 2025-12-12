"""Shell completion script generation operations.

This is a thin shim that re-exports from erk_shared.integrations.completion.
All implementations are in erk_shared for sharing across packages.
"""

# Re-export all Completion types from erk_shared
from erk_shared.integrations.completion import Completion as Completion
from erk_shared.integrations.completion import FakeCompletion as FakeCompletion
from erk_shared.integrations.completion import RealCompletion as RealCompletion
