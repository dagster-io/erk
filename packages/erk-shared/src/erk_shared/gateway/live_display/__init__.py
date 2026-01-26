"""Live display gateway for real-time output."""

from erk_shared.gateway.live_display.abc import LiveDisplay
from erk_shared.gateway.live_display.fake import FakeLiveDisplay
from erk_shared.gateway.live_display.real import RealLiveDisplay

__all__ = [
    "LiveDisplay",
    "FakeLiveDisplay",
    "RealLiveDisplay",
]
