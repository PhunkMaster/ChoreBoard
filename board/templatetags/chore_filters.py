"""Custom template filters for chore display."""
from django import template
from chores.models import Completion

register = template.Library()


@register.filter
def format_due_date(due_at):
    """
    Format due_at for display.
    Shows 'No due date' for far-future sentinel dates (year >= 9999).
    Otherwise shows formatted date.
    """
    if not due_at:
        return 'No due date'

    # Check for sentinel date (year 9999 = no due date for one-time tasks)
    if due_at.year >= 9999:
        return 'No due date'

    # Normal due date - show formatted date
    return due_at.strftime('%b %d, %Y')


@register.filter
def is_sentinel_date(due_at):
    """
    Check if a due date is a sentinel date (no real due date).
    Returns True for dates with year >= 9999.
    """
    if not due_at:
        return False

    return due_at.year >= 9999


@register.simple_tag
def get_completion_details(completion_id):
    """Get completion details including helpers."""
    if not completion_id:
        return None
    try:
        return Completion.objects.select_related(
            'completed_by'
        ).prefetch_related(
            'shares__user'
        ).get(id=completion_id)
    except Completion.DoesNotExist:
        return None
