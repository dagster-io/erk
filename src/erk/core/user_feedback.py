"""User-facing diagnostic output with mode awareness.

This is a thin shim that re-exports from erk_shared.gateway.feedback.
All implementations are in erk_shared for sharing across packages.
"""

# Re-export all UserFeedback types from erk_shared
from erk_shared.gateway.feedback import FakeUserFeedback as FakeUserFeedback
from erk_shared.gateway.feedback import InteractiveFeedback as InteractiveFeedback
from erk_shared.gateway.feedback import SuppressedFeedback as SuppressedFeedback
from erk_shared.gateway.feedback import UserFeedback as UserFeedback
