import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nfl_data_py as nfl
from database.db_manager import DatabaseManager

def fetch_snap_counts(seasons):
    """
    Fetch snap count data for NFL players - V2 schema compatible
    
    Args:
        seasons: List of seasons to fetch (e.g., [2022, 2023, 2024])
    """
    db = DatabaseManager()
    
    print("=" * 70)
    print("FETCHING SNAP COUNT DATA - V2")
    print("=" * 70)
    
    print("\nDownloading snap count data from nfl_data_py...")
    snap_data = nfl.import_snap_counts(seasons)
    
    print(f"Found {len(snap_data)} snap count records")
    
    updated_count = 0
    added_to_depth = 0
    skipped_count = 0
    
    for idx, row in snap_data.iterrows():
        try:
            player_name = row['player']
            team_abbr = row['team']
            position = row['position']
            season = int(row['season'])
            week = int(row['week'])
            
            team = db.get_team_by_abbreviation(team_abbr)
            if not team:
                skipped_count += 1
                continue
            
            team_id = team['team_id']
            
            player = db.execute_query("""
                SELECT p.player_id 
                FROM players p
                JOIN player_seasons ps ON p.player_id = ps.player_id
                WHERE p.name = %s 
                AND ps.team_id = %s 
                AND ps.season = %s
                AND p.position = %s
                LIMIT 1
            """, (player_name, team_id, season, position))
            
            if not player:
                player = db.execute_query("""
                    SELECT player_id 
                    FROM players 
                    WHERE name = %s AND position = %s
                    LIMIT 1
                """, (player_name, position))
            
            if not player:
                skipped_count += 1
                continue
            
            player_id = player[0]['player_id'] 
            offense_snaps = row.get('offense_snaps', 0) or 0
            defense_snaps = row.get('defense_snaps', 0) or 0
            st_snaps = row.get('st_snaps', 0) or 0
            offense_pct = row.get('offense_pct', 0) or 0
            defense_pct = row.get('defense_pct', 0) or 0
            snap_percentage = max(offense_pct, defense_pct) * 100
            
            existing = db.execute_query("""
                SELECT depth_chart_id FROM depth_charts
                WHERE team_id = %s AND player_id = %s 
                AND position = %s AND season = %s AND week = %s
            """, (team_id, player_id, position, season, week))
            
            if existing:
                db.execute_update("""
                    UPDATE depth_charts
                    SET snap_percentage = %s,
                        offense_snaps = %s,
                        defense_snaps = %s,
                        special_teams_snaps = %s
                    WHERE depth_chart_id = %s
                """, (snap_percentage, offense_snaps, defense_snaps, st_snaps, 
                      existing[0]['depth_chart_id']))
                updated_count += 1
            else:
                db.execute_insert("""
                    INSERT INTO depth_charts 
                    (team_id, player_id, position, depth_order, season, week, 
                     snap_percentage, offense_snaps, defense_snaps, special_teams_snaps)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (team_id, player_id, position, 99, season, week, 
                      snap_percentage, offense_snaps, defense_snaps, st_snaps))
                added_to_depth += 1
            
            if (updated_count + added_to_depth) % 500 == 0:
                print(f"  Progress: {updated_count + added_to_depth} records processed...")
                
        except Exception as e:
            if "Duplicate entry" not in str(e):
                print(f"Error processing {row.get('player', 'unknown')}: {e}")
            skipped_count += 1
    
    print(f"\n{'=' * 70}")
    print(f"✓ Updated {updated_count} existing depth chart entries")
    print(f"✓ Added {added_to_depth} new depth chart entries with snap counts")
    print(f"✓ Skipped {skipped_count} records (player not found)")
    print(f"{'=' * 70}")
    
    summary = db.execute_query("""
        SELECT season, COUNT(*) as entries, 
               AVG(snap_percentage) as avg_snap_pct,
               COUNT(DISTINCT player_id) as unique_players
        FROM depth_charts
        WHERE snap_percentage IS NOT NULL
        GROUP BY season
        ORDER BY season
    """)
    
    print("\nSnap Count Summary by Season:")
    for row in summary:
        print(f"  {row['season']}: {row['entries']} entries, "
              f"{row['unique_players']} players, "
              f"avg snap % = {row['avg_snap_pct']:.1f}%")
    
    print("\nTop 10 Players by Average Snap % (2024):")
    
    top_players = db.execute_query("""
        SELECT p.name, p.position, 
               (SELECT t.abbreviation 
                FROM teams t 
                JOIN player_seasons ps ON t.team_id = ps.team_id 
                WHERE ps.player_id = p.player_id AND ps.season = 2024 
                LIMIT 1) as team,
               AVG(dc.snap_percentage) as avg_snaps,
               COUNT(*) as weeks_played
        FROM depth_charts dc
        JOIN players p ON dc.player_id = p.player_id
        WHERE dc.season = 2024 AND dc.snap_percentage > 0
        GROUP BY p.player_id, p.name, p.position
        HAVING weeks_played >= 5
        ORDER BY avg_snaps DESC
        LIMIT 10
    """)
    
    for player in top_players:
        team_display = player['team'] if player['team'] else 'N/A'
        print(f"  {player['name']:25} ({player['position']}) {team_display} - "
              f"{player['avg_snaps']:.1f}% over {player['weeks_played']} weeks")

if __name__ == "__main__":
    seasons = [2022, 2023, 2024, 2025]
    fetch_snap_counts(seasons)