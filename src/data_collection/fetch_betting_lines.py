import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
import requests
import time
from datetime import datetime

class BettingLinesFetcher:
    """Fetch historical betting lines from The Odds API"""
    
    def __init__(self, api_key=None):
        self.db = DatabaseManager()
        self.api_key = api_key 
        self.base_url = "https://api.the-odds-api.com/v4"
    
    def add_sample_betting_lines(self, seasons):
        """
        Add sample betting lines based on actual game outcomes
        This simulates what Vegas lines would have been
        
        For a real implementation, you'd fetch from The Odds API or scrape from sports reference sites
        """
        print("=" * 70)
        print("ADDING BETTING LINES")
        print("=" * 70)
        games_query = """
            SELECT 
                g.game_id, g.season, g.week,
                g.home_team_id, g.away_team_id,
                g.home_score, g.away_score,
                ht.abbreviation as home_abbr,
                at.abbreviation as away_abbr
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE g.season IN ({})
            AND g.game_status = 'Final'
            AND g.home_score IS NOT NULL
            ORDER BY g.season, g.week
        """.format(','.join(['%s'] * len(seasons)))
        
        games = self.db.execute_query(games_query, tuple(seasons))
        
        print(f"Found {len(games)} games to add lines for...")
        
        added_count = 0
        
        for game in games:
            actual_diff = game['home_score'] - game['away_score']

            import random
            noise = random.uniform(-3, 3)
            simulated_spread = round((actual_diff + noise) * 2) / 2
            total_points = game['home_score'] + game['away_score']
            ou_noise = random.uniform(-4, 4)
            simulated_over_under = round((total_points + ou_noise) * 2) / 2
            try:
                self.db.add_betting_line(
                    game_id=game['game_id'],
                    source='Simulated',
                    spread=simulated_spread,
                    spread_juice=-110,
                    over_under=simulated_over_under,
                    over_juice=-110,
                    under_juice=-110,
                    is_opening_line=True
                )
                added_count += 1
                
                if added_count % 50 == 0:
                    print(f"  Progress: {added_count} lines added...")
                    
            except Exception as e:
                if "Duplicate entry" not in str(e):
                    print(f"Error adding line: {e}")
        
        print(f"\n{'=' * 70}")
        print(f"✓ Added {added_count} betting lines")
        print(f"{'=' * 70}")
        print("\nSample Betting Lines:")
        sample = self.db.execute_query("""
            SELECT 
                g.season, g.week,
                ht.abbreviation as home,
                at.abbreviation as away,
                bl.spread,
                bl.over_under,
                g.home_score,
                g.away_score
            FROM betting_lines bl
            JOIN games g ON bl.game_id = g.game_id
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            ORDER BY RAND()
            LIMIT 10
        """)
        
        print(f"\n{'Week':<6} {'Matchup':<20} {'Spread':<8} {'O/U':<6} {'Result':<10}")
        print("-" * 60)
        for row in sample:
            matchup = f"{row['away']} @ {row['home']}"
            result = f"{row['away_score']}-{row['home_score']}"
            print(f"{row['week']:<6} {matchup:<20} {row['spread']:<8.1f} {row['over_under']:<6.1f} {result:<10}")

def main():
    fetcher = BettingLinesFetcher()
    seasons = [2022, 2023]
    fetcher.add_sample_betting_lines(seasons)
    
    print("\n" + "=" * 70)
    print("NOTE: These are simulated betting lines for demonstration.")
    print("For production, integrate with The Odds API or scrape historical data.")
    print("=" * 70)

if __name__ == "__main__":
    main()