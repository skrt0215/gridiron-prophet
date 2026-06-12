"""Shared NFL-week calendar.

Single source of truth for mapping a calendar date to the current NFL week.
Previously this table was copy-pasted in several modules.
"""
from datetime import datetime

# Regular-season week windows (inclusive start/end dates).
SEASON_2025_WEEKS = {
    1: ("2025-09-05", "2025-09-09"),
    2: ("2025-09-10", "2025-09-16"),
    3: ("2025-09-17", "2025-09-23"),
    4: ("2025-09-24", "2025-09-30"),
    5: ("2025-10-01", "2025-10-07"),
    6: ("2025-10-08", "2025-10-14"),
    7: ("2025-10-15", "2025-10-21"),
    8: ("2025-10-22", "2025-10-28"),
    9: ("2025-10-29", "2025-11-04"),
    10: ("2025-11-05", "2025-11-11"),
    11: ("2025-11-12", "2025-11-18"),
    12: ("2025-11-19", "2025-11-25"),
    13: ("2025-11-26", "2025-12-02"),
    14: ("2025-12-03", "2025-12-09"),
    15: ("2025-12-10", "2025-12-16"),
    16: ("2025-12-17", "2025-12-23"),
    17: ("2025-12-24", "2025-12-30"),
    18: ("2025-12-31", "2026-01-05"),
}


def get_current_nfl_week(today=None):
    """Return the NFL week number for ``today`` (defaults to the current date).

    Falls back to week 18 once the regular season is over, and week 1 before it
    starts.
    """
    if today is None:
        today = datetime.now().date()

    for week, (start_str, end_str) in SEASON_2025_WEEKS.items():
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        if start <= today <= end:
            return week

    last_week_end = datetime.strptime(SEASON_2025_WEEKS[18][1], "%Y-%m-%d").date()
    if today > last_week_end:
        return 18

    return 1
