"""Priority order for MatrixPortal screen presentations."""


def select_presentation(reminder_active, timer_active, football_active):
    """Return the highest-priority active presentation source."""
    if reminder_active:
        return "reminder"
    if timer_active:
        return "timer"
    if football_active:
        return "football"
    return "rotation"
