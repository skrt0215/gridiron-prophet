import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch_games import NFLGameFetcher
import time

def fetch_multiple_weeks(season, start_week, end_week):
    """
    Fetch multiple weeks of NFL games
    
    Args:
        season: Year of the season (e.g., 2025)
        start_week: First week to fetch (e.g., 1)
        end_week: Last week to fetch (e.g., 5)
    """
    fetcher = NFLGameFetcher()
    
    print("=" * 70)
    print(f"Fetching {season} NFL Season - Weeks {start_week} to {end_week}")
    print("=" * 70)
    
    total_games = 0
    
    for week in range(start_week, end_week + 1):
        print(f"\n{'=' * 70}")
        print(f"WEEK {week}")
        print(f"{'=' * 70}")
        
        games = fetcher.fetch_scoreboard(season=season, week=week)
        
        if games:
            print(f"Found {len(games)} games for Week {week}")
            added = fetcher.save_games_to_db(games)
            total_games += added
            print(f"Added {added} games")
        else:
            print(f"No games found for Week {week}")
        
        if week < end_week:
            time.sleep(1)
    
    print(f"\n{'=' * 70}")
    print(f"✓ COMPLETE: Added {total_games} total games to database")
    print(f"{'=' * 70}")
    print("\nDatabase Summary:")
    all_games = fetcher.db.execute_query("""
        SELECT 
            season,
            week,
            COUNT(*) as game_count,
            SUM(CASE WHEN game_status = 'Final' THEN 1 ELSE 0 END) as completed_games
        FROM games
        WHERE season = %s AND week BETWEEN %s AND %s
        GROUP BY season, week
        ORDER BY week
    """, (season, start_week, end_week))
    
    for game in all_games:
        print(f"  Week {game['week']}: {game['game_count']} games ({game['completed_games']} completed)")

if __name__ == "__main__":
    seasons_to_fetch = [
        (2022, 1, 18),
        (2023, 1, 18),
        (2024, 1, 18),
    ]
    
    print("=" * 70)
    print("FETCHING MULTIPLE NFL SEASONS")
    print("=" * 70)
    
    for season, start_week, end_week in seasons_to_fetch:
        print(f"\n\n{'#' * 70}")
        print(f"# STARTING SEASON {season}")
        print(f"{'#' * 70}\n")
        
        fetch_multiple_weeks(season, start_week, end_week)
        time.sleep(2)
    
    print("\n\n" + "=" * 70)
    print("ALL SEASONS COMPLETE!")
    print("=" * 70)