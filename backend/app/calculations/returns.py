from datetime import date, timedelta

from . import constants as c


def quarter_due(fy_start: int, q: int) -> date:
    """Quarterly return: by the end of the month succeeding the quarter (Q1=Apr-Jun ... Q4=Jan-Mar)."""
    end_month_next = {1: (fy_start, 7), 2: (fy_start, 10), 3: (fy_start + 1, 1), 4: (fy_start + 1, 4)}[q]
    y, m = end_month_next
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return nxt - timedelta(days=1)


def annual_due(fy_start: int, label: str | None = None) -> date:
    ext = c.RETURN_EXTENSIONS.get(label or "")
    if ext:
        return date(*ext)
    return date(fy_start + 1, *c.ANNUAL_RETURN_DUE)


def status(due_on: date, filed_on: date | None, as_of: date) -> str:
    if filed_on:
        return "filed_late" if filed_on > due_on else "filed"
    return "overdue" if as_of > due_on else "due"
