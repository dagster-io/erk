"""Re-export RealPlanDataProvider from its new home for backwards compatibility.

The canonical import is now:
    from erk.tui.data.real_provider import RealPlanDataProvider
"""

from erk.tui.data.real_provider import RealPlanDataProvider

__all__ = ["RealPlanDataProvider"]
