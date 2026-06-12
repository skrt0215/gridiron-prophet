import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nflreadpy as nfl
from database.db_manager import DatabaseManager
from datetime import datetime

TEAM_ABBR_MAP = {
    'LA': 'LAR',
    'OAK': 'LV',
    'SD': 'LAC',
    'STL': 'LAR',
}

def normalize_team(abbr):
    if abbr is None:
        return None
    return TEAM_ABBR_MAP.get(abbr, abbr)

def fetch_historical_games(seasons):
    db = DatabaseManager()

    print("=" * 70)
    print("FETCHING NFL GAMES")
    print("=" * 70)
    print(f"\nSeasons: {', '.join(map(str, seasons))}")
    print("Downloading schedule data from nflreadpy...")

    schedule = nfl.load_schedules(seasons).to_pandas()

    print(f"Found {len(schedule)} total games")
    print("COLUMNS:", list(schedule.columns))

    added_count = 0
    skipped_count = 0

    for _, game in schedule.iterrows():
        try:
            home_abbr = normalize_team(game['home_team'])
            away_abbr = normalize_team(game['away_team'])

            home_team = db.get_team_by_abbreviation(home_abbr)
            away_team = db.get_team_by_abbreviation(away_abbr)

            if not home_team or not away_team:
                print(f"Skipping: Could not find teams {away_abbr} @ {home_abbr}")
                skipped_count += 1
                continue

            game_date = datetime.strptime(str(game['gameday']), '%Y-%m-%d').date()
            game_time = None
            if 'gametime' in game and game['gametime'] is not None and str(game['gametime']) != 'nan':
                try:
                    game_time = datetime.strptime(str(game['gametime']), '%H:%M:%S').time()
                except (ValueError, TypeError):
                    try:
                        game_time = datetime.strptime(str(game['gametime']), '%H:%M').time()
                    except (ValueError, TypeError):
                        pass

            home_score = game['home_score']
            away_score = game['away_score']

            has_home = home_score is not None and str(home_score) != 'nan'
            has_away = away_score is not None and str(away_score) != 'nan'

            game_status = 'Final' if has_home else 'Scheduled'

            roof_val = game['roof'] if 'roof' in game else None
            is_dome = str(roof_val) == 'dome'

            stadium_val = game['stadium'] if 'stadium' in game else None
            if stadium_val is not None and str(stadium_val) == 'nan':
                stadium_val = None

            db.add_game(
                season=int(game['season']),
                week=int(game['week']),
                game_date=game_date,
                game_time=game_time,
                home_team_id=home_team['team_id'],
                away_team_id=away_team['team_id'],
                home_score=int(home_score) if has_home else None,
                away_score=int(away_score) if has_away else None,
                stadium=stadium_val,
                is_dome=is_dome,
                game_status=game_status
            )

            score_str = ""
            if game_status == 'Final':
                score_str = f" | Final: {away_abbr} {int(away_score)}, {home_abbr} {int(home_score)}"

            print(f"+ {game['season']} Week {game['week']}: {away_abbr} @ {home_abbr}{score_str}")
            added_count += 1

        except Exception as e:
            if "Duplicate entry" in str(e):
                skipped_count += 1
            else:
                print(f"Error: {e}")
                skipped_count += 1

    print(f"\n{'=' * 70}")
    print(f"Added {added_count} games")
    print(f"Skipped {skipped_count} games (duplicates or errors)")
    print(f"{'=' * 70}")
    print("\nDatabase Summary by Season:")
    summary = db.execute_query("""
        SELECT season, COUNT(*) as total_games,
               SUM(CASE WHEN game_status = 'Final' THEN 1 ELSE 0 END) as completed
        FROM games
        GROUP BY season
        ORDER BY season
    """)

    for row in summary:
        print(f"  {row['season']}: {row['total_games']} games ({row['completed']} completed)")

if __name__ == "__main__":
    seasons = [2022, 2023, 2024, 2025]
    fetch_historical_games(seasons)