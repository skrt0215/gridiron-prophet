"""
Historical Data Fetcher for Active 2025 Players
Fetches 2022-2024 game statistics for all players currently on 2025 rosters
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nfl_data_py as nfl
from database.db_manager import DatabaseManager
import pandas as pd
from datetime import datetime

class HistoricalDataFetcher:
    """Fetch historical statistics for active 2025 players"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.player_name_to_id = {}
        self.game_cache = {}
    
    def get_active_players(self):
        """Get all active 2025 players from database"""
        print("\n" + "="*70)
        print("LOADING ACTIVE 2025 PLAYERS")
        print("="*70)
        
        players = self.db.get_active_players_for_season(2025)
        
        for player in players:
            self.player_name_to_id[player['name']] = player['player_id']
        
        print(f"✓ Loaded {len(players)} active players for 2025 season")
        return players
    
    def fetch_historical_stats(self, seasons=[2022, 2023, 2024]):
        """Fetch weekly stats for specified seasons"""
        print("\n" + "="*70)
        print(f"FETCHING HISTORICAL STATS ({', '.join(map(str, seasons))})")
        print("="*70)
        print("\nDownloading player statistics from nfl_data_py...")
        print("This may take several minutes...\n")
        
        try:
            stats_df = nfl.import_weekly_data(seasons)
            print(f"✓ Downloaded {len(stats_df)} player-game records")
            return stats_df
            
        except Exception as e:
            print(f"✗ Error fetching stats: {e}")
            return None
    
    def find_or_create_game(self, row, season, week):
        """Find the game_id for this stat, or skip if game doesn't exist"""
        cache_key = f"{season}-{week}-{row.get('recent_team')}-{row.get('opponent_team')}"
        
        if cache_key in self.game_cache:
            return self.game_cache[cache_key]
        
        recent_team = self.db.get_team_by_abbreviation(row.get('recent_team'))
        opponent_team = self.db.get_team_by_abbreviation(row.get('opponent_team'))
        
        if not recent_team or not opponent_team:
            self.game_cache[cache_key] = None
            return None
        
        recent_team_id = recent_team['team_id']
        opponent_team_id = opponent_team['team_id']
        
        game = self.db.execute_query("""
            SELECT game_id, home_team_id, away_team_id 
            FROM games 
            WHERE season = %s 
            AND week = %s 
            AND (
                (home_team_id = %s AND away_team_id = %s) OR
                (home_team_id = %s AND away_team_id = %s)
            )
            LIMIT 1
        """, (season, week, recent_team_id, opponent_team_id, 
              opponent_team_id, recent_team_id))
        
        game_id = game[0]['game_id'] if game else None
        self.game_cache[cache_key] = game_id
        return game_id
    
    def process_stat_row(self, row):
        """Process a single stat row and return formatted data"""
        try:
            player_name = row.get('player_display_name')
            if not player_name or pd.isna(player_name):
                return None
            
            if player_name not in self.player_name_to_id:
                return None
            
            player_id = self.player_name_to_id[player_name]
            season = int(row.get('season'))
            week = int(row.get('week'))
            game_id = self.find_or_create_game(row, season, week)

            if not game_id:
                return None
            team = self.db.get_team_by_abbreviation(row.get('recent_team'))

            if not team:
                return None
            team_id = team['team_id']
            
            def safe_int(val):
                return int(val) if val and not pd.isna(val) else 0
            
            def safe_float(val):
                return float(val) if val and not pd.isna(val) else 0.0
            
            stats = {
                'player_id': player_id,
                'game_id': game_id,
                'team_id': team_id,
                'season': season,
                'week': week,
                'pass_attempts': safe_int(row.get('attempts')),
                'pass_completions': safe_int(row.get('completions')),
                'pass_yards': safe_int(row.get('passing_yards')),
                'pass_touchdowns': safe_int(row.get('passing_tds')),
                'interceptions': safe_int(row.get('interceptions')),
                'sacks_taken': safe_int(row.get('sacks')),
                'rush_attempts': safe_int(row.get('carries')),
                'rush_yards': safe_int(row.get('rushing_yards')),
                'rush_touchdowns': safe_int(row.get('rushing_tds')),
                'targets': safe_int(row.get('targets')),
                'receptions': safe_int(row.get('receptions')),
                'receiving_yards': safe_int(row.get('receiving_yards')),
                'receiving_touchdowns': safe_int(row.get('receiving_tds')),
                'tackles': 0,
                'tackles_for_loss': 0,
                'sacks': 0.0,
                'forced_fumbles': 0,
                'fumble_recoveries': 0,
                'interceptions_defense': 0,
                'passes_defended': 0,
                'fumbles': safe_int(row.get('fumbles')),
                'fumbles_lost': safe_int(row.get('fumbles_lost')),
            }
            
            return stats
            
        except Exception as e:
            return None
    
    def load_stats_to_database(self, stats_df):
        """Process and load statistics into database"""
        print("\n" + "="*70)
        print("PROCESSING AND LOADING STATS")
        print("="*70)
        
        added_count = 0
        skipped_count = 0
        error_count = 0
        
        total_rows = len(stats_df)
        
        for idx, row in stats_df.iterrows():
            if (idx + 1) % 1000 == 0:
                print(f"  Progress: {idx + 1}/{total_rows} rows processed "
                      f"({added_count} added, {skipped_count} skipped)...")
            
            stats = self.process_stat_row(row)
            
            if stats is None:
                skipped_count += 1
                continue
            
            try:
                self.db.add_player_game_stat(**stats)
                added_count += 1
                
            except Exception as e:
                if "Duplicate entry" not in str(e):
                    error_count += 1
                    if error_count <= 5:
                        print(f"  ✗ Error adding stat: {e}")
                skipped_count += 1
        
        print("\n" + "="*70)
        print(f"✓ Added {added_count} player-game stat records")
        print(f"- Skipped {skipped_count} records (not 2025 active or no game match)")
        if error_count > 0:
            print(f"⚠️  {error_count} errors encountered")
    
    def verify_historical_data(self):
        """Verify the historical data was loaded correctly"""
        print("\n" + "="*70)
        print("VERIFICATION - HISTORICAL DATA")
        print("="*70)

        result = self.db.execute_query("""
            SELECT 
                season,
                COUNT(*) as stat_records,
                COUNT(DISTINCT player_id) as unique_players,
                COUNT(DISTINCT game_id) as unique_games
            FROM player_game_stats
            GROUP BY season
            ORDER BY season
        """)
        
        print("\nStats loaded by season:")
        print(f"{'Season':<8} {'Records':<12} {'Players':<12} {'Games':<10}")
        print("-" * 50)
        
        total_records = 0
        for r in result:
            print(f"{r['season']:<8} {r['stat_records']:<12} "
                  f"{r['unique_players']:<12} {r['unique_games']:<10}")
            total_records += r['stat_records']
        
        print("-" * 50)
        print(f"{'TOTAL':<8} {total_records:<12}")
        print("\n" + "-"*70)
        print("Sample: Patrick Mahomes Career Stats")
        print("-"*70)
        
        mahomes = self.db.get_player_by_name("Patrick Mahomes")
        if mahomes:
            career_stats = self.db.get_player_career_stats(mahomes['player_id'])
            
            if career_stats:
                print(f"\n{'Season':<8} {'Games':<8} {'Pass Yds':<12} {'Pass TDs':<10} "
                      f"{'Rush Yds':<12}")
                print("-" * 60)
                
                for stat in career_stats:
                    print(f"{stat['season']:<8} {stat['games']:<8} "
                          f"{stat['total_pass_yards'] or 0:<12} "
                          f"{stat['total_pass_tds'] or 0:<10} "
                          f"{stat['total_rush_yards'] or 0:<12}")
            else:
                print("  No stats found")
        else:
            print("  Player not found in database")
        print("\n" + "-"*70)
        print("2025 Active Players Without Historical Stats (likely rookies):")
        print("-"*70)
        
        no_stats = self.db.execute_query("""
            SELECT p.name, ps.position, t.abbreviation as team
            FROM player_seasons ps
            JOIN players p ON ps.player_id = p.player_id
            JOIN teams t ON ps.team_id = t.team_id
            LEFT JOIN player_game_stats pgs ON p.player_id = pgs.player_id
            WHERE ps.season = 2025 
            AND ps.roster_status = 'Active'
            AND pgs.player_id IS NULL
            ORDER BY t.abbreviation, ps.position, p.name
            LIMIT 20
        """)
        
        if no_stats:
            print(f"\nFound {len(no_stats)} active players without historical stats")
            print("First 20:")
            for player in no_stats[:20]:
                print(f"  {player['team']:<5} {player['position']:<4} {player['name']}")
            print("\n  (These are likely 2025 rookies or players new to the league)")
        else:
            print("\n✓ All active 2025 players have historical stats!")
    
    def run(self):
        """Run the full historical data fetch process"""
        print("\n" + "="*70)
        print("GRIDIRON PROPHET - HISTORICAL DATA FETCHER")
        print("="*70)
        print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        active_players = self.get_active_players()
        
        if not active_players:
            print("\n✗ No active players found. Run init_rosters_2025.py first!")
            return
        stats_df = self.fetch_historical_stats(seasons=[2022, 2023, 2024])
        
        if stats_df is None or len(stats_df) == 0:
            print("\n✗ Failed to fetch historical stats. Aborting.")
            return
        self.load_stats_to_database(stats_df)
        self.verify_historical_data()
        
        print("\n" + "="*70)
        print("✓ HISTORICAL DATA FETCH COMPLETE!")
        print("="*70)
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\nNext steps:")
        print("  1. Fetch 2025 current season stats (partial)")
        print("  2. Fetch current injury data")
        print("  3. Train your prediction model with historical + current data!")
        print("  4. Generate predictions for upcoming games")

if __name__ == "__main__":
    fetcher = HistoricalDataFetcher()
    fetcher.run()