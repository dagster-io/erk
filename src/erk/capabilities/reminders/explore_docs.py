"""ExploreDocsReminderCapability - reminder for doc-first Explore prompts."""

from erk.core.capabilities.reminder_capability import ReminderCapability


class ExploreDocsReminderCapability(ReminderCapability):
    """Reminder to include doc-first instructions when spawning Explore agents."""

    @property
    def reminder_name(self) -> str:
        return "explore-docs"

    @property
    def description(self) -> str:
        return "Remind agent to include doc-first instructions in Explore prompts"
