"""Display-specific formatting refinements."""

from formatting import todoist_due_label as _todoist_due_label


def todoist_due_label(event, current_date):
    """Return a day-only Todoist due label, using TODAY for same-day tasks."""
    label = _todoist_due_label(event, current_date)
    return "TODAY" if label == "DUE IN TODAY" else label
