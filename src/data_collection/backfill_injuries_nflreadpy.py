import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import nflreadpy as nfl
from src.database.db_manager import DatabaseManager
from src.config.season import CURRENT_SEASON, get_season_weeks
from src.data_collection.smart_injury_updater import normalize_player_name

TEAM_FIX = {'LA': 'LAR', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'}
GAME_STATUSES = ['Out', 'Doubtful', 'Questionable']
PRACTICE_MAP = {
    'Did Not Participate In Practice': 'DNP',
    'Limited Participation in Practice': 'Limited',
    'Full Participation in Practice': 'Full',
}


def _clean(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def _practice(value):
    value = _clean(value)
    if value is None:
        return None
    return PRACTICE_MAP.get(value, str(value)[:20])


def build_player_map(db, season):
    rows = db.execute_query(
        "SELECT ps.player_id, ps.team_id, p.name "
        "FROM player_seasons ps JOIN players p ON p.player_id = ps.player_id "
        "WHERE ps.season = %s",
        (season,),
    )
    return {(normalize_player_name(r['name']), r['team_id']): r['player_id'] for r in rows}


def backfill(season, commit=False):
    db = DatabaseManager()

    week_dates = {wk: dates[0] for wk, dates in get_season_weeks(season).items()}
    if not week_dates:
        print(f"No SEASON_WEEKS configured for {season}; aborting.")
        return

    teams = {t['abbreviation']: t['team_id'] for t in db.get_all_teams()}
    player_map = build_player_map(db, season)

    df = nfl.load_injuries([season]).to_pandas()
    df = df[(df['season_type'] == 'REG') & (df['report_status'].isin(GAME_STATUSES))]
    df = df[df['week'].isin(week_dates.keys())]

    records = []
    unmatched = []
    for _, row in df.iterrows():
        team = TEAM_FIX.get(row['team'], row['team'])
        team_id = teams.get(team)
        player_id = player_map.get((normalize_player_name(row['full_name']), team_id))
        if not player_id:
            unmatched.append(f"{row['full_name']} ({row['team']})")
            continue
        week = int(row['week'])
        records.append({
            'player_id': player_id,
            'season': season,
            'week': week,
            'injury_status': row['report_status'],
            'body_part': (str(_clean(row['report_primary_injury']))[:50]
                          if _clean(row['report_primary_injury']) else None),
            'date_reported': week_dates[week],
            'practice_status': _practice(row['practice_status']),
            'notes': _clean(row['report_secondary_injury']),
        })

    print(f"Season {season}: {len(df)} game-status rows, "
          f"{len(records)} matched, {len(unmatched)} unmatched")

    if not commit:
        print("DRY RUN - no changes written. Re-run with --commit to apply.")
        print("Unmatched sample:", unmatched[:15])
        return

    deleted = db.execute_update("DELETE FROM injuries WHERE season = %s", (season,))
    print(f"Deleted {deleted} existing injuries for {season}")

    inserted = 0
    for rec in records:
        db.add_injury(
            player_id=rec['player_id'],
            season=rec['season'],
            injury_status=rec['injury_status'],
            date_reported=rec['date_reported'],
            week=rec['week'],
            body_part=rec['body_part'],
            practice_status=rec['practice_status'],
            notes=rec['notes'],
        )
        inserted += 1

    print(f"Inserted {inserted} injuries for {season}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill historical injuries from nflreadpy")
    parser.add_argument('--season', type=int, default=CURRENT_SEASON - 1)
    parser.add_argument('--commit', action='store_true')
    args = parser.parse_args()
    backfill(season=args.season, commit=args.commit)
