"""
ESPN 2025 Schedule Fetcher
Fetches the complete 2025 season schedule and adds missing games
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from database.db_manager import DatabaseManager
from datetime import datetime
import time

class ScheduleFetcher:
    """Fetch 2025 schedule from ESPN"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.espn_to_nfl = {
            'ARI': 'ARI', 'ATL': 'ATL', 'BAL': 'BAL', 'BUF': 'BUF',
            'CAR': 'CAR', 'CHI': 'CHI', 'CIN': 'CIN', 'CLE': 'CLE',
            'DAL': 'DAL', 'DEN': 'DEN', 'DET': 'DET', 'GB': 'GB',
            'HOU': 'HOU', 'IND': 'IND', 'JAX': 'JAX', 'KC': 'KC',
            'LAR': 'LA', 'LAC': 'LAC', 'LV': 'LV', 'MIA': 'MIA',
            'MIN': 'MIN', 'NE': 'NE', 'NO': 'NO', 'NYG': 'NYG',
            'NYJ': 'NYJ', 'PHI': 'PHI', 'PIT': 'PIT', 'SEA': 'SEA',
            'SF': 'SF', 'TB': 'TB', 'TEN': 'TEN', 'WSH': 'WAS'
        }
    
    def fetch_week_schedule(self, season, week):
        """Fetch schedule for a specific week"""
        url = f"http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        params = {
            'seasontype': 2,
            'week': week,
            'dates': season
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('events', [])
        except Exception as e:
            print(f"  ✗ Error fetching Week {week}: {e}")
            return []
    
    def add_game_to_db(self, game_data, season, week):
        """Add a game to the database"""
        try:
            competitions = game_data.get('competitions', [{}])[0]
            competitors = competitions.get('competitors', [])
            
            if len(competitors) != 2:
                return False
            
            home_team = next((c for c in competitors if c.get('homeAway') == 'home'), None)
            away_team = next((c for c in competitors if c.get('homeAway') == 'away'), None)
            
            if not home_team or not away_team:
                return False
            
            espn_home_abbr = home_team['team']['abbreviation']
            espn_away_abbr = away_team['team']['abbreviation']
            
            home_abbr = self.espn_to_nfl.get(espn_home_abbr, espn_home_abbr)
            away_abbr = self.espn_to_nfl.get(espn_away_abbr, espn_away_abbr)
            
            home_team_obj = self.db.get_team_by_abbreviation(home_abbr)
            away_team_obj = self.db.get_team_by_abbreviation(away_abbr)
            
            if not home_team_obj or not away_team_obj:
                print(f"    ⚠️  Teams not found in DB: {home_abbr} vs {away_abbr}")
                return False
            
            home_team_id = home_team_obj['team_id']
            away_team_id = away_team_obj['team_id']
            
            game_date_str = game_data.get('date')
            game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00')).date()
            game_time = datetime.fromisoformat(game_date_str.replace('Z', '+00:00')).time()
            
            venue = competitions.get('venue', {})
            stadium = venue.get('fullName')
            is_dome = venue.get('indoor', False)
            
            status = competitions.get('status', {})
            game_status = 'Final' if status.get('type', {}).get('completed', False) else 'Scheduled'
            
            home_score = int(home_team.get('score', 0)) if home_team.get('score') else None
            away_score = int(away_team.get('score', 0)) if away_team.get('score') else None
            
            game_id = self.db.add_game_safe(
                season=season,
                week=week,
                game_date=game_date,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                game_time=game_time,
                home_score=home_score,
                away_score=away_score,
                stadium=stadium,
                is_dome=is_dome,
                game_status=game_status
            )
            
            return True
            
        except Exception as e:
            print(f"    ✗ Error adding game: {e}")
            return False
    
    def fetch_and_add_schedule(self, season=2025, start_week=1, end_week=18):
        """Fetch complete schedule and add to database"""
        print("\n" + "="*70)
        print("FETCHING 2025 SCHEDULE FROM ESPN")
        print("="*70)
        print(f"\nFetching weeks {start_week} to {end_week}...\n")
        
        total_added = 0
        total_updated = 0
        
        for week in range(start_week, end_week + 1):
            print(f"Week {week}...")
            
            games = self.fetch_week_schedule(season, week)
            
            if not games:
                print(f"  No games found")
                continue
            
            week_added = 0
            for game in games:
                if self.add_game_to_db(game, season, week):
                    week_added += 1
            
            print(f"  ✓ Processed {len(games)} games")
            total_added += week_added
            time.sleep(0.5)
        
        print(f"\n✓ Complete! Processed schedule for weeks {start_week}-{end_week}")
        return total_added
    
    def verify_schedule(self):
        """Verify the schedule is complete"""
        print("\n" + "="*70)
        print("VERIFICATION - 2025 SCHEDULE")
        print("="*70)
        result = self.db.execute_query("""
            SELECT week, COUNT(*) as games
            FROM games
            WHERE season = 2025
            GROUP BY week
            ORDER BY week
        """)
        
        print(f"\n{'Week':<8} {'Games':<10}")
        print("-" * 20)
        
        total = 0
        for r in result:
            print(f"{r['week']:<8} {r['games']:<10}")
            total += r['games']
        
        print("-" * 20)
        print(f"{'TOTAL':<8} {total:<10}")
        print("\n" + "-"*70)
        print("Games Per Team:")
        print("-"*70)
        
        team_result = self.db.execute_query("""
            SELECT 
                t.abbreviation,
                COUNT(DISTINCT g.game_id) as game_count
            FROM teams t
            LEFT JOIN games g ON (t.team_id = g.home_team_id OR t.team_id = g.away_team_id) 
                AND g.season = 2025
            GROUP BY t.team_id, t.abbreviation
            ORDER BY game_count ASC, t.abbreviation
        """)
        
        print(f"\n{'Team':<8} {'Games':<10}")
        print("-" * 20)
        
        for r in team_result:
            status = "⚠️" if r['game_count'] < 6 else "✓"
            print(f"{status} {r['abbreviation']:<6} {r['game_count']:<10}")
        was_games = [r for r in team_result if r['abbreviation'] == 'WAS']
        if was_games and was_games[0]['game_count'] > 0:
            print(f"\n✓ Washington Commanders now has {was_games[0]['game_count']} games!")
        elif was_games:
            print(f"\n⚠️ Washington Commanders still has 0 games")
    
    def run(self, start_week=1, end_week=18):
        """Run the schedule fetch"""
        print("\n" + "="*70)
        print("GRIDIRON PROPHET - 2025 SCHEDULE FETCHER")
        print("="*70)
        print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.fetch_and_add_schedule(2025, start_week, end_week)
        self.verify_schedule()
        
        print("\n" + "="*70)
        print("✓ SCHEDULE FETCH COMPLETE!")
        print("="*70)
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nNow you can run fetch_2025_espn.py to get player stats!")

if __name__ == "__main__":
    fetcher = ScheduleFetcher()
    fetcher.run(start_week=1, end_week=18)