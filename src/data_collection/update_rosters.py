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
        self.db.execute_update("DELETE FROM injuries")
        print("  ✓ Cleared injuries")
        
        self.db.execute_update("DELETE FROM depth_charts")
        print("  ✓ Cleared depth charts")
        
        self.db.execute_update("DELETE FROM players")
        print("  ✓ Cleared players")
        
        return True
    
    def import_rosters(self, seasons=[2024, 2025]):
        """Import rosters from nfl_data_py"""
        print(f"\nImporting rosters for seasons: {seasons}...")
        
        try:
            rosters_df = nfl.import_seasonal_rosters(seasons)
            print(f"Found {len(rosters_df)} player records")
            
            added_count = 0
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
                
                # Extract player info
                name = player.get('player_name') or player.get('full_name', 'Unknown')
                position = player.get('position', 'UNK')
                jersey = player.get('jersey_number')
                height = player.get('height')
                weight = player.get('weight')
                
                # Add player to database
                try:
                    self.db.add_player(
                        name=name,
                        team_id=team_id,
                        position=position,
                        jersey_number=jersey,
                        height=height,
                        weight=weight,
                        status='Active'
                    )
                    added_count += 1
                    
                    if added_count % 100 == 0:
                        print(f"  Progress: {added_count} players added...")
                        
                except Exception as e:
                    # Skip duplicates or errors
                    skipped_count += 1
                    if "Duplicate" not in str(e):
                        print(f"  Warning: Could not add {name}: {e}")
            
            print(f"\n✓ Added {added_count} players")
            print(f"✓ Skipped {skipped_count} records")
            
        except Exception as e:
            print(f"Error importing rosters: {e}")
            import traceback
            traceback.print_exc()
    
    def verify_rosters(self):
        """Verify roster data is correct"""
        print("\n" + "="*60)
        print("ROSTER VERIFICATION")
        print("="*60)
        
        # Get total players
        result = self.db.execute_query("SELECT COUNT(*) as count FROM players")
        total_players = result[0]['count']
        print(f"\nTotal players in database: {total_players}")
        
        # Get players per team
        result = self.db.execute_query("""
            SELECT t.abbreviation, t.name, COUNT(p.player_id) as player_count
            FROM teams t
            LEFT JOIN players p ON t.team_id = p.team_id
            GROUP BY t.team_id
            ORDER BY player_count DESC
        """)
        
        print("\nPlayers per team:")
        for r in result:
            print(f"  {r['abbreviation']:5} {r['name']:30} {r['player_count']:3} players")
        
        # Show sample of Jets roster
        print("\n" + "-"*60)
        print("Sample: New York Jets Roster")
        print("-"*60)
        
        result = self.db.execute_query("""
            SELECT p.name, p.position, p.jersey_number
            FROM players p
            JOIN teams t ON p.team_id = t.team_id
            WHERE t.abbreviation = 'NYJ'
            ORDER BY p.position, p.name
            LIMIT 20
        """)
        
        for r in result:
            jersey = f"#{r['jersey_number']}" if r['jersey_number'] else ""
            print(f"  {r['position']:5} {jersey:5} {r['name']}")
    
    def run_full_update(self):
        """Run complete roster update"""
        print("="*60)
        print("NFL ROSTER UPDATER")
        print("="*60)
        
        # Clear old data
        if not self.clear_old_rosters():
            return
        
        # Import fresh rosters
        self.import_rosters(seasons=[2025])
        
        # Verify
        self.verify_rosters()
        
        print("\n✓ Roster update complete!")
        print("\nNote: You'll need to re-run the injury fetcher to rebuild injury data")

if __name__ == "__main__":
    updater = RosterUpdater()
    updater.run_full_update()