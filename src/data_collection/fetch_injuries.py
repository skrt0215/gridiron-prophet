import nfl_data_py as nfl
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DatabaseManager

class InjuryFetcher:
    """Fetch and store NFL injury data from multiple sources"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.current_season = 2025
        
    def fetch_historical_injuries(self, season):
        """Fetch historical injury data using nfl_data_py"""
        print(f"\nFetching historical injuries for {season}...")
        
        try:
            injuries_df = nfl.import_injuries([season])
            print(f"Found {len(injuries_df)} injury records")
            
            # Process and store in database
            for _, injury in injuries_df.iterrows():
                self._store_injury(injury, source='nfl_data_py')
            
            print(f"✓ Processed {len(injuries_df)} injury records")
            
        except Exception as e:
            print(f"Error fetching historical injuries: {e}")
    
    def fetch_live_injuries_espn(self):
        """Scrape current injury reports from ESPN"""
        print(f"\nFetching live injuries from ESPN...")
        
        url = "https://www.espn.com/nfl/injuries"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all team injury sections
            injury_count = 0
            teams = soup.find_all('div', class_='ResponsiveTable')
            
            for team_section in teams:
                # Extract team name
                team_header = team_section.find_previous('div', class_='Table__Title')
                if team_header:
                    team_name = team_header.text.strip()
                    team_abbr = self._get_team_abbreviation(team_name)
                    
                    # Find injury rows
                    rows = team_section.find_all('tr')[1:]  # Skip header
                    
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            player_name = cols[0].text.strip()
                            position = cols[1].text.strip()
                            injury = cols[2].text.strip()
                            status = cols[3].text.strip()
                            
                            injury_data = {
                                'team': team_abbr,
                                'full_name': player_name,
                                'position': position,
                                'report_primary_injury': injury,
                                'report_status': status,
                                'practice_status': status,
                                'date_modified': datetime.now(),
                                'season': self.current_season,
                                'week': self._get_current_week()
                            }
                            
                            self._store_injury(injury_data, source='espn_live')
                            injury_count += 1
            
            print(f"✓ Processed {injury_count} live injury reports")
            
        except Exception as e:
            print(f"Error fetching live injuries: {e}")
    
    def _store_injury(self, injury_data, source='unknown'):
        """Store injury data in database with player matching and updates"""
        try:
            # Get team
            team = self.db.get_team_by_abbreviation(injury_data.get('team', ''))
            
            if not team:
                print(f"Warning: Team not found for {injury_data.get('team', 'Unknown')}")
                return
            
            team_id = team['team_id']
            player_name = injury_data.get('full_name', '')
            position = injury_data.get('position', '')
            
            # Get or create player
            player_id = self._get_or_create_player(player_name, team_id, position)
            
            if not player_id:
                print(f"  ⚠ Could not create player: {player_name}")
                return
            
            # Check injury status
            status = injury_data.get('report_status', '')
            
            # If player is healthy/reactivated, update existing injury to resolved
            if status.lower() in ['active', 'healthy', 'cleared']:
                self._mark_injury_resolved(player_id)
                print(f"  ✓ {player_name} ({position}) - CLEARED/ACTIVATED")
                return
            
            # Check if injury already exists for this player
            existing_injury = self._get_active_injury(player_id)
            
            injury_body_part = injury_data.get('report_primary_injury', 'Unspecified')
            practice_status = injury_data.get('practice_status', status)
            date_reported = injury_data.get('date_modified', datetime.now())
            
            if existing_injury:
                # Update existing injury
                self.db.execute_update("""
                    UPDATE injuries 
                    SET injury_status = %s,
                        body_part = %s,
                        practice_status = %s,
                        notes = %s,
                        date_reported = %s
                    WHERE injury_id = %s
                """, (status, injury_body_part, practice_status, f'Source: {source}', 
                      date_reported, existing_injury['injury_id']))
                
                print(f"  ↻ {player_name} ({position}) - {injury_body_part} - {status} [UPDATED]")
            else:
                # Create new injury record
                self.db.add_injury(
                    player_id=player_id,
                    injury_status=status,
                    body_part=injury_body_part,
                    date_reported=date_reported,
                    practice_status=practice_status,
                    notes=f'Source: {source}'
                )
                
                print(f"  ✓ {player_name} ({position}) - {injury_body_part} - {status} [NEW]")
            
        except Exception as e:
            print(f"Error storing injury for {injury_data.get('full_name', 'Unknown')}: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_or_create_player(self, player_name, team_id, position):
        """Get existing player or create new one"""
        # Try to find existing player
        query = """
            SELECT player_id FROM players 
            WHERE name = %s AND team_id = %s
        """
        result = self.db.execute_query(query, (player_name, team_id))
        
        if result:
            return result[0]['player_id']
        
        # Create new player if not found
        try:
            player_id = self.db.add_player(
                name=player_name,
                team_id=team_id,
                position=position,
                status='Active'
            )
            return player_id
        except Exception as e:
            print(f"Error creating player {player_name}: {e}")
            return None
    
    def _get_active_injury(self, player_id):
        """Get active injury for a player"""
        query = """
            SELECT injury_id FROM injuries 
            WHERE player_id = %s 
            AND injury_status IN ('Out', 'Doubtful', 'Questionable', 'Injured Reserve')
            ORDER BY date_reported DESC
            LIMIT 1
        """
        result = self.db.execute_query(query, (player_id,))
        return result[0] if result else None
    
    def _mark_injury_resolved(self, player_id):
        """Mark all active injuries as resolved when player is cleared"""
        self.db.execute_update("""
            UPDATE injuries 
            SET injury_status = 'Resolved',
                practice_status = 'Full Participation in Practice'
            WHERE player_id = %s 
            AND injury_status IN ('Out', 'Doubtful', 'Questionable', 'Injured Reserve')
        """, (player_id,))
    
    def _get_team_abbreviation(self, team_name):
        """Convert full team name to abbreviation"""
        team_map = {
            'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
            'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
            'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
            'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
            'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
            'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
            'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
            'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
            'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
            'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
            'Tennessee Titans': 'TEN', 'Washington Commanders': 'WSH'
        }
        return team_map.get(team_name, team_name[:3].upper())
    
    def _get_current_week(self):
        """Determine current NFL week (simplified)"""
        # This is a simplified version - you'd want to calculate based on current date
        return 6
    
    def generate_injury_report(self):
        """Generate a summary of current injuries by team, sorted by most recent"""
        print("\n" + "="*60)
        print("CURRENT INJURY REPORT (Most Recent First)")
        print("="*60)
        
        # Get all active injuries ordered by date (newest first)
        query = """
            SELECT i.*, p.name as player_name, p.position, t.name as team_name, t.abbreviation as team_abbr
            FROM injuries i
            JOIN players p ON i.player_id = p.player_id
            LEFT JOIN teams t ON p.team_id = t.team_id
            WHERE i.injury_status IN ('Out', 'Doubtful', 'Questionable', 'Injured Reserve')
            ORDER BY i.date_reported DESC
        """
        
        injuries = self.db.execute_query(query)
        
        if not injuries:
            print("\n✓ No active injuries found in database")
            return
        
        print(f"\nTotal Active Injuries: {len(injuries)}\n")
        
        # Group by status for summary
        status_counts = {}
        qb_injuries = []
        
        for injury in injuries:
            status = injury['injury_status']
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Track QB injuries separately
            if injury['position'] == 'QB':
                qb_injuries.append(injury)
        
        # Show summary
        print("Status Breakdown:")
        for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {status}: {count} players")
        
        # Highlight QB injuries
        if qb_injuries:
            print(f"\n⚠️  CRITICAL: {len(qb_injuries)} Quarterback(s) Injured:")
            for qb in qb_injuries:
                print(f"  • {qb['player_name']} ({qb['team_abbr']}) - {qb['injury_status']}")
        
        # Show all injuries (most recent first)
        print("\n" + "-"*60)
        print("ALL ACTIVE INJURIES (Most Recent First):")
        print("-"*60)
        
        for idx, injury in enumerate(injuries[:50], 1):  # Show first 50
            date_str = injury['date_reported'].strftime('%Y-%m-%d') if injury['date_reported'] else 'Unknown'
            print(f"{idx}. [{date_str}] {injury['player_name']} ({injury['team_abbr']}, {injury['position']}) - "
                  f"{injury['body_part'] or 'Injury'} - {injury['injury_status']}")
        
        if len(injuries) > 50:
            print(f"\n... and {len(injuries) - 50} more injuries")
        
        print("\n" + "="*60)
    
    def run_full_update(self):
        """Run complete injury data update"""
        print("="*60)
        print("NFL INJURY DATA UPDATER")
        print("="*60)
        
        # Fetch live current injuries
        self.fetch_live_injuries_espn()
        
        # Optionally fetch historical for pattern analysis
        # self.fetch_historical_injuries(2024)
        
        # Generate report
        self.generate_injury_report()
        
        print("\n✓ Injury data update complete!")

if __name__ == "__main__":
    fetcher = InjuryFetcher()
    fetcher.run_full_update()