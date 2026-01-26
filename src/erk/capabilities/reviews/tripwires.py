"""TripwiresReviewDefCapability - tripwires code review."""

from erk.core.capabilities.review_capability import ReviewCapability


class TripwiresReviewDefCapability(ReviewCapability):
    """Tripwires code review definition.

    Detects dangerous code patterns based on tripwire rules.
    Requires: code-reviews-system capability
    """

    @property
    def review_name(self) -> str:
        return "tripwires"

    @property
    def description(self) -> str:
        return "Tripwires code review for detecting dangerous patterns"
