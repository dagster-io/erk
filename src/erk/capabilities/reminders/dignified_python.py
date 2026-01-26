"""DignifiedPythonReminderCapability - reminder for dignified-python standards."""

from erk.core.capabilities.reminder_capability import ReminderCapability


class DignifiedPythonReminderCapability(ReminderCapability):
    """Reminder to follow dignified-python coding standards."""

    @property
    def reminder_name(self) -> str:
        return "dignified-python"

    @property
    def description(self) -> str:
        return "Remind agent to follow dignified-python standards"
