"""Individual code review capabilities.

Each capability installs a specific code review definition to .claude/reviews/
in the target project. Requires code-reviews-system capability to be installed first.
"""

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


class DignifiedPythonReviewDefCapability(ReviewCapability):
    """Dignified Python code review definition.

    Reviews Python code for adherence to dignified-python standards.
    Requires: code-reviews-system capability
    """

    @property
    def review_name(self) -> str:
        return "dignified-python"

    @property
    def description(self) -> str:
        return "Dignified Python style code review"


class DignifiedCodeSimplifierReviewDefCapability(ReviewCapability):
    """Code simplification suggestions review definition.

    Suggests code simplifications using dignified-code-simplifier skill.
    Requires: code-reviews-system capability
    """

    @property
    def review_name(self) -> str:
        return "dignified-code-simplifier"

    @property
    def description(self) -> str:
        return "Code simplification suggestions review"
