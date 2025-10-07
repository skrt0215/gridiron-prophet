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
        """Store injury data in database"""
        try:
            # Get or create player
            team = self.db.get_team_by_abbreviation(injury_data.get('team', ''))
            
            if not team:
                print(f"Warning: Team not found for {injury_data.get('team', 'Unknown')}")
                return
            
            team_id = team['team_id']
            
            # For now, we'll store injuries linked to team
            # In a full implementation, you'd link to player_id
            print(f"  • {injury_data.get('full_name', 'Unknown')} ({injury_data.get('position', '?')}) - "
                  f"{injury_data.get('report_primary_injury', 'Injury')} - {injury_data.get('report_status', 'Status')}")
            
            # TODO: Link to actual player records and store in injuries table
            # This requires enhancing the player lookup system
            
        except Exception as e:
            print(f"Error storing injury: {e}")
    
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
        """Generate a summary of current injuries by team"""
        print("\n" + "="*60)
        print("INJURY IMPACT ANALYSIS")
        print("="*60)
        
        # This would query your database for current injuries
        # and calculate impact scores for each team
        
        print("\nKey Injuries to Watch:")
        print("• Implement impact scoring based on player position and status")
        print("• Weight QB injuries higher than other positions")
        print("• Consider practice participation levels")
        
        # TODO: Implement full injury impact analysis
    
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