import nfl_data_py as nfl
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DatabaseManager

class RosterUpdaterV2:
    """Update team rosters with V2 multi-season schema"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def clear_old_rosters(self):
        """Clear existing roster data but keep structure"""
        print("\n⚠️  WARNING: This will delete player_seasons data")
        response = input("Are you sure you want to continue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Aborted.")
            return False
        
        print("\nClearing old roster data...")
        self.db.execute_update("DELETE FROM player_seasons")
        print("  ✓ Cleared player_seasons")
        
        return True
    
    def get_or_create_player(self, name, position, height=None, weight=None, college=None):
        """Get existing player or create new one in master players table"""
        result = self.db.execute_query(
            "SELECT player_id FROM players WHERE name = %s AND position = %s",
            (name, position)
        )
        
        if result:
            return result[0]['player_id']
        
        player_id = self.db.execute_insert("""
            INSERT INTO players (name, position, height, weight, college)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, position, height, weight, college))
        
        return player_id
    
    def import_rosters(self, seasons=[2022, 2023, 2024, 2025]):
        """Import rosters for multiple seasons"""
        print(f"\nImporting rosters for seasons: {seasons}...")
        
        try:
            rosters_df = nfl.import_seasonal_rosters(seasons)
            print(f"Found {len(rosters_df)} player-season records")
            
            players_created = 0
            seasons_added = 0
            skipped_count = 0
            
            for _, player in rosters_df.iterrows():
                try:
                    team_abbr = player.get('team')
                    team = self.db.get_team_by_abbreviation(team_abbr)
                    
                    if not team:
                        skipped_count += 1
                        continue
                    
                    team_id = team['team_id']
                    season = int(player.get('season', 2024))
                    
                    name = player.get('player_name') or player.get('full_name', 'Unknown')
                    position = player.get('position', 'UNK')
                    jersey = player.get('jersey_number')
                    height = player.get('height')
                    weight = player.get('weight')
                    college = player.get('college')
                    
                    player_id = self.get_or_create_player(name, position, height, weight, college)
                    
                    if not player_id:
                        skipped_count += 1
                        continue
                    
                    existing = self.db.execute_query(
                        "SELECT player_season_id FROM player_seasons WHERE player_id = %s AND season = %s",
                        (player_id, season)
                    )
                    
                    if existing:
                        self.db.execute_update("""
                            UPDATE player_seasons 
                            SET team_id = %s, position = %s, jersey_number = %s, status = 'Active'
                            WHERE player_season_id = %s
                        """, (team_id, position, jersey, existing[0]['player_season_id']))
                    else:
                        self.db.execute_insert("""
                            INSERT INTO player_seasons 
                            (player_id, season, team_id, position, jersey_number, status)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (player_id, season, team_id, position, jersey, 'Active'))
                        seasons_added += 1
                    
                    if seasons_added % 500 == 0:
                        print(f"  Progress: {seasons_added} player-season records added...")
                        
                except Exception as e:
                    if "Duplicate entry" not in str(e):
                        print(f"  Warning: Error processing player: {e}")
                    skipped_count += 1
            
            print(f"\n✓ Added {seasons_added} player-season records")
            print(f"✓ Skipped {skipped_count} records")
            
        except Exception as e:
            print(f"Error importing rosters: {e}")
            import traceback
            traceback.print_exc()
    
    def verify_rosters(self):
        """Verify roster data is correct"""
        print("\n" + "="*70)
        print("ROSTER VERIFICATION")
        print("="*70)
        
        result = self.db.execute_query("SELECT COUNT(DISTINCT player_id) as count FROM players")
        unique_players = result[0]['count']
        print(f"\nUnique players in database: {unique_players}")
        
        result = self.db.execute_query("SELECT COUNT(*) as count FROM player_seasons")
        total_seasons = result[0]['count']
        print(f"Total player-season records: {total_seasons}")
        
        result = self.db.execute_query("""
            SELECT season, COUNT(*) as count, COUNT(DISTINCT player_id) as unique_players
            FROM player_seasons
            GROUP BY season
            ORDER BY season
        """)
        
        print("\nRoster data by season:")
        for r in result:
            print(f"  {r['season']}: {r['count']} records ({r['unique_players']} unique players)")
        
        result = self.db.execute_query("""
            SELECT t.abbreviation, COUNT(ps.player_season_id) as player_count
            FROM teams t
            LEFT JOIN player_seasons ps ON t.team_id = ps.team_id AND ps.season = 2025
            GROUP BY t.team_id
            ORDER BY player_count DESC
            LIMIT 10
        """)
        
        print("\nTop 10 teams by 2025 roster size:")
        for r in result:
            print(f"  {r['abbreviation']:5} {r['player_count']:3} players")
        
        print("\n" + "-"*70)
        print("Sample: Kansas City Chiefs 2025 Roster")
        print("-"*70)
        
        result = self.db.execute_query("""
            SELECT p.name, ps.position, ps.jersey_number
            FROM player_seasons ps
            JOIN players p ON ps.player_id = p.player_id
            JOIN teams t ON ps.team_id = t.team_id
            WHERE t.abbreviation = 'KC' AND ps.season = 2025
            ORDER BY ps.position, p.name
            LIMIT 20
        """)
        
        for r in result:
            jersey = f"#{r['jersey_number']}" if r['jersey_number'] else ""
            print(f"  {r['position']:5} {jersey:5} {r['name']}")
        
        print("\n" + "-"*70)
        print("Players who changed teams (2024 -> 2025):")
        print("-"*70)
        
        result = self.db.execute_query("""
            SELECT p.name, p.position,
                   t1.abbreviation as team_2024,
                   t2.abbreviation as team_2025
            FROM players p
            JOIN player_seasons ps1 ON p.player_id = ps1.player_id AND ps1.season = 2024
            JOIN player_seasons ps2 ON p.player_id = ps2.player_id AND ps2.season = 2025
            JOIN teams t1 ON ps1.team_id = t1.team_id
            JOIN teams t2 ON ps2.team_id = t2.team_id
            WHERE ps1.team_id != ps2.team_id
            ORDER BY p.name
            LIMIT 15
        """)
        
        if result:
            for r in result:
                print(f"  {r['name']:25} ({r['position']}) {r['team_2024']} -> {r['team_2025']}")
        else:
            print("  No team changes detected")
    
    def run_full_update(self, seasons=[2022, 2023, 2024, 2025]):
        """Run complete roster update for multiple seasons"""
        print("="*70)
        print("NFL ROSTER UPDATER V2 - Multi-Season")
        print("="*70)
        
        if not self.clear_old_rosters():
            return
        
        self.import_rosters(seasons=seasons)
        
        self.verify_rosters()
        
        print("\n✓ Roster update complete!")
        print("\nNext steps:")
        print("1. Run: python src/data_collection/fetch_snap_counts.py")
        print("2. Run: python src/data_collection/fetch_injuries.py")

if __name__ == "__main__":
    updater = RosterUpdaterV2()
    updater.run_full_update(seasons=[2022, 2023, 2024, 2025])