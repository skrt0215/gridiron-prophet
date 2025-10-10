"""
ESPN Injury Report Fetcher
Fetches current NFL injury reports via web scraping
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup
from database.db_manager import DatabaseManager
from datetime import datetime, date
import time

class InjuryFetcher:
    """Fetch NFL injury reports from ESPN"""
    
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
        
        self.player_cache = {}
    
    def normalize_player_name(self, name):
        """Normalize player names for matching"""
        name = name.replace(' Jr.', '').replace(' Sr.', '')
        name = name.replace(' II', '').replace(' III', '').replace(' IV', '')
        parts = name.split()
        if len(parts) == 3 and len(parts[1]) <= 2:
            name = f"{parts[0]} {parts[2]}"
        
        return name.strip().lower()
    
    def get_all_injuries_from_espn(self):
        """Fetch all NFL injuries from ESPN's injury page"""
        url = "https://www.espn.com/nfl/injuries"
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            injuries_by_team = {}
            tables = soup.find_all('table')
            
            print(f"  Found {len(tables)} tables on page\n")
            
            for idx, table in enumerate(tables): 
                team_abbr = None
                team_text = None
                parent = table.find_parent()
                for _ in range(5):
                    if parent is None:
                        break
                    
                    for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
                        heading = parent.find(tag)
                        if heading:
                            team_text = heading.get_text(strip=True)
                            team_abbr = self.extract_team_abbr(team_text)
                            if team_abbr:
                                break
                    
                    if team_abbr:
                        break
                    parent = parent.find_parent()
                
                if not team_abbr:
                    elem = table
                    for _ in range(20):
                        elem = elem.find_previous()
                        if elem is None:
                            break
                        
                        if elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'div', 'span']:
                            text = elem.get_text(strip=True)
                            if text and len(text) > 3:
                                team_abbr = self.extract_team_abbr(text)
                                if team_abbr:
                                    team_text = text
                                    break
                
                if not team_abbr:
                    print(f"  Table {idx+1}: Could not find team name")
                    continue
                
                print(f"  Table {idx+1}: {team_abbr} ({team_text})")
                rows = table.find_all('tr')
                
                if len(rows) < 2:
                    continue
                team_injuries = []
                
                for row in rows[1:]:
                    try:
                        cells = row.find_all('td')
                        
                        if len(cells) < 2:
                            continue
                        name_cell = cells[0]
                        player_link = name_cell.find('a')
                        player_name = player_link.get_text(strip=True) if player_link else name_cell.get_text(strip=True)
                        
                        if not player_name:
                            continue
                        
                        position = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                        status = cells[-1].get_text(strip=True)
                        injury_type = ''
                        if len(cells) >= 3:
                            injury_type = cells[2].get_text(strip=True)
                        
                        if player_name and status:
                            team_injuries.append({
                                'name': player_name,
                                'position': position,
                                'status': status,
                                'type': injury_type if injury_type else 'Unknown'
                            })
                    
                    except Exception as e:
                        continue
                
                if team_injuries:
                    print(f"    → Found {len(team_injuries)} injuries")
                    if team_abbr not in injuries_by_team:
                        injuries_by_team[team_abbr] = []
                    injuries_by_team[team_abbr].extend(team_injuries)
                else:
                    print(f"    → No injuries found in table")
            
            return injuries_by_team
            
        except Exception as e:
            print(f"  ✗ Error fetching injury page: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def extract_team_abbr(self, team_name):
        """Extract team abbreviation from full name"""
        name_map = {
            'Arizona Cardinals': 'ARI',
            'Atlanta Falcons': 'ATL',
            'Baltimore Ravens': 'BAL',
            'Buffalo Bills': 'BUF',
            'Carolina Panthers': 'CAR',
            'Chicago Bears': 'CHI',
            'Cincinnati Bengals': 'CIN',
            'Cleveland Browns': 'CLE',
            'Dallas Cowboys': 'DAL',
            'Denver Broncos': 'DEN',
            'Detroit Lions': 'DET',
            'Green Bay Packers': 'GB',
            'Houston Texans': 'HOU',
            'Indianapolis Colts': 'IND',
            'Jacksonville Jaguars': 'JAX',
            'Kansas City Chiefs': 'KC',
            'Las Vegas Raiders': 'LV',
            'Los Angeles Chargers': 'LAC',
            'Los Angeles Rams': 'LA',
            'Miami Dolphins': 'MIA',
            'Minnesota Vikings': 'MIN',
            'New England Patriots': 'NE',
            'New Orleans Saints': 'NO',
            'New York Giants': 'NYG',
            'New York Jets': 'NYJ',
            'Philadelphia Eagles': 'PHI',
            'Pittsburgh Steelers': 'PIT',
            'San Francisco 49ers': 'SF',
            'Seattle Seahawks': 'SEA',
            'Tampa Bay Buccaneers': 'TB',
            'Tennessee Titans': 'TEN',
            'Washington Commanders': 'WAS'
        }
        
        for full_name, abbr in name_map.items():
            if full_name in team_name:
                return abbr
        
        return None
    
    def parse_injury_status(self, status_str):
        """Parse ESPN injury status to our format"""
        if not status_str:
            return 'Questionable', None
        
        status = status_str.upper().strip()
        
        if 'OUT' in status:
            return 'Out', None
        elif 'DOUBTFUL' in status:
            return 'Doubtful', None
        elif 'QUESTIONABLE' in status or 'QUEST' in status:
            return 'Questionable', None
        elif 'IR' in status or 'INJURED RESERVE' in status:
            return 'IR', None
        elif 'PUP' in status:
            return 'PUP', None
        elif 'NFI' in status:
            return 'NFI', None
        elif 'PROBABLE' in status:
            return 'Questionable', None
        else:
            return 'Questionable', None
    
    def find_player_id(self, player_name, team_id):
        """Find player_id in database"""
        normalized_name = self.normalize_player_name(player_name)
        
        cache_key = f"{normalized_name}_{team_id}"
        if cache_key in self.player_cache:
            return self.player_cache[cache_key]
        
        result = self.db.execute_query("""
            SELECT p.player_id
            FROM players p
            JOIN player_seasons ps ON p.player_id = ps.player_id
            WHERE LOWER(p.name) = %s 
            AND ps.team_id = %s 
            AND ps.season = 2025
            LIMIT 1
        """, (normalized_name, team_id))
        
        player_id = result[0]['player_id'] if result else None
        self.player_cache[cache_key] = player_id
        
        return player_id
    
    def add_injury_to_db_scraped(self, injury_data, team_id, season=2025):
        """Add a scraped injury to the database"""
        try:
            player_name = injury_data.get('name')
            if not player_name:
                return False
            
            player_id = self.find_player_id(player_name, team_id)
            if not player_id:
                return False
            
            injury_status_raw = injury_data.get('status', '')
            injury_status, practice_status = self.parse_injury_status(injury_status_raw)
            body_part = injury_data.get('type', 'Unknown')
            date_reported = date.today()
            
            self.db.add_injury(
                player_id=player_id,
                season=season,
                injury_status=injury_status,
                date_reported=date_reported,
                body_part=body_part,
                practice_status=practice_status,
                notes=f"{injury_status_raw} - {body_part}"
            )
            
            return True
            
        except Exception as e:
            return False
    
    def clear_current_injuries(self, season=2025):
        """Clear existing injuries for the current season"""
        print("\nClearing existing 2025 injury data...")
        count = self.db.execute_update("DELETE FROM injuries WHERE season = %s", (season,))
        print(f"✓ Cleared {count} old injury records")
    
    def fetch_all_injuries(self, season=2025):
        """Fetch injuries for all teams via web scraping"""
        print("\n" + "="*70)
        print("FETCHING NFL INJURY REPORTS")
        print("="*70)
        print(f"\nScraping injury data from ESPN...\n")
        
        injuries_by_team = self.get_all_injuries_from_espn()
        
        if not injuries_by_team:
            print("✗ No injury data found. ESPN page structure may have changed.")
            return 0
        
        print(f"Found injuries for {len(injuries_by_team)} teams\n")
        
        total_injuries = 0
        
        for team_abbr, injuries in injuries_by_team.items():
            team = self.db.get_team_by_abbreviation(team_abbr)
            if not team:
                print(f"  ⚠️  Team not found in DB: {team_abbr}")
                continue
            
            team_id = team['team_id']
            
            print(f"{team_abbr}...", end=" ")
            
            team_injury_count = 0
            for injury in injuries:
                if self.add_injury_to_db_scraped(injury, team_id, season):
                    team_injury_count += 1
            
            if team_injury_count > 0:
                print(f"✓ {team_injury_count} injuries")
                total_injuries += team_injury_count
            else:
                print(f"({len(injuries)} found, 0 matched)")
            
            time.sleep(0.1)
        
        print(f"\n{'='*70}")
        print(f"✓ Added {total_injuries} injuries")
        print(f"{'='*70}")
        
        return total_injuries
    
    def verify_injuries(self, season=2025):
        """Verify and display injury data"""
        print("\n" + "="*70)
        print("INJURY REPORT VERIFICATION")
        print("="*70)
        
        result = self.db.execute_query("""
            SELECT 
                injury_status,
                COUNT(*) as count
            FROM injuries
            WHERE season = %s
            GROUP BY injury_status
            ORDER BY 
                CASE injury_status
                    WHEN 'Out' THEN 1
                    WHEN 'Doubtful' THEN 2
                    WHEN 'Questionable' THEN 3
                    WHEN 'IR' THEN 4
                    WHEN 'PUP' THEN 5
                    ELSE 6
                END
        """, (season,))
        
        print(f"\n{'Status':<20} {'Count':<10}")
        print("-" * 35)
        
        total = 0
        for r in result:
            print(f"{r['injury_status']:<20} {r['count']:<10}")
            total += r['count']
        
        print("-" * 35)
        print(f"{'TOTAL':<20} {total:<10}")
        
        print("\n" + "-"*70)
        print("Injuries Per Team:")
        print("-"*70)
        
        team_result = self.db.execute_query("""
            SELECT 
                t.abbreviation,
                COUNT(i.injury_id) as injury_count,
                COUNT(CASE WHEN i.injury_status = 'Out' THEN 1 END) as out_count,
                COUNT(CASE WHEN i.injury_status = 'IR' THEN 1 END) as ir_count
            FROM teams t
            LEFT JOIN player_seasons ps ON t.team_id = ps.team_id AND ps.season = %s
            LEFT JOIN injuries i ON ps.player_id = i.player_id AND i.season = %s
            GROUP BY t.team_id, t.abbreviation
            HAVING injury_count > 0
            ORDER BY injury_count DESC
        """, (season, season))
        
        print(f"\n{'Team':<8} {'Total':<10} {'Out':<8} {'IR':<8}")
        print("-" * 40)
        
        for r in team_result:
            print(f"{r['abbreviation']:<8} {r['injury_count']:<10} "
                  f"{r['out_count']:<8} {r['ir_count']:<8}")
        
        print("\n" + "-"*70)
        print("Sample Injury Report:")
        print("-"*70)
        
        sample = self.db.execute_query("""
            SELECT 
                p.name,
                ps.position,
                t.abbreviation as team,
                i.injury_status,
                i.body_part,
                i.date_reported
            FROM injuries i
            JOIN players p ON i.player_id = p.player_id
            JOIN player_seasons ps ON i.player_id = ps.player_id AND i.season = ps.season
            JOIN teams t ON ps.team_id = t.team_id
            WHERE i.season = %s
            ORDER BY 
                CASE i.injury_status
                    WHEN 'Out' THEN 1
                    WHEN 'IR' THEN 2
                    WHEN 'Doubtful' THEN 3
                    ELSE 4
                END,
                t.abbreviation
            LIMIT 20
        """, (season,))
        
        print(f"\n{'Team':<6} {'Player':<25} {'Pos':<5} {'Status':<15} {'Injury':<15}")
        print("-" * 75)
        
        for r in sample:
            print(f"{r['team']:<6} {r['name']:<25} {r['position']:<5} "
                  f"{r['injury_status']:<15} {r['body_part']:<15}")
    
    def run(self, clear_existing=True):
        """Run the full injury fetch process"""
        print("\n" + "="*70)
        print("GRIDIRON PROPHET - INJURY REPORT FETCHER")
        print("="*70)
        print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if clear_existing:
            self.clear_current_injuries(2025)
        
        total = self.fetch_all_injuries(2025)
        
        if total > 0:
            self.verify_injuries(2025)
        else:
            print("\n⚠️  No injuries found. This might be an API issue.")
        
        print("\n" + "="*70)
        print("✓ INJURY FETCH COMPLETE!")
        print("="*70)
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nYour prediction model can now factor in current injuries!")

if __name__ == "__main__":
    fetcher = InjuryFetcher()
    fetcher.run(clear_existing=True)