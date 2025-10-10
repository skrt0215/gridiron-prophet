import nfl_data_py as nfl
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DatabaseManager

class InjuryFetcherV2:
    """Fetch and store NFL injury data - V2 schema compatible"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.current_season = 2025
        self.current_week = 6
        
    def fetch_live_injuries_espn(self):
        print(f"\nFetching live injuries from ESPN...")
        
        url = "https://www.espn.com/nfl/injuries"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            injury_count = 0
            teams = soup.find_all('div', class_='ResponsiveTable')
            
            for team_section in teams:
                team_header = team_section.find_previous('div', class_='Table__Title')
                if team_header:
                    team_name = team_header.text.strip()
                    team_abbr = self._get_team_abbreviation(team_name)
                    
                    rows = team_section.find_all('tr')[1:]
                    
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            player_name = cols[0].text.strip()
                            position = cols[1].text.strip()
                            body_part = cols[2].text.strip()
                            status = cols[3].text.strip()
                            
                            injury_data = {
                                'team': team_abbr,
                                'full_name': player_name,
                                'position': position,
                                'body_part': body_part,
                                'status': status,
                                'date_reported': datetime.now().date(),
                                'season': self.current_season,
                                'week': self.current_week
                            }
                            
                            self._store_injury(injury_data)
                            injury_count += 1
            
            print(f"✓ Processed {injury_count} live injury reports")
            
        except Exception as e:
            print(f"Error fetching live injuries: {e}")
    
    def _store_injury(self, injury_data):
        try:
            team = self.db.get_team_by_abbreviation(injury_data.get('team', ''))
            
            if not team:
                print(f"Warning: Team not found for {injury_data.get('team', 'Unknown')}")
                return
            
            team_id = team['team_id']
            player_name = injury_data.get('full_name', '')
            position = injury_data.get('position', '')
            
            player_id = self._get_or_create_player(player_name, team_id, position)
            
            if not player_id:
                return
            
            status = injury_data.get('status', '')
            
            if status.lower() in ['active', 'healthy', 'cleared']:
                self._mark_injury_resolved(player_id)
                print(f"  ✓ {player_name} ({position}) - CLEARED/ACTIVATED")
                return
            
            existing_injury = self._get_active_injury(player_id, self.current_season)
            
            body_part = injury_data.get('body_part', 'Unspecified')
            date_reported = injury_data.get('date_reported', datetime.now().date())
            season = injury_data.get('season', self.current_season)
            week = injury_data.get('week', self.current_week)
            
            if existing_injury:
                self.db.execute_update("""
                    UPDATE injuries 
                    SET injury_status = %s,
                        body_part = %s,
                        practice_status = %s,
                        week = %s,
                        date_reported = %s
                    WHERE injury_id = %s
                """, (status, body_part, status, week, date_reported, existing_injury['injury_id']))
                
                print(f"  ↻ {player_name} ({position}) - {body_part} - {status} [UPDATED]")
            else:
                self.db.execute_insert("""
                    INSERT INTO injuries
                    (player_id, season, week, injury_status, body_part, 
                     date_reported, practice_status, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (player_id, season, week, status, body_part, 
                      date_reported, status, 'Source: espn_live'))
                
                print(f"  ✓ {player_name} ({position}) - {body_part} - {status} [NEW]")
            
        except Exception as e:
            print(f"Error storing injury for {injury_data.get('full_name', 'Unknown')}: {e}")
    
    def _get_or_create_player(self, player_name, team_id, position):
        """Get or create player in V2 schema"""
        query = """
            SELECT p.player_id 
            FROM players p
            JOIN player_seasons ps ON p.player_id = ps.player_id
            WHERE p.name = %s 
            AND ps.team_id = %s 
            AND ps.season = %s
        """
        result = self.db.execute_query(query, (player_name, team_id, self.current_season))
        
        if result:
            return result[0]['player_id']
        
        query = """
            SELECT p.player_id, p.name 
            FROM players p
            JOIN player_seasons ps ON p.player_id = ps.player_id
            WHERE ps.team_id = %s 
            AND ps.season = %s
            AND p.position = %s
        """
        result = self.db.execute_query(query, (team_id, self.current_season, position))
        
        if result:
            player_name_clean = player_name.lower().replace("'", "").replace(".", "").replace("-", "").replace(" jr", "").replace(" sr", "").replace(" ii", "").replace(" iii", "").strip()
            
            for player in result:
                db_name_clean = player['name'].lower().replace("'", "").replace(".", "").replace("-", "").replace(" jr", "").replace(" sr", "").replace(" ii", "").replace(" iii", "").strip()
                
                if player_name_clean == db_name_clean or player_name_clean in db_name_clean or db_name_clean in player_name_clean:
                    return player['player_id']
        
        print(f"  → Creating new player: {player_name} ({position}) for team_id {team_id}")
        
        player_id = self.db.execute_insert(
            "INSERT INTO players (name, team_id, position) VALUES (%s, %s, %s)",
            (player_name, team_id, position)
        )
        
        self.db.execute_insert("""
            INSERT INTO player_seasons (player_id, season, team_id, position, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (player_id, self.current_season, team_id, position, 'Active'))
        
        return player_id
    
    def _get_active_injury(self, player_id, season):
        query = """
            SELECT injury_id FROM injuries 
            WHERE player_id = %s 
            AND season = %s
            AND injury_status IN ('Out', 'Doubtful', 'Questionable', 'Injured Reserve')
            ORDER BY date_reported DESC
            LIMIT 1
        """
        result = self.db.execute_query(query, (player_id, season))
        return result[0] if result else None
    
    def _mark_injury_resolved(self, player_id):
        self.db.execute_update("""
            UPDATE injuries 
            SET injury_status = 'Resolved',
                practice_status = 'Full Participation in Practice'
            WHERE player_id = %s 
            AND season = %s
            AND injury_status IN ('Out', 'Doubtful', 'Questionable', 'Injured Reserve')
        """, (player_id, self.current_season))
    
    def _get_team_abbreviation(self, team_name):
        team_map = {
            'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
            'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
            'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
            'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
            'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
            'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
            'Los Angeles Rams': 'LA', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
            'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
            'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
            'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
            'Tennessee Titans': 'TEN', 'Washington Commanders': 'WSH'
        }
        return team_map.get(team_name, team_name[:3].upper())
    
    def generate_injury_report(self):
        print("\n" + "="*60)
        print("CURRENT INJURY REPORT (Most Recent First)")
        print("="*60)
        
        query = """
            SELECT i.*, p.name as player_name, p.position, 
                   t.name as team_name, t.abbreviation as team_abbr
            FROM injuries i
            JOIN players p ON i.player_id = p.player_id
            JOIN player_seasons ps ON p.player_id = ps.player_id AND i.season = ps.season
            JOIN teams t ON ps.team_id = t.team_id
            WHERE i.injury_status IN ('Out', 'Doubtful', 'Questionable', 'Injured Reserve')
            AND i.season = %s
            ORDER BY i.date_reported DESC
        """
        
        injuries = self.db.execute_query(query, (self.current_season,))
        
        if not injuries:
            print("\n✓ No active injuries found in database")
            return
        
        print(f"\nTotal Active Injuries: {len(injuries)}\n")
        
        status_counts = {}
        qb_injuries = []
        
        for injury in injuries:
            status = injury['injury_status']
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if injury['position'] == 'QB':
                qb_injuries.append(injury)
        
        print("Status Breakdown:")
        for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {status}: {count} players")
        
        if qb_injuries:
            print(f"\n⚠️  CRITICAL: {len(qb_injuries)} Quarterback(s) Injured:")
            for qb in qb_injuries:
                print(f"  • {qb['player_name']} ({qb['team_abbr']}) - {qb['injury_status']}")
        
        print("\n" + "-"*60)
        print("ALL ACTIVE INJURIES (Most Recent First):")
        print("-"*60)
        
        for idx, injury in enumerate(injuries[:50], 1):
            date_str = injury['date_reported'].strftime('%Y-%m-%d') if injury['date_reported'] else 'Unknown'
            body_part = injury['body_part'] if injury['body_part'] else 'Injury'
            print(f"{idx}. [{date_str}] {injury['player_name']} ({injury['team_abbr']}, {injury['position']}) - "
                  f"{body_part} - {injury['injury_status']}")
        
        if len(injuries) > 50:
            print(f"\n... and {len(injuries) - 50} more injuries")
        
        print("\n" + "="*60)
    
    def run_full_update(self):
        print("="*60)
        print("NFL INJURY DATA UPDATER - V2")
        print("="*60)
        
        self.fetch_live_injuries_espn()
        self.generate_injury_report()
        
        print("\n✓ Injury data update complete!")

if __name__ == "__main__":
    fetcher = InjuryFetcherV2()
    fetcher.run_full_update()