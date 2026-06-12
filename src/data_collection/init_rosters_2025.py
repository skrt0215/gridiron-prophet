"""
Clean Roster Initialization for 2025 Season
Fetches ONLY active 2025 players and properly populates the database
"""
import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nflreadpy as nfl
from database.db_manager import DatabaseManager
from config.season import CURRENT_SEASON
import pandas as pd

TEAM_FIX = {'LA': 'LAR', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'}

class RosterInitializer:
    """Initialize rosters for a given season"""

    def __init__(self):
        self.db = DatabaseManager()
        self.player_cache = {}

    def clear_player_data(self):
        """Clear all player-related data (keeps teams and games)"""
        print("\n" + "="*70)
        print("WARNING: This will delete ALL player data")
        print("="*70)
        print("This will clear:")
        print("  - All players")
        print("  - All player_seasons records")
        print("  - All player_game_stats")
        print("  - All injuries")
        print("  - All depth_charts")
        print("\nTeams and Games will NOT be affected.")

        response = input("\nAre you sure you want to continue? (type 'yes'): ")

        if response.lower() != 'yes':
            print("\nAborted. No changes made.")
            return False

        print("\nClearing player data...")

        try:
            self.db.execute_update("DELETE FROM player_game_stats")
            print("  Cleared player_game_stats")

            self.db.execute_update("DELETE FROM depth_charts")
            print("  Cleared depth_charts")

            self.db.execute_update("DELETE FROM injuries")
            print("  Cleared injuries")

            self.db.execute_update("DELETE FROM player_seasons")
            print("  Cleared player_seasons")

            self.db.execute_update("DELETE FROM players")
            print("  Cleared players")

            print("\nAll player data cleared successfully!")
            return True

        except Exception as e:
            print(f"\nError clearing data: {e}")
            return False

    def determine_roster_status(self, status_str):
        """Determine roster status from roster status field"""
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

    def fetch_rosters(self, season):
        """Fetch rosters for a season from nflreadpy"""
        print("\n" + "="*70)
        print(f"FETCHING {season} ROSTERS")
        print("="*70)
        print(f"\nDownloading {season} roster data from nflreadpy...")

        try:
            rosters_df = nfl.load_rosters(season).to_pandas()
            print(f"Found {len(rosters_df)} player records for {season}")
            print("COLUMNS:", list(rosters_df.columns))

            return rosters_df

        except Exception as e:
            print(f"Error fetching rosters: {e}")
            return None

    def process_rosters(self, rosters_df, season):
        """Process roster data and populate database"""
        print("\n" + "="*70)
        print("PROCESSING ROSTERS")
        print("="*70)

        added_players = 0
        added_seasons = 0
        skipped = 0
        errors = []

        for idx, row in rosters_df.iterrows():
            try:
                team_abbr = row.get('team')
                if not team_abbr or pd.isna(team_abbr):
                    skipped += 1
                    continue

                team_abbr = TEAM_FIX.get(team_abbr, team_abbr)

                team = self.db.get_team_by_abbreviation(team_abbr)
                if not team:
                    errors.append(f"Team not found: {team_abbr}")
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

                if player_id and player_id not in self.player_cache:
                    added_players += 1
                    self.player_cache[player_id] = name

                jersey = row.get('jersey_number')
                age = row.get('age')
                years_exp = row.get('years_exp')
                status = row.get('status', '')

                if pd.isna(jersey): jersey = None
                if pd.isna(age): age = None
                if pd.isna(years_exp):
                    years_exp = None
                else:
                    years_exp = int(years_exp)

                roster_status = self.determine_roster_status(status)
                self.db.add_player_season(
                    player_id=player_id,
                    season=season,
                    team_id=team_id,
                    position=position,
                    jersey_number=jersey,
                    age=age,
                    years_in_league=years_exp,
                    roster_status=roster_status,
                    status='Active'
                )

                added_seasons += 1

                if added_seasons % 100 == 0:
                    print(f"  Progress: {added_seasons} player-seasons processed...")

            except Exception as e:
                errors.append(f"Error processing {row.get('player_name', 'Unknown')}: {e}")
                skipped += 1

        print("\n" + "="*70)
        print(f"Added {added_players} unique players to database")
        print(f"Added {added_seasons} player-season records")
        print(f"Skipped {skipped} records")

        if errors:
            print(f"\nErrors encountered: {len(errors)}")
            print("First 5 errors:")
            for error in errors[:5]:
                print(f"  - {error}")

    def verify_rosters(self, season):
        """Verify roster data after import"""
        print("\n" + "="*70)
        print("ROSTER VERIFICATION")
        print("="*70)

        result = self.db.execute_query("""
            SELECT
                t.abbreviation,
                COUNT(CASE WHEN ps.roster_status = 'Active' THEN 1 END) as active,
                COUNT(CASE WHEN ps.roster_status = 'Practice Squad' THEN 1 END) as practice,
                COUNT(CASE WHEN ps.roster_status = 'Injured Reserve' THEN 1 END) as ir,
                COUNT(CASE WHEN ps.roster_status IN ('PUP', 'NFI', 'Suspended') THEN 1 END) as other,
                COUNT(*) as total
            FROM teams t
            LEFT JOIN player_seasons ps ON t.team_id = ps.team_id AND ps.season = %s
            GROUP BY t.team_id, t.abbreviation
            ORDER BY t.abbreviation
        """, (season,))

        print(f"\n{'Team':<6} {'Active':<8} {'Practice':<10} {'IR':<6} {'Other':<7} {'Total':<6}")
        print("-" * 60)

        total_active = 0
        total_all = 0
        issues = []

        for r in result:
            print(f"{r['abbreviation']:<6} {r['active']:<8} {r['practice']:<10} "
                  f"{r['ir']:<6} {r['other']:<7} {r['total']:<6}")

            total_active += r['active']
            total_all += r['total']

            if r['total'] == 0:
                issues.append(f"{r['abbreviation']}: No players found!")
            elif r['active'] < 40:
                issues.append(f"{r['abbreviation']}: Only {r['active']} active players (expected ~53)")
            elif r['active'] > 60:
                issues.append(f"{r['abbreviation']}: {r['active']} active players (seems high)")

        print("-" * 60)
        print(f"{'TOTALS':<6} {total_active:<8} {'':<10} {'':<6} {'':<7} {total_all:<6}")

        print(f"\nTotal players in database: {total_all}")
        print(f"Total active players: {total_active}")

        if issues:
            print(f"\nPotential Issues ({len(issues)}):")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\nAll teams have reasonable roster counts!")

        print("\n" + "-"*60)
        print("Sample: Kansas City Chiefs Active Roster")
        print("-"*60)

        sample = self.db.execute_query("""
            SELECT p.name, ps.position, ps.jersey_number, ps.roster_status
            FROM player_seasons ps
            JOIN players p ON ps.player_id = p.player_id
            JOIN teams t ON ps.team_id = t.team_id
            WHERE t.abbreviation = 'KC' AND ps.season = %s AND ps.roster_status = 'Active'
            ORDER BY
                CASE ps.position
                    WHEN 'QB' THEN 1 WHEN 'RB' THEN 2 WHEN 'WR' THEN 3
                    WHEN 'TE' THEN 4 WHEN 'OL' THEN 5 ELSE 6
                END,
                p.name
            LIMIT 15
        """, (season,))

        for r in sample:
            jersey = f"#{r['jersey_number']}" if r['jersey_number'] else "   "
            print(f"  {r['position']:<4} {jersey:<5} {r['name']:<30}")

    def run(self, season=CURRENT_SEASON, clear=False):
        """Run the full initialization process for a season"""
        print("\n" + "="*70)
        print(f"GRIDIRON PROPHET - {season} ROSTER INITIALIZATION")
        print("="*70)

        if clear and not self.clear_player_data():
            return

        rosters_df = self.fetch_rosters(season)
        if rosters_df is None or len(rosters_df) == 0:
            print("\nFailed to fetch rosters. Aborting.")
            return

        self.process_rosters(rosters_df, season)
        self.verify_rosters(season)

        print("\n" + "="*70)
        print(f"{season} ROSTER INITIALIZATION COMPLETE!")
        print("="*70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize rosters for a season")
    parser.add_argument('--season', type=int, default=CURRENT_SEASON)
    parser.add_argument('--clear', action='store_true',
                        help="Wipe ALL player data first (destructive)")
    args = parser.parse_args()

    initializer = RosterInitializer()
    initializer.run(season=args.season, clear=args.clear)