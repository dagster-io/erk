"""TripwiresReminderCapability - reminder to check tripwires.md."""

from erk.core.capabilities.reminder_capability import ReminderCapability


class TripwiresReminderCapability(ReminderCapability):
    """Reminder to check tripwires.md before performing actions."""

    @property
    def reminder_name(self) -> str:
        return "tripwires"

    @property
    def description(self) -> str:
        return "Remind agent to check tripwires.md"
