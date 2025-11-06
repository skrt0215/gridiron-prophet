import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nfl_data_py as nfl
from database.db_manager import DatabaseManager
import pandas as pd
from datetime import datetime

class SmartRosterUpdater:
    
    def __init__(self):
        self.db = DatabaseManager()
        self.updates_made = {
            'new_players': 0,
            'trades': 0,
            'status_changes': 0,
            'duplicates_removed': 0,
            'errors': []
        }
    
    def fetch_current_rosters(self):
        print("\n" + "="*70)
        print("FETCHING CURRENT 2025 ROSTERS")
        print("="*70)
        print("\nDownloading latest roster data...")
        
        try:
            rosters_df = nfl.import_seasonal_rosters([2025])
            print(f"✓ Found {len(rosters_df)} player records for 2025")
            return rosters_df
            
        except Exception as e:
            print(f"✗ Error fetching rosters: {e}")
            return None
    
    def determine_roster_status(self, status_str):
        if not status_str or pd.isna(status_str):
            return 'Active'
        
        status = str(status_str).upper().strip()
        
        if status in ['ACT', 'ACTIVE', '']:
            return 'Active'
        elif 'PRACTICE' in status or status in ['PRA', 'PS']:
            return 'Practice Squad'
        elif 'INJURED' in status or status in ['IR', 'RES', 'RESERVE']:
            return 'Injured Reserve'
        elif 'PUP' in status:
            return 'PUP'
        elif 'NFI' in status:
            return 'NFI'
        elif 'SUS' in status or 'SUSPEND' in status:
            return 'Suspended'
        else:
            return 'Active'
    
    def remove_duplicates(self):
        print("\n" + "="*70)
        print("CHECKING FOR DUPLICATE PLAYER_SEASONS")
        print("="*70)
        
        duplicates = self.db.execute_query("""
            SELECT 
                ps.player_id,
                p.name,
                COUNT(*) as count,
                GROUP_CONCAT(ps.player_season_id) as ids,
                GROUP_CONCAT(t.abbreviation) as teams
            FROM player_seasons ps
            JOIN players p ON ps.player_id = p.player_id
            JOIN teams t ON ps.team_id = t.team_id
            WHERE ps.season = 2025
            GROUP BY ps.player_id
            HAVING COUNT(*) > 1
        """)
        
        if not duplicates:
            print("✓ No duplicates found")
            return
        
        print(f"⚠️  Found {len(duplicates)} players with duplicate 2025 records")
        
        for dup in duplicates:
            ids = [int(x) for x in dup['ids'].split(',')]
            teams = dup['teams'].split(',')
            
            print(f"\n  Player: {dup['name']}")
            print(f"  Teams: {', '.join(teams)}")
            print(f"  Keeping most recent record, removing {len(ids)-1} duplicate(s)")
            
            keep_id = max(ids)
            remove_ids = [x for x in ids if x != keep_id]
            
            for remove_id in remove_ids:
                try:
                    self.db.execute_update(
                        "DELETE FROM player_seasons WHERE player_season_id = %s",
                        (remove_id,)
                    )
                    self.updates_made['duplicates_removed'] += 1
                except Exception as e:
                    self.updates_made['errors'].append(f"Error removing duplicate for {dup['name']}: {e}")
        
        print(f"\n✓ Removed {self.updates_made['duplicates_removed']} duplicate records")
    
    def update_rosters(self, rosters_df):
        print("\n" + "="*70)
        print("UPDATING ROSTERS")
        print("="*70)
        
        processed = 0
        skipped = 0
        
        for idx, row in rosters_df.iterrows():
            try:
                team_abbr = row.get('team')
                if not team_abbr or pd.isna(team_abbr):
                    skipped += 1
                    continue
                
                team = self.db.get_team_by_abbreviation(team_abbr)
                if not team:
                    self.updates_made['errors'].append(f"Team not found: {team_abbr}")
                    skipped += 1
                    continue
                
                team_id = team['team_id']
                name = row.get('player_name') or row.get('full_name')
                if not name or pd.isna(name):
                    skipped += 1
                    continue
                
                position = row.get('position', 'UNK')
                if pd.isna(position):
                    position = 'UNK'
                
                height = row.get('height')
                weight = row.get('weight')
                college = row.get('college')
                
                if pd.isna(height): height = None
                if pd.isna(weight): weight = None
                if pd.isna(college): college = None
                
                player_id = self.db.get_or_create_player(
                    name=name,
                    position=position,
                    height=height,
                    weight=weight,
                    college=college
                )
                
                existing = self.db.execute_query("""
                    SELECT player_season_id, team_id, roster_status
                    FROM player_seasons
                    WHERE player_id = %s AND season = 2025
                    LIMIT 1
                """, (player_id,))
                
                jersey = row.get('jersey_number')
                age = row.get('age')
                years_exp = row.get('years_exp') or row.get('entry_year')
                status = row.get('status', '')
                
                if pd.isna(jersey): jersey = None
                if pd.isna(age): age = None
                if pd.isna(years_exp): years_exp = None
                
                roster_status = self.determine_roster_status(status)
                
                if existing:
                    old_team_id = existing[0]['team_id']
                    old_status = existing[0]['roster_status']
                    
                    if old_team_id != team_id:
                        print(f"  🔄 TRADE: {name} → {team_abbr}")
                        self.updates_made['trades'] += 1
                    
                    if old_status != roster_status:
                        self.updates_made['status_changes'] += 1
                    
                    self.db.execute_update("""
                        UPDATE player_seasons
                        SET team_id = %s,
                            position = %s,
                            jersey_number = %s,
                            age = %s,
                            years_in_league = %s,
                            roster_status = %s,
                            updated_at = NOW()
                        WHERE player_season_id = %s
                    """, (team_id, position, jersey, age, years_exp, roster_status,
                          existing[0]['player_season_id']))
                else:
                    self.db.add_player_season(
                        player_id=player_id,
                        season=2025,
                        team_id=team_id,
                        position=position,
                        jersey_number=jersey,
                        age=age,
                        years_in_league=years_exp,
                        roster_status=roster_status,
                        status='Active'
                    )
                    self.updates_made['new_players'] += 1
                
                processed += 1
                
                if processed % 200 == 0:
                    print(f"  Progress: {processed} players processed...")
                
            except Exception as e:
                self.updates_made['errors'].append(f"Error processing {row.get('player_name', 'Unknown')}: {e}")
                skipped += 1
        
        print(f"\n✓ Processed {processed} players")
        if skipped > 0:
            print(f"⚠️  Skipped {skipped} records")
    
    def print_summary(self):
        print("\n" + "="*70)
        print("UPDATE SUMMARY")
        print("="*70)
        print(f"🆕 New Players Added: {self.updates_made['new_players']}")
        print(f"🔄 Trades Detected: {self.updates_made['trades']}")
        print(f"📝 Status Changes: {self.updates_made['status_changes']}")
        print(f"🗑️  Duplicates Removed: {self.updates_made['duplicates_removed']}")
        
        if self.updates_made['errors']:
            print(f"\n⚠️  Errors: {len(self.updates_made['errors'])}")
            print("First 5 errors:")
            for error in self.updates_made['errors'][:5]:
                print(f"  - {error}")
    
    def verify_counts(self):
        result = self.db.execute_query("""
            SELECT 
                COUNT(DISTINCT p.player_id) as total_players,
                COUNT(ps.player_season_id) as total_seasons,
                COUNT(CASE WHEN ps.roster_status = 'Active' THEN 1 END) as active
            FROM players p
            LEFT JOIN player_seasons ps ON p.player_id = ps.player_id AND ps.season = 2025
        """)
        
        print("\n" + "="*70)
        print("DATABASE VERIFICATION")
        print("="*70)
        print(f"Total Players in DB: {result[0]['total_players']}")
        print(f"2025 Player-Seasons: {result[0]['total_seasons']}")
        print(f"Active Players: {result[0]['active']}")
    
    def run(self):
        print("\n" + "="*70)
        print("SMART ROSTER UPDATER - 2025 SEASON")
        print("="*70)
        print(f"📅 Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        rosters_df = self.fetch_current_rosters()
        if rosters_df is None or len(rosters_df) == 0:
            print("\n✗ Failed to fetch rosters. Aborting.")
            return False
        
        self.remove_duplicates()
        
        self.update_rosters(rosters_df)
        
        self.print_summary()
        
        self.verify_counts()
        
        print("\n" + "="*70)
        print("✅ ROSTER UPDATE COMPLETE!")
        print("="*70)
        
        return True

if __name__ == "__main__":
    updater = SmartRosterUpdater()
    updater.run()