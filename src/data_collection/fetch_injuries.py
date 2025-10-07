import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv('config/.env')
from database.db_manager import DatabaseManager
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import time

class InjuryReportFetcher:
    """Fetch current NFL injury reports"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.espn_url = "https://www.espn.com/nfl/injuries"
    
    
    def fetch_sportsdata_injuries(self):
        """Fetch injury reports from SportsData.io"""
        print("Fetching injury reports from SportsData.io...")
        
        api_key = os.getenv('SPORTSDATA_API_KEY')
        if not api_key:
            print("ERROR: SPORTSDATA_API_KEY not found in .env file")
            return []
        
        injuries = []
        
        try:
            # Current season - adjust as needed
            season = "2025"
            week = "6"  # Adjust to current week
            
            url = f"https://api.sportsdata.io/v3/nfl/scores/json/Injuries/{season}/{week}"
            
            params = {'key': api_key}
            
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                print(f"SportsData API returned status {response.status_code}")
                return []
            
            data = response.json()
            
            for player_inj in data:
                team_abbr = player_inj.get('Team', '')
                
                # Get team from database
                team = self.db.get_team_by_abbreviation(team_abbr)
                if not team:
                    continue
                
                team_id = team['team_id']
                
                # Map SportsData team name
                team_name_query = self.db.execute_query(
                    "SELECT name FROM teams WHERE team_id = %s", (team_id,)
                )
                team_name = team_name_query[0]['name'] if team_name_query else team_abbr
                
                player_name = player_inj.get('Name', '')
                position = player_inj.get('Position', 'Unknown')
                status = player_inj.get('Status', 'Unknown')  # Out, Questionable, Doubtful, etc.
                injury_type = player_inj.get('BodyPart', 'Unknown')  # Ankle, Knee, etc.
                
                injuries.append({
                    'team_id': team_id,
                    'team_name': team_name,
                    'player_name': player_name,
                    'position': position,
                    'status': status,
                    'injury_type': injury_type
                })
            
            print(f"✓ Found {len(injuries)} injury reports")
            return injuries
            
        except Exception as e:
            print(f"Error fetching SportsData injuries: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def save_injuries_to_db(self, injuries_list, game_week=None):
        """Save current injuries to database"""
        
        today = date.today()
        added_count = 0
        
        for inj in injuries_list:
            try:
                # Get or create player
                player = self.db.execute_query(
                    "SELECT player_id FROM players WHERE name = %s AND team_id = %s LIMIT 1",
                    (inj['player_name'], inj['team_id'])
                )
                
                if not player:
                    # Create player if doesn't exist
                    player_id = self.db.add_player(
                        name=inj['player_name'],
                        team_id=inj['team_id'],
                        position=inj['position']
                    )
                else:
                    player_id = player[0]['player_id']
                
                # Add injury report
                # Add injury report
                self.db.add_injury(
                    player_id=player_id,
                    injury_status=inj['status'],
                    date_reported=today,
                    body_part=inj['injury_type'], 
                    practice_status=inj['status']
                )
                
                added_count += 1
                
            except Exception as e:
                if "Duplicate entry" not in str(e):
                    print(f"Error saving injury for {inj['player_name']}: {e}")
        
        print(f"✓ Saved {added_count} injury reports to database")
        return added_count
    
    def get_team_injury_impact(self, team_id):
        """
        Calculate injury impact score for a team
        Higher score = more significant injuries
        """
        
        # Get current injuries
        injuries = self.db.execute_query("""
            SELECT 
                p.name,
                p.position,
                i.injury_status,
                i.body_part
            FROM injuries i
            JOIN players p ON i.player_id = p.player_id
            WHERE p.team_id = %s
            AND i.injury_status IN ('Out', 'Doubtful', 'Questionable', 'Injured Reserve')
            AND i.date_reported >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """, (team_id,))
        
        if not injuries:
            return {
                'impact_score': 0,
                'key_injuries': [],
                'total_injuries': 0
            }
        
        # Position importance weights
        position_weights = {
            'QB': 10,
            'RB': 5,
            'WR': 4,
            'TE': 3,
            'OL': 3,
            'DL': 3,
            'LB': 3,
            'CB': 4,
            'S': 3,
            'K': 1,
            'P': 1
        }
        
        # Status severity weights
        status_weights = {
            'Out': 3,
            'Injured Reserve': 3,
            'Doubtful': 2,
            'Questionable': 1,
            'Probable': 0.5
        }
        
        impact_score = 0
        key_injuries = []
        
        for injury in injuries:
            pos = injury['position']
            status = injury['injury_status']
            
            pos_weight = position_weights.get(pos, 2)
            status_weight = status_weights.get(status, 1)
            
            injury_impact = pos_weight * status_weight
            impact_score += injury_impact
            
            # Track key injuries (high impact positions)
            if pos in ['QB', 'RB', 'WR', 'CB'] and status in ['Out', 'Doubtful', 'Injured Reserve']:
                key_injuries.append({
                    'player': injury['name'],
                    'position': pos,
                    'status': status,
                    'impact': injury_impact
                })
        
        return {
            'impact_score': impact_score,
            'key_injuries': sorted(key_injuries, key=lambda x: x['impact'], reverse=True),
            'total_injuries': len(injuries)
        }

def main():
    fetcher = InjuryReportFetcher()
    
    print("=" * 70)
    print("NFL INJURY REPORT FETCHER")
    print("=" * 70)
    
    # Fetch current injuries from SportsData.io
    injuries = fetcher.fetch_sportsdata_injuries()
    
    # DEBUG: Show first few injuries
    print("\n=== First 3 injuries from API ===")
    for i, inj in enumerate(injuries[:3]):
        print(f"\nInjury {i+1}:")
        print(f"  Player: {inj['player_name']}")
        print(f"  Position: {inj['position']}")
        print(f"  Status field: {inj['status']}")
        print(f"  Injury_type field: {inj['injury_type']}")
    print("=== End Debug ===\n")
    
    if injuries:
        # Save to database
        fetcher.save_injuries_to_db(injuries)
        
        # Show summary by team
        print("\nInjury Summary by Team:")
        teams_with_injuries = {}
        
        for inj in injuries:
            team = inj['team_name']
            if team not in teams_with_injuries:
                teams_with_injuries[team] = []
            teams_with_injuries[team].append(inj)
        
        for team, team_injuries in sorted(teams_with_injuries.items()):
            # Fixed: use injury_type instead of status
            out_count = len([i for i in team_injuries if i['status'] in ['Out', 'Injured Reserve']])
            questionable_count = len([i for i in team_injuries if i['status'] == 'Questionable'])
            
            print(f"\n{team}:")
            print(f"  Out/IR: {out_count}")
            print(f"  Questionable: {questionable_count}")
            
            # Show key injuries - Fixed: use injury_type instead of status
            key_positions = ['QB', 'RB', 'WR', 'TE']
            for inj in team_injuries:
                if inj['position'] in key_positions and inj['status'] in ['Out', 'Doubtful', 'Injured Reserve']:
                    print(f"    ⚠️  {inj['player_name']} ({inj['position']}) - {inj['status']}")
    
    print("\n" + "=" * 70)
    print("✓ Injury data updated")
    print("=" * 70)

if __name__ == "__main__":
    main()