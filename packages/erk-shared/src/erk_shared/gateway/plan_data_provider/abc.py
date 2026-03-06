"""Re-export PlanDataProvider from its new home for backwards compatibility.

The canonical import is now:
    from erk.tui.data.provider_abc import PlanDataProvider
"""

from erk.tui.data.provider_abc import PlanDataProvider

__all__ = ["PlanDataProvider"]
