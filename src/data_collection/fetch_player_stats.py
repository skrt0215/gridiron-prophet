import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nfl_data_py as nfl
from database.db_manager import DatabaseManager
import pandas as pd

def fetch_player_stats(seasons):
    """
    Fetch player game statistics using nfl_data_py
    
    Args:
        seasons: List of seasons to fetch (e.g., [2022, 2023, 2024])
    """
    db = DatabaseManager()
    
    print("=" * 70)
    print("FETCHING PLAYER STATISTICS")
    print("=" * 70)
    
    # Fetch weekly player stats
    print("\nDownloading player statistics from nfl_data_py...")
    print("This may take a few minutes...")
    
    stats = nfl.import_weekly_data(seasons)
    
    print(f"\nFound {len(stats)} player-game records")
    
    added_count = 0
    skipped_count = 0
    player_cache = {}  # Cache player lookups
    
    for idx, row in stats.iterrows():
        try:
            # Get player
            player_name = row['player_display_name']
            
            # Check cache first
            if player_name in player_cache:
                player_id = player_cache[player_name]
            else:
                # Look up or create player
                player = db.execute_query(
                    "SELECT player_id FROM players WHERE name = %s LIMIT 1",
                    (player_name,)
                )
                
                if player:
                    player_id = player[0]['player_id']
                else:
                    # Create new player
                    team = db.get_team_by_abbreviation(row['recent_team'])
                    team_id = team['team_id'] if team else None
                    
                    player_id = db.add_player(
                        name=player_name,
                        team_id=team_id,
                        position=row['position']
                    )
                    print(f"  + Added new player: {player_name} ({row['position']})")
                
                player_cache[player_name] = player_id
            
            # Find the corresponding game
            opponent_team = db.get_team_by_abbreviation(row['opponent_team'])
            recent_team = db.get_team_by_abbreviation(row['recent_team'])
            
            if not opponent_team or not recent_team:
                skipped_count += 1
                continue
            
            # Find game in database
            game = db.execute_query("""
                SELECT game_id, home_team_id, away_team_id 
                FROM games 
                WHERE season = %s 
                AND week = %s 
                AND (
                    (home_team_id = %s AND away_team_id = %s) OR
                    (home_team_id = %s AND away_team_id = %s)
                )
                LIMIT 1
            """, (
                int(row['season']),
                int(row['week']),
                recent_team['team_id'], opponent_team['team_id'],
                opponent_team['team_id'], recent_team['team_id']
            ))
            
            if not game:
                skipped_count += 1
                continue
            
            game_id = game[0]['game_id']
            
            # Add player game stats
            stat_id = db.execute_insert("""
                INSERT INTO player_game_stats (
                    game_id, player_id, team_id,
                    pass_attempts, pass_completions, pass_yards, pass_touchdowns, interceptions, sacks_taken,
                    rush_attempts, rush_yards, rush_touchdowns,
                    targets, receptions, receiving_yards, receiving_touchdowns,
                    tackles, tackles_for_loss, sacks, forced_fumbles, fumble_recoveries,
                    interceptions_defense, passes_defended,
                    fumbles, fumbles_lost
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s
                )
            """, (
                game_id, player_id, recent_team['team_id'],
                # Passing
                int(row.get('attempts', 0) or 0),
                int(row.get('completions', 0) or 0),
                int(row.get('passing_yards', 0) or 0),
                int(row.get('passing_tds', 0) or 0),
                int(row.get('interceptions', 0) or 0),
                int(row.get('sacks', 0) or 0),
                # Rushing
                int(row.get('carries', 0) or 0),
                int(row.get('rushing_yards', 0) or 0),
                int(row.get('rushing_tds', 0) or 0),
                # Receiving
                int(row.get('targets', 0) or 0),
                int(row.get('receptions', 0) or 0),
                int(row.get('receiving_yards', 0) or 0),
                int(row.get('receiving_tds', 0) or 0),
                # Defense (these fields may not exist in the dataset)
                0, 0, 0, 0, 0, 0, 0,
                # Misc
                int(row.get('fumbles', 0) or 0),
                int(row.get('fumbles_lost', 0) or 0)
            ))
            
            added_count += 1
            
            if added_count % 100 == 0:
                print(f"  Progress: {added_count} stats added...")
            
        except Exception as e:
            if "Duplicate entry" not in str(e):
                print(f"✗ Error: {e}")
            skipped_count += 1
    
    print(f"\n{'=' * 70}")
    print(f"✓ Added {added_count} player game stats")
    print(f"- Skipped {skipped_count} records")
    print(f"{'=' * 70}")
    
    # Show summary
    print("\nDatabase Summary:")
    
    players = db.execute_query("SELECT COUNT(*) as count FROM players")
    print(f"  Total players: {players[0]['count']}")
    
    stats_summary = db.execute_query("""
        SELECT season, COUNT(*) as stat_count
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        GROUP BY season
        ORDER BY season
    """)
    
    print("\n  Stats by season:")
    for row in stats_summary:
        print(f"    {row['season']}: {row['stat_count']} player-game records")

if __name__ == "__main__":
    # Fetch stats for 2022-2024 (complete seasons)
    # We'll fetch 2025 separately as it's ongoing
    seasons = [2022, 2023, 2024]
    fetch_player_stats(seasons)