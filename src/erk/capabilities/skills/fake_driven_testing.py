"""FakeDrivenTestingCapability - 5-layer test architecture with fakes."""

from erk.core.capabilities.skill_capability import SkillCapability


class FakeDrivenTestingCapability(SkillCapability):
    """5-layer test architecture with fakes."""

    @property
    def skill_name(self) -> str:
        return "fake-driven-testing"

    @property
    def description(self) -> str:
        return "5-layer test architecture with fakes"
