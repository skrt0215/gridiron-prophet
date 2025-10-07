import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nfl_data_py as nfl
from database.db_manager import DatabaseManager
import pandas as pd

def fetch_snap_counts(seasons):
    """
    Fetch snap count data for NFL players
    
    Args:
        seasons: List of seasons to fetch (e.g., [2022, 2023, 2024])
    """
    db = DatabaseManager()
    
    print("=" * 70)
    print("FETCHING SNAP COUNT DATA")
    print("=" * 70)
    
    print("\nDownloading snap count data from nfl_data_py...")
    snap_data = nfl.import_snap_counts(seasons)
    
    print(f"Found {len(snap_data)} snap count records")
    
    updated_count = 0
    added_to_depth = 0
    
    for idx, row in snap_data.iterrows():
        try:
            # Get player
            player = db.execute_query(
                "SELECT player_id FROM players WHERE name = %s LIMIT 1",
                (row['player'],)
            )
            
            if not player:
                continue
            
            player_id = player[0]['player_id']
            
            # Get team
            team = db.get_team_by_abbreviation(row['team'])
            if not team:
                continue
            
            team_id = team['team_id']
            
            # Calculate snap percentage
            offense_snaps = row.get('offense_snaps', 0) or 0
            defense_snaps = row.get('defense_snaps', 0) or 0
            st_snaps = row.get('st_snaps', 0) or 0
            
            offense_pct = row.get('offense_pct', 0) or 0
            defense_pct = row.get('defense_pct', 0) or 0
            
            # Determine primary snap percentage
            snap_percentage = max(offense_pct, defense_pct)
            
            # Update or insert depth chart entry
            season = int(row['season'])
            week = int(row['week'])
            position = row['position']
            
            # Check if depth chart entry exists
            existing = db.execute_query("""
                SELECT depth_chart_id FROM depth_charts
                WHERE team_id = %s AND player_id = %s 
                AND position = %s AND season = %s AND week = %s
            """, (team_id, player_id, position, season, week))
            
            if existing:
                # Update existing entry
                db.execute_update("""
                    UPDATE depth_charts
                    SET snap_percentage = %s
                    WHERE depth_chart_id = %s
                """, (snap_percentage, existing[0]['depth_chart_id']))
                updated_count += 1
            else:
                # Insert new depth chart entry
                db.execute_insert("""
                    INSERT INTO depth_charts 
                    (team_id, player_id, position, depth_order, season, week, snap_percentage)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (team_id, player_id, position, 99, season, week, snap_percentage))
                added_to_depth += 1
            
            if (updated_count + added_to_depth) % 100 == 0:
                print(f"  Progress: {updated_count + added_to_depth} records processed...")
                
        except Exception as e:
            if "Duplicate entry" not in str(e):
                print(f"Error processing {row.get('player', 'unknown')}: {e}")
    
    print(f"\n{'=' * 70}")
    print(f"✓ Updated {updated_count} existing depth chart entries")
    print(f"✓ Added {added_to_depth} new depth chart entries with snap counts")
    print(f"{'=' * 70}")
    
    # Show summary
    summary = db.execute_query("""
        SELECT season, COUNT(*) as entries, 
               AVG(snap_percentage) as avg_snap_pct
        FROM depth_charts
        WHERE snap_percentage IS NOT NULL
        GROUP BY season
        ORDER BY season
    """)
    
    print("\nSnap Count Summary by Season:")
    for row in summary:
        print(f"  {row['season']}: {row['entries']} entries, avg snap % = {row['avg_snap_pct']:.1f}%")

if __name__ == "__main__":
    # Fetch snap counts for 2022-2024
    seasons = [2022, 2023, 2024]
    fetch_snap_counts(seasons)