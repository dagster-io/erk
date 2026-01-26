"""DevrunReminderCapability - reminder to use devrun agent."""

from erk.core.capabilities.reminder_capability import ReminderCapability


class DevrunReminderCapability(ReminderCapability):
    """Reminder to use devrun agent for pytest/ty/ruff/prettier/make/gt."""

    @property
    def reminder_name(self) -> str:
        return "devrun"

    @property
    def description(self) -> str:
        return "Remind agent to use devrun for CI tool commands"
