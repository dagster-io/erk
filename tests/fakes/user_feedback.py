"""Fake UserFeedback for testing.

This is a thin shim that re-exports from erk_shared.gateway.feedback.
All implementations are in erk_shared for sharing with erk-kits.
"""

# Re-export FakeUserFeedback from erk_shared
from erk_shared.gateway.feedback import FakeUserFeedback as FakeUserFeedback
