"""
Central season configuration for Gridiron Prophet.
Change CURRENT_SEASON here and the whole app rolls forward.
"""
from datetime import datetime

CURRENT_SEASON = 2026

TRAINING_SEASONS = [2022, 2023, 2024, 2025, 2026]

SEASON_WEEKS = {
    2025: {
        1: ("2025-09-05", "2025-09-09"), 2: ("2025-09-10", "2025-09-16"),
        3: ("2025-09-17", "2025-09-23"), 4: ("2025-09-24", "2025-09-30"),
        5: ("2025-10-01", "2025-10-07"), 6: ("2025-10-08", "2025-10-14"),
        7: ("2025-10-15", "2025-10-21"), 8: ("2025-10-22", "2025-10-28"),
        9: ("2025-10-29", "2025-11-04"), 10: ("2025-11-05", "2025-11-11"),
        11: ("2025-11-12", "2025-11-18"), 12: ("2025-11-19", "2025-11-25"),
        13: ("2025-11-26", "2025-12-02"), 14: ("2025-12-03", "2025-12-09"),
        15: ("2025-12-10", "2025-12-16"), 16: ("2025-12-17", "2025-12-23"),
        17: ("2025-12-24", "2025-12-30"), 18: ("2025-12-31", "2026-01-05"),
    },
    2026: {
        1: ("2026-09-09", "2026-09-15"), 2: ("2026-09-16", "2026-09-22"),
        3: ("2026-09-23", "2026-09-29"), 4: ("2026-09-30", "2026-10-06"),
        5: ("2026-10-07", "2026-10-13"), 6: ("2026-10-14", "2026-10-20"),
        7: ("2026-10-21", "2026-10-27"), 8: ("2026-10-28", "2026-11-03"),
        9: ("2026-11-04", "2026-11-10"), 10: ("2026-11-11", "2026-11-17"),
        11: ("2026-11-18", "2026-11-24"), 12: ("2026-11-25", "2026-12-01"),
        13: ("2026-12-02", "2026-12-08"), 14: ("2026-12-09", "2026-12-15"),
        15: ("2026-12-16", "2026-12-22"), 16: ("2026-12-23", "2026-12-29"),
        17: ("2026-12-30", "2027-01-05"), 18: ("2027-01-06", "2027-01-11"),
    },
}


def get_season_weeks(season=None):
    season = season or CURRENT_SEASON
    return SEASON_WEEKS.get(season, {})


def get_current_week(season=None):
    season = season or CURRENT_SEASON
    weeks = get_season_weeks(season)
    if not weeks:
        return 1
    today = datetime.now().date()
    for week, (start_str, end_str) in weeks.items():
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        if start <= today <= end:
            return week
    last_week = max(weeks.keys())
    last_week_end = datetime.strptime(weeks[last_week][1], "%Y-%m-%d").date()
    if today > last_week_end:
        return last_week
    return 1


def date_to_week(date_str, season=None):
    season = season or CURRENT_SEASON
    weeks = get_season_weeks(season)
    try:
        date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    for week, (start_str, end_str) in weeks.items():
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        if start <= date <= end:
            return week
    if weeks:
        last_week = max(weeks.keys())
        last_week_end = datetime.strptime(weeks[last_week][1], "%Y-%m-%d").date()
        if date > last_week_end:
            return last_week
    return None
