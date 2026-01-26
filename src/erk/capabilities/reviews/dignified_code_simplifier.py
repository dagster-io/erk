"""DignifiedCodeSimplifierReviewDefCapability - code simplification review."""

from erk.core.capabilities.review_capability import ReviewCapability


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
