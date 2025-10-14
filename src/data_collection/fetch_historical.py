import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nfl_data_py as nfl
from database.db_manager import DatabaseManager
from datetime import datetime

def fetch_historical_games(seasons):
    """
    Fetch historical NFL game data using nfl_data_py
    
    Args:
        seasons: List of seasons to fetch (e.g., [2022, 2023, 2024])
    """
    db = DatabaseManager()
    
    print("=" * 70)
    print("FETCHING HISTORICAL NFL GAMES")
    print("=" * 70)
    print("\nDownloading schedule data from nfl_data_py...")
    schedule = nfl.import_schedules(seasons)
    
    print(f"Found {len(schedule)} total games")
    
    added_count = 0
    skipped_count = 0
    
    for _, game in schedule.iterrows():
        try:
            home_team = db.get_team_by_abbreviation(game['home_team'])
            away_team = db.get_team_by_abbreviation(game['away_team'])
            
            if not home_team or not away_team:
                print(f"Skipping: Could not find teams {game['away_team']} @ {game['home_team']}")
                skipped_count += 1
                continue
            game_date = datetime.strptime(str(game['gameday']), '%Y-%m-%d').date()
            game_time = None
            if 'gametime' in game and game['gametime']:
                try:
                    game_time = datetime.strptime(str(game['gametime']), '%H:%M:%S').time()
                except:
                    pass
            
            game_status = 'Final' if game['home_score'] is not None else 'Scheduled'
            
            game_id = db.add_game(
                season=int(game['season']),
                week=int(game['week']),
                game_date=game_date,
                game_time=game_time,
                home_team_id=home_team['team_id'],
                away_team_id=away_team['team_id'],
                home_score=int(game['home_score']) if game['home_score'] is not None else None,
                away_score=int(game['away_score']) if game['away_score'] is not None else None,
                stadium=game.get('stadium'),
                is_dome=game.get('roof') == 'dome' if 'roof' in game else False,
                game_status=game_status
            )
            
            score_str = ""
            if game_status == 'Final':
                score_str = f" | Final: {game['away_team']} {int(game['away_score'])}, {game['home_team']} {int(game['home_score'])}"
            
            print(f"✓ {game['season']} Week {game['week']}: {game['away_team']} @ {game['home_team']}{score_str}")
            added_count += 1
            
        except Exception as e:
            if "Duplicate entry" in str(e):
                skipped_count += 1
            else:
                print(f"✗ Error: {e}")
    
    print(f"\n{'=' * 70}")
    print(f"✓ Added {added_count} games")
    print(f"- Skipped {skipped_count} games (duplicates or errors)")
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
    seasons = [2022, 2023, 2024]
    fetch_historical_games(seasons)