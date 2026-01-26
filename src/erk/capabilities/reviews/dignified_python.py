"""DignifiedPythonReviewDefCapability - dignified Python code review."""

from erk.core.capabilities.review_capability import ReviewCapability


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
