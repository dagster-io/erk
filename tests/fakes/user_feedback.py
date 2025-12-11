"""Fake UserFeedback for testing.

This is a thin shim that re-exports from erk_shared.gateways.feedback.
All implementations are in erk_shared for sharing with dot-agent-kit.
"""

# Re-export FakeUserFeedback from erk_shared
from erk_shared.gateways.feedback import FakeUserFeedback as FakeUserFeedback
