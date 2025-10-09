import nfl_data_py as nfl
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DatabaseManager

class RosterUpdater:
    """Update team rosters with clean data from nfl_data_py"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def clear_old_rosters(self):
        """Clear existing player data (keeps teams and games intact)"""
        print("\n⚠️  WARNING: This will delete all player data and related records")
        response = input("Are you sure you want to continue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Aborted.")
            return False
        
        print("\nClearing old roster data...")
        
        # Delete in order due to foreign keys
        self.db.execute_update("DELETE FROM player_game_stats")
        print("  ✓ Cleared player game stats")
        
        self.db.execute_update("DELETE FROM player_seasons")
        print("  ✓ Cleared player seasons")
        
        self.db.execute_update("DELETE FROM injuries")
        print("  ✓ Cleared injuries")
        
        self.db.execute_update("DELETE FROM depth_charts")
        print("  ✓ Cleared depth charts")
        
        self.db.execute_update("DELETE FROM players")
        print("  ✓ Cleared players")
        
        return True
    
    def determine_roster_status(self, player_row):
        """Determine if player is Active, Practice Squad, IR, etc."""
        status = player_row.get('status', '').upper()
        
        # Map status from nfl_data_py to our categories
        if status in ['ACT', 'ACTIVE', '']:
            return 'Active'
        elif 'PRACTICE' in status or status == 'PRA':
            return 'Practice Squad'
        elif 'INJURED' in status or status in ['IR', 'RES', 'RESERVE']:
            return 'Injured Reserve'
        elif 'PUP' in status:
            return 'PUP'
        elif 'NFI' in status:
            return 'NFI'
        elif 'SUSPENDED' in status or status == 'SUS':
            return 'Suspended'
        else:
            # Default to Active if uncertain (we'll verify counts later)
            return 'Active'
    
    def import_rosters(self, seasons=[2024, 2025]):
        """Import rosters from nfl_data_py with proper status tracking"""
        print(f"\nImporting rosters for seasons: {seasons}...")
        
        try:
            rosters_df = nfl.import_seasonal_rosters(seasons)
            print(f"Found {len(rosters_df)} player records")
            
            added_players = 0
            added_seasons = 0
            skipped_count = 0
            
            for _, player in rosters_df.iterrows():
                # Get team
                team_abbr = player.get('team')
                team = self.db.get_team_by_abbreviation(team_abbr)
                
                if not team:
                    print(f"  Warning: Team not found for {team_abbr}")
                    skipped_count += 1
                    continue
                
                team_id = team['team_id']
                season = player.get('season', 2025)
                
                # Extract player info
                name = player.get('player_name') or player.get('full_name', 'Unknown')
                position = player.get('position', 'UNK')
                jersey = player.get('jersey_number')
                height = player.get('height')
                weight = player.get('weight')
                age = player.get('age')
                years_exp = player.get('years_exp') or player.get('entry_year')
                
                # Determine roster status
                roster_status = self.determine_roster_status(player)
                
                # Add player to players table (if not exists)
                try:
                    player_id = self.db.add_player(
                        name=name,
                        team_id=team_id,
                        position=position,
                        jersey_number=jersey,
                        height=height,
                        weight=weight,
                        age=age,
                        years_in_league=years_exp,
                        status='Active'  # Keep this for legacy compatibility
                    )
                    
                    if player_id:
                        added_players += 1
                    
                except Exception as e:
                    # Player might already exist, get their ID
                    result = self.db.execute_query(
                        "SELECT player_id FROM players WHERE name = %s AND team_id = %s",
                        (name, team_id)
                    )
                    if result:
                        player_id = result[0]['player_id']
                    else:
                        print(f"  Warning: Could not add/find {name}: {e}")
                        skipped_count += 1
                        continue
                
                # Add to player_seasons table
                try:
                    self.db.execute_update("""
                        INSERT INTO player_seasons 
                        (player_id, season, team_id, position, jersey_number, age, 
                         years_in_league, roster_status, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Active')
                        ON DUPLICATE KEY UPDATE
                        position = VALUES(position),
                        jersey_number = VALUES(jersey_number),
                        roster_status = VALUES(roster_status)
                    """, (player_id, season, team_id, position, jersey, age, years_exp, roster_status))
                    
                    added_seasons += 1
                    
                    if added_seasons % 100 == 0:
                        print(f"  Progress: {added_seasons} player-seasons added...")
                        
                except Exception as e:
                    skipped_count += 1
                    if "Duplicate" not in str(e):
                        print(f"  Warning: Could not add season for {name}: {e}")
            
            print(f"\n✓ Added {added_players} unique players")
            print(f"✓ Added {added_seasons} player-season records")
            print(f"✓ Skipped {skipped_count} records")
            
        except Exception as e:
            print(f"Error importing rosters: {e}")
            import traceback
            traceback.print_exc()
    
    def verify_rosters(self, season=2025):
        """Verify roster data is correct"""
        print("\n" + "="*60)
        print(f"ROSTER VERIFICATION - {season} Season")
        print("="*60)
        
        # Get players per team with roster status breakdown
        result = self.db.execute_query("""
            SELECT 
                t.abbreviation,
                t.name,
                COUNT(CASE WHEN ps.roster_status = 'Active' THEN 1 END) as active,
                COUNT(CASE WHEN ps.roster_status = 'Practice Squad' THEN 1 END) as practice_squad,
                COUNT(CASE WHEN ps.roster_status = 'Injured Reserve' THEN 1 END) as injured_reserve,
                COUNT(*) as total
            FROM teams t
            LEFT JOIN player_seasons ps ON t.team_id = ps.team_id AND ps.season = %s
            GROUP BY t.team_id
            ORDER BY active DESC
        """, (season,))
        
        print("\nRoster breakdown by team:")
        print(f"{'Team':<5} {'Active':<8} {'Practice':<10} {'IR':<6} {'Total':<6}")
        print("-" * 60)
        
        teams_with_issues = []
        for r in result:
            print(f"{r['abbreviation']:<5} {r['active']:<8} {r['practice_squad']:<10} {r['injured_reserve']:<6} {r['total']:<6}")
            
            # Flag teams with incorrect active roster count
            if r['active'] != 53 and r['active'] > 0:
                teams_with_issues.append((r['abbreviation'], r['active']))
        
        if teams_with_issues:
            print("\n⚠️  WARNING: These teams don't have exactly 53 active players:")
            for team, count in teams_with_issues:
                print(f"  {team}: {count} players (should be 53)")
            print("\nThis means nfl_data_py doesn't properly distinguish active roster.")
            print("You may need to manually verify/update using official NFL sources.")
        else:
            print("\n✓ All teams have exactly 53 active players!")
        
        # Show sample of a team's roster
        print("\n" + "-"*60)
        print("Sample: New York Giants Active Roster")
        print("-"*60)
        
        result = self.db.execute_query("""
            SELECT p.name, ps.position, ps.jersey_number, ps.roster_status
            FROM player_seasons ps
            JOIN players p ON ps.player_id = p.player_id
            JOIN teams t ON ps.team_id = t.team_id
            WHERE t.abbreviation = 'NYG' AND ps.season = %s AND ps.roster_status = 'Active'
            ORDER BY 
                CASE ps.position
                    WHEN 'QB' THEN 1 WHEN 'RB' THEN 2 WHEN 'WR' THEN 3
                    WHEN 'TE' THEN 4 WHEN 'OL' THEN 5 ELSE 6
                END,
                p.name
            LIMIT 20
        """, (season,))
        
        for r in result:
            jersey = f"#{r['jersey_number']}" if r['jersey_number'] else ""
            print(f"  {r['position']:<5} {jersey:<5} {r['name']:<30} [{r['roster_status']}]")
    
    def run_full_update(self):
        """Run complete roster update"""
        print("="*60)
        print("NFL ROSTER UPDATER")
        print("="*60)
        
        # Clear old data
        if not self.clear_old_rosters():
            return
        
        # Import fresh rosters (2024 + 2025 to track team changes)
        self.import_rosters(seasons=[2024, 2025])
        
        # Verify
        self.verify_rosters(season=2025)
        
        print("\n✓ Roster update complete!")
        print("\nNote: You'll need to re-run the injury fetcher to rebuild injury data")

if __name__ == "__main__":
    updater = RosterUpdater()
    updater.run_full_update()