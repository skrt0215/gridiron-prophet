import requests
from bs4 import BeautifulSoup
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DatabaseManager

class OfficialRosterScraper:
    """Scrape official 53-man rosters from NFL.com to fix roster_status"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_team_roster_from_nfl(self, team_abbr):
        """Scrape official roster from NFL.com"""
        # NFL.com uses different abbreviations sometimes
        nfl_team_map = {
            'LA': 'LAR',  # Rams
            'LV': 'LV',   # Raiders
        }
        
        nfl_abbr = nfl_team_map.get(team_abbr, team_abbr)
        url = f"https://www.nfl.com/teams/{nfl_abbr.lower()}/roster"
        
        print(f"  Fetching {team_abbr} roster from NFL.com...")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # NFL.com roster structure - look for player names
            players = []
            
            # Try multiple selectors as NFL.com layout changes
            player_elements = (
                soup.find_all('div', class_='nfl-o-roster__person-name') or
                soup.find_all('a', class_='d3-o-player-fullname') or
                soup.select('.nfl-c-player-header__name')
            )
            
            for elem in player_elements:
                name = elem.get_text(strip=True)
                if name and len(name) > 2:  # Basic validation
                    players.append(name)
            
            return list(set(players))  # Remove duplicates
            
        except Exception as e:
            print(f"    Error scraping {team_abbr}: {e}")
            return None
    
    def get_team_roster_from_espn(self, team_abbr):
        """Backup: Scrape from ESPN if NFL.com fails"""
        # ESPN team abbreviations
        espn_team_map = {
            'LA': 'lar',
            'LV': 'lv',
        }
        
        espn_abbr = espn_team_map.get(team_abbr, team_abbr.lower())
        url = f"https://www.espn.com/nfl/team/roster/_/name/{espn_abbr}"
        
        print(f"  Trying ESPN for {team_abbr}...")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            players = []
            player_links = soup.find_all('a', class_='AnchorLink')
            
            for link in player_links:
                if '/nfl/player/' in link.get('href', ''):
                    name = link.get_text(strip=True)
                    if name and len(name) > 2:
                        players.append(name)
            
            return list(set(players))
            
        except Exception as e:
            print(f"    Error with ESPN {team_abbr}: {e}")
            return None
    
    def normalize_name(self, name):
        """Normalize player names for matching"""
        # Remove Jr., Sr., II, III, etc.
        name = name.replace(' Jr.', '').replace(' Sr.', '')
        name = name.replace(' II', '').replace(' III', '').replace(' IV', '')
        
        # Remove middle initials
        parts = name.split()
        if len(parts) == 3 and len(parts[1]) <= 2:
            name = f"{parts[0]} {parts[2]}"
        
        return name.strip().lower()
    
    def mark_active_roster(self, team_abbr, official_roster):
        """Mark players as Active or Practice Squad based on official roster"""
        if not official_roster:
            print(f"    No roster data for {team_abbr}, skipping...")
            return 0
        
        # Get team_id
        team = self.db.get_team_by_abbreviation(team_abbr)
        if not team:
            print(f"    Team {team_abbr} not found in database")
            return 0
        
        team_id = team['team_id']
        
        # Normalize official roster names
        official_normalized = {self.normalize_name(name): name for name in official_roster}
        
        # Get all players for this team in 2025 season
        db_players = self.db.execute_query("""
            SELECT ps.player_season_id, p.name, ps.roster_status
            FROM player_seasons ps
            JOIN players p ON ps.player_id = p.player_id
            WHERE ps.team_id = %s AND ps.season = 2025
        """, (team_id,))
        
        active_count = 0
        practice_count = 0
        
        for player in db_players:
            db_name_normalized = self.normalize_name(player['name'])
            
            # Check if player is in official roster
            if db_name_normalized in official_normalized:
                # Mark as Active (53-man roster)
                self.db.execute_update("""
                    UPDATE player_seasons 
                    SET roster_status = 'Active'
                    WHERE player_season_id = %s
                """, (player['player_season_id'],))
                active_count += 1
            else:
                # Mark as Practice Squad or Inactive
                self.db.execute_update("""
                    UPDATE player_seasons 
                    SET roster_status = 'Practice Squad'
                    WHERE player_season_id = %s
                """, (player['player_season_id'],))
                practice_count += 1
        
        print(f"    ✓ {team_abbr}: {active_count} active, {practice_count} practice squad")
        return active_count
    
    def fix_all_rosters(self):
        """Fix roster_status for all teams"""
        print("\n" + "="*60)
        print("OFFICIAL ROSTER SCRAPER")
        print("="*60)
        print("\nFetching official 53-man rosters for all 32 teams...")
        print("This may take a few minutes...\n")
        
        # Get all teams
        teams = self.db.get_all_teams()
        
        success_count = 0
        failed_teams = []
        
        for team in teams:
            team_abbr = team['abbreviation']
            
            # Try NFL.com first
            roster = self.get_team_roster_from_nfl(team_abbr)
            
            # If NFL.com fails, try ESPN
            if not roster or len(roster) < 40:
                roster = self.get_team_roster_from_espn(team_abbr)
            
            if roster and len(roster) >= 40:
                active_count = self.mark_active_roster(team_abbr, roster)
                if 40 <= active_count <= 60:  # Reasonable range
                    success_count += 1
                else:
                    failed_teams.append(f"{team_abbr} ({active_count} players)")
            else:
                failed_teams.append(f"{team_abbr} (no data)")
                print(f"    ⚠️  Could not get roster for {team_abbr}")
            
            # Be nice to servers
            time.sleep(1)
        
        print("\n" + "="*60)
        print(f"✓ Successfully updated {success_count}/32 teams")
        
        if failed_teams:
            print(f"\n⚠️  Failed teams: {', '.join(failed_teams)}")
            print("\nFor failed teams, you may need to manually verify rosters.")
        
        # Verify final counts
        self.verify_final_rosters()
    
    def verify_final_rosters(self):
        """Verify roster counts after fixing"""
        print("\n" + "="*60)
        print("FINAL VERIFICATION")
        print("="*60)
        
        result = self.db.execute_query("""
            SELECT 
                t.abbreviation,
                COUNT(CASE WHEN ps.roster_status = 'Active' THEN 1 END) as active,
                COUNT(CASE WHEN ps.roster_status = 'Practice Squad' THEN 1 END) as practice
            FROM teams t
            LEFT JOIN player_seasons ps ON t.team_id = ps.team_id AND ps.season = 2025
            GROUP BY t.team_id
            ORDER BY active DESC
        """)
        
        print(f"\n{'Team':<5} {'Active':<8} {'Practice':<10}")
        print("-" * 30)
        
        perfect_teams = 0
        for r in result:
            status = "✓" if 50 <= r['active'] <= 55 else "⚠️"
            print(f"{status} {r['abbreviation']:<5} {r['active']:<8} {r['practice']:<10}")
            if 50 <= r['active'] <= 55:
                perfect_teams += 1
        
        print(f"\n{perfect_teams}/32 teams have proper active roster counts")

if __name__ == "__main__":
    scraper = OfficialRosterScraper()
    scraper.fix_all_rosters()