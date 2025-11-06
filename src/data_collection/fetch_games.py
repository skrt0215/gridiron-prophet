import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime
from database.db_manager import DatabaseManager

class NFLGameFetcher:
    
    def __init__(self):
        self.db = DatabaseManager()
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
    
    def get_team_id_by_abbreviation(self, abbr):
        team = self.db.get_team_by_abbreviation(abbr)
        return team['team_id'] if team else None
    
    def fetch_scoreboard(self, season=2024, week=None):
        url = f"{self.base_url}/scoreboard"
        
        params = {}
        if week:
            params['week'] = week
            params['seasontype'] = 2
        
        print(f"Fetching games for {season} season, week {week if week else 'current'}...")
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self.parse_scoreboard_data(data, season, week)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching scoreboard: {e}")
            return []
    
    def parse_scoreboard_data(self, data, season, week):
        games = []
        
        if 'events' not in data:
            print("No games found in response")
            return games
        
        for event in data['events']:
            try:
                game_info = self.extract_game_info(event, season, week)
                if game_info:
                    games.append(game_info)
            except Exception as e:
                print(f"Error parsing game: {e}")
                continue
        
        return games
    
    def extract_game_info(self, event, season, week):
        
        competition = event['competitions'][0]
        home_team = None
        away_team = None
        
        for team in competition['competitors']:
            team_abbr = team['team'].get('abbreviation', '')
            
            if team['homeAway'] == 'home':
                home_team = {
                    'abbreviation': team_abbr,
                    'score': int(team.get('score', 0))
                }
            else:
                away_team = {
                    'abbreviation': team_abbr,
                    'score': int(team.get('score', 0))
                }
        
        if not home_team or not away_team:
            return None
        home_team_id = self.get_team_id_by_abbreviation(home_team['abbreviation'])
        away_team_id = self.get_team_id_by_abbreviation(away_team['abbreviation'])
        
        if not home_team_id or not away_team_id:
            print(f"Warning: Could not find team IDs for {home_team['abbreviation']} vs {away_team['abbreviation']}")
            return None
        game_date_str = event['date']
        game_datetime = datetime.strptime(game_date_str, '%Y-%m-%dT%H:%MZ')
        venue = competition.get('venue', {})
        stadium = venue.get('fullName', '')
        is_dome = venue.get('indoor', False)
        status = competition['status']['type']['name']
        game_status = 'Final' if status == 'STATUS_FINAL' else 'Scheduled'
        
        return {
            'season': season,
            'week': week if week else event.get('week', {}).get('number'),
            'game_date': game_datetime.date(),
            'game_time': game_datetime.time(),
            'home_team_id': home_team_id,
            'away_team_id': away_team_id,
            'home_score': home_team['score'] if game_status == 'Final' else None,
            'away_score': away_team['score'] if game_status == 'Final' else None,
            'stadium': stadium,
            'is_dome': is_dome,
            'game_status': game_status
        }
    
    def save_games_to_db(self, games):
        added_count = 0
        
        for game in games:
            try:
                game_id = self.db.add_game_safe(**game)
                home_team = self.db.get_team_by_abbreviation(
                    self.db.execute_query(
                        "SELECT abbreviation FROM teams WHERE team_id = %s",
                        (game['home_team_id'],)
                    )[0]['abbreviation']
                )
                away_team = self.db.get_team_by_abbreviation(
                    self.db.execute_query(
                        "SELECT abbreviation FROM teams WHERE team_id = %s",
                        (game['away_team_id'],)
                    )[0]['abbreviation']
                )
                
                score_info = ""
                if game['home_score'] is not None:
                    score_info = f" - Final: {away_team['abbreviation']} {game['away_score']}, {home_team['abbreviation']} {game['home_score']}"
                
                print(f"✓ Added: Week {game['week']} - {away_team['name']} @ {home_team['name']}{score_info}")
                added_count += 1
                
            except Exception as e:
                if "Duplicate entry" in str(e):
                    print(f"- Skipped: Game already exists")
                else:
                    print(f"✗ Error saving game: {e}")
        
        return added_count

def get_current_nfl_week() -> int:
    SEASON_2025_WEEKS = {
        1: ("2025-09-05", "2025-09-09"),
        2: ("2025-09-10", "2025-09-16"),
        3: ("2025-09-17", "2025-09-23"),
        4: ("2025-09-24", "2025-09-30"),
        5: ("2025-10-01", "2025-10-07"),
        6: ("2025-10-08", "2025-10-14"),
        7: ("2025-10-15", "2025-10-21"),
        8: ("2025-10-22", "2025-10-28"),
        9: ("2025-10-29", "2025-11-04"),
        10: ("2025-11-05", "2025-11-11"),
        11: ("2025-11-12", "2025-11-18"),
        12: ("2025-11-19", "2025-11-25"),
        13: ("2025-11-26", "2025-12-02"),
        14: ("2025-12-03", "2025-12-09"),
        15: ("2025-12-10", "2025-12-16"),
        16: ("2025-12-17", "2025-12-23"),
        17: ("2025-12-24", "2025-12-30"),
        18: ("2025-12-31", "2026-01-05"),
    }
    
    try:
        today = datetime.now().date()
        
        for week, (start_str, end_str) in SEASON_2025_WEEKS.items():
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_str, "%Y-%m-%d").date()
            
            if start <= today <= end:
                return week
        
        last_week_end = datetime.strptime(SEASON_2025_WEEKS[18][1], "%Y-%m-%d").date()
        if today > last_week_end:
            return 18
        
        return 1
        
    except Exception as e:
        print(f"⚠️  Error getting current week: {e}")
        return 10

def main():
    fetcher = NFLGameFetcher()
    
    print("=" * 60)
    print("NFL Game Data Fetcher")
    print("=" * 60)
    
    season = 2025
    current_week = get_current_nfl_week()
    completed_week = current_week - 1
    
    print(f"📅 Current Week: {current_week}")
    print(f"🎯 Fetching completed games from Week {completed_week}")
    
    games = fetcher.fetch_scoreboard(season=season, week=completed_week)
    
    if games:
        print(f"\nFound {len(games)} games")
        added = fetcher.save_games_to_db(games)
        print(f"\n✓ Successfully added {added} games to database!")
    else:
        print("No games found")

if __name__ == "__main__":
    main()