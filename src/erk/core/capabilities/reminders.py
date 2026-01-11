"""Concrete reminder capabilities for opt-in context injection.

Each reminder capability controls whether a specific reminder is injected
by the user prompt hook. Users install these via:

    erk init capability install devrun-reminder

Installation creates a marker file that signals the hook to include that reminder.
"""

from erk.core.capabilities.reminder_capability import ReminderCapability


class DevrunReminderCapability(ReminderCapability):
    """Reminder to use devrun agent for pytest/ty/ruff/prettier/make/gt."""

    @property
    def reminder_name(self) -> str:
        return "devrun"

    @property
    def description(self) -> str:
        return "Remind agent to use devrun for CI tool commands"


class DignifiedPythonReminderCapability(ReminderCapability):
    """Reminder to follow dignified-python coding standards."""

    @property
    def reminder_name(self) -> str:
        return "dignified-python"

    @property
    def description(self) -> str:
        return "Remind agent to follow dignified-python standards"


class TripwiresReminderCapability(ReminderCapability):
    """Reminder to check tripwires.md before performing actions."""

    @property
    def reminder_name(self) -> str:
        return "tripwires"

    @property
    def description(self) -> str:
        return "Remind agent to check tripwires.md"
