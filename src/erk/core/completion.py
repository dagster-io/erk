"""Shell completion script generation operations.

This is a thin shim that re-exports from erk_shared.gateway.completion.
All implementations are in erk_shared for sharing across packages.
"""

from erk_shared.gateway.completion.abc import Completion as Completion
from erk_shared.gateway.completion.fake import FakeCompletion as FakeCompletion
from erk_shared.gateway.completion.real import RealCompletion as RealCompletion
