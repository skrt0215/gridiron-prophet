"""
ESPN 2025 Stats Fetcher
Fetches current 2025 season stats from ESPN API
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from database.db_manager import DatabaseManager
from datetime import datetime
import time

class ESPN2025Fetcher:
    """Fetch 2025 season stats from ESPN API"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.player_name_to_id = {}
        self.game_cache = {}
        
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
    
    def load_active_players(self):
        """Load active 2025 players"""
        print("\n" + "="*70)
        print("LOADING ACTIVE 2025 PLAYERS")
        print("="*70)
        
        players = self.db.get_active_players_for_season(2025)
        for player in players:
            self.player_name_to_id[player['name'].lower()] = player['player_id']
        
        print(f"✓ Loaded {len(players)} active players")
        return players
    
    def get_week_schedule(self, season, week):
        """Get games for a specific week from ESPN"""
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
            
            games = data.get('events', [])
            print(f"  Found {len(games)} games for Week {week}")
            return games
            
        except Exception as e:
            print(f"  ✗ Error fetching week {week} schedule: {e}")
            return []
    
    def get_player_stats_for_game(self, game_id):
        """Get player statistics for a specific game"""
        url = f"http://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
        params = {'event': game_id}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            boxscore = data.get('boxscore', {})
            players = boxscore.get('players', [])
            
            return players
            
        except Exception as e:
            print(f"    ✗ Error fetching game {game_id} stats: {e}")
            return []
    
    def normalize_player_name(self, name):
        """Normalize player names for matching"""
        name = name.replace(' Jr.', '').replace(' Sr.', '')
        name = name.replace(' II', '').replace(' III', '').replace(' IV', '')
        parts = name.split()
        if len(parts) == 3 and len(parts[1]) <= 2:
            name = f"{parts[0]} {parts[2]}"
        
        return name.strip().lower()
    
    def parse_player_stats(self, stat_data, position_category):
        """Parse individual player stat line"""
        stats = {
            'pass_attempts': 0, 'pass_completions': 0, 'pass_yards': 0,
            'pass_touchdowns': 0, 'interceptions': 0, 'sacks_taken': 0,
            'rush_attempts': 0, 'rush_yards': 0, 'rush_touchdowns': 0,
            'targets': 0, 'receptions': 0, 'receiving_yards': 0,
            'receiving_touchdowns': 0, 'fumbles': 0, 'fumbles_lost': 0
        }
        
        stat_labels = stat_data.get('labels', [])
        stat_values = stat_data.get('stats', [])
        
        if not stat_labels or not stat_values:
            return stats
        
        stat_dict = dict(zip(stat_labels, stat_values))
        
        if position_category == 'passing':
            if 'C/ATT' in stat_dict:
                comp_att = stat_dict['C/ATT'].split('/')
                if len(comp_att) == 2:
                    stats['pass_completions'] = int(comp_att[0])
                    stats['pass_attempts'] = int(comp_att[1])
            stats['pass_yards'] = int(stat_dict.get('YDS', 0))
            stats['pass_touchdowns'] = int(stat_dict.get('TD', 0))
            stats['interceptions'] = int(stat_dict.get('INT', 0))
            stats['sacks_taken'] = int(stat_dict.get('SACKS', 0) if 'SACKS' in stat_dict else 0)
        
        elif position_category == 'rushing':
            stats['rush_attempts'] = int(stat_dict.get('CAR', 0))
            stats['rush_yards'] = int(stat_dict.get('YDS', 0))
            stats['rush_touchdowns'] = int(stat_dict.get('TD', 0))
        
        elif position_category == 'receiving':
            stats['receptions'] = int(stat_dict.get('REC', 0))
            stats['receiving_yards'] = int(stat_dict.get('YDS', 0))
            stats['receiving_touchdowns'] = int(stat_dict.get('TD', 0))
            stats['targets'] = int(stat_dict.get('TGTS', 0) if 'TGTS' in stat_dict else 0)
        
        return stats
    
    def find_game_id(self, home_team_abbr, away_team_abbr, season, week):
        """Find game_id in our database"""
        home_team = self.db.get_team_by_abbreviation(home_team_abbr)
        away_team = self.db.get_team_by_abbreviation(away_team_abbr)
        
        if not home_team or not away_team:
            return None, None, None
        
        game = self.db.execute_query("""
            SELECT game_id, home_team_id, away_team_id
            FROM games
            WHERE season = %s AND week = %s
            AND home_team_id = %s AND away_team_id = %s
            LIMIT 1
        """, (season, week, home_team['team_id'], away_team['team_id']))
        
        if game:
            return game[0]['game_id'], home_team['team_id'], away_team['team_id']
        return None, None, None
    
    def process_week(self, season, week):
        """Process all games for a specific week"""
        print(f"\nProcessing Week {week}...")
        
        games = self.get_week_schedule(season, week)
        
        if not games:
            print(f"  No games found for Week {week}")
            return 0
        
        total_stats_added = 0
        
        for game_data in games:
            try:
                competitions = game_data.get('competitions', [{}])[0]
                competitors = competitions.get('competitors', [])
                
                if len(competitors) != 2:
                    continue
                
                home_team = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                away_team = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                
                if not home_team or not away_team:
                    continue
                
                espn_home_abbr = home_team['team']['abbreviation']
                espn_away_abbr = away_team['team']['abbreviation']
                
                home_abbr = self.espn_to_nfl.get(espn_home_abbr, espn_home_abbr)
                away_abbr = self.espn_to_nfl.get(espn_away_abbr, espn_away_abbr)
                
                game_id, home_team_id, away_team_id = self.find_game_id(home_abbr, away_abbr, season, week)
                
                if not game_id:
                    print(f"  ⚠️  Game not found in DB: {home_abbr} vs {away_abbr}")
                    continue
                
                espn_game_id = game_data.get('id')
                player_stats = self.get_player_stats_for_game(espn_game_id)
                
                for team_stats in player_stats:
                    team_abbr = team_stats.get('team', {}).get('abbreviation', '')
                    team_abbr = self.espn_to_nfl.get(team_abbr, team_abbr)
                    
                    team_obj = self.db.get_team_by_abbreviation(team_abbr)
                    if not team_obj:
                        continue
                    team_id = team_obj['team_id']
                    for category in team_stats.get('statistics', []):
                        category_name = category.get('name', '').lower()
                        athletes = category.get('athletes', [])
                        for athlete_data in athletes:
                            athlete = athlete_data.get('athlete', {})
                            player_name = athlete.get('displayName', '')
                            if not player_name:
                                continue
                            normalized_name = self.normalize_player_name(player_name)
                            player_id = self.player_name_to_id.get(normalized_name)
                            if not player_id:
                                continue 
                            stats = self.parse_player_stats(athlete_data, category_name)
                            try:
                                self.db.add_player_game_stat(
                                    player_id=player_id,
                                    game_id=game_id,
                                    team_id=team_id,
                                    season=season,
                                    week=week,
                                    **stats
                                )
                                total_stats_added += 1
                            except Exception as e:
                                if "Duplicate entry" not in str(e):
                                    pass
                                time.sleep(0.5)
            except Exception as e:
                print(f"  ✗ Error processing game: {e}")
                continue
        
        print(f"  ✓ Added {total_stats_added} player stats for Week {week}")
        return total_stats_added
    
    def fetch_2025_season(self, start_week=1, end_week=18):
        """Fetch 2025 season stats week by week"""
        print("\n" + "="*70)
        print("FETCHING 2025 SEASON FROM ESPN")
        print("="*70)
        print(f"\nFetching weeks {start_week} to {end_week}...")
        
        total_added = 0
        
        for week in range(start_week, end_week + 1):
            added = self.process_week(2025, week)
            total_added += added
            time.sleep(1)
        return total_added
    
    def verify_data(self):
        """Verify 2025 data"""
        print("\n" + "="*70)
        print("VERIFICATION")
        print("="*70)
        
        result = self.db.execute_query("""
            SELECT week, COUNT(*) as records, COUNT(DISTINCT player_id) as players
            FROM player_game_stats
            WHERE season = 2025
            GROUP BY week
            ORDER BY week
        """)
        
        print(f"\n{'Week':<8} {'Records':<12} {'Players':<12}")
        print("-" * 40)
        
        total = 0
        for r in result:
            print(f"{r['week']:<8} {r['records']:<12} {r['players']:<12}")
            total += r['records']
        
        print("-" * 40)
        print(f"{'TOTAL':<8} {total:<12}")
    
    def run(self, start_week=1, end_week=None):
        """Run the full fetch process"""
        print("\n" + "="*70)
        print("GRIDIRON PROPHET - ESPN 2025 STATS FETCHER")
        print("="*70)
        print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if end_week is None:
            end_week = 6
            print(f"\nAuto-fetching weeks {start_week}-{end_week}")
        
        self.load_active_players()
        total = self.fetch_2025_season(start_week, end_week)
        self.verify_data()
        
        print("\n" + "="*70)
        print(f"✓ COMPLETE! Added {total} total stat records")
        print("="*70)
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    fetcher = ESPN2025Fetcher()
    
    fetcher.run(start_week=1, end_week=6)