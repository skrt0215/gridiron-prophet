import sys
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager

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

ESPN_INJURY_URL = "https://www.espn.com/nfl/injuries"

def get_current_week() -> int:
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


def normalize_player_name(name):
    name = name.replace(' Jr.', '').replace(' Sr.', '')
    name = name.replace(' II', '').replace(' III', '').replace(' IV', '')
    parts = name.split()
    if len(parts) == 3 and len(parts[1]) <= 2:
        name = f"{parts[0]} {parts[2]}"
    return name.strip().lower()


def fetch_espn_injuries() -> List[Dict]:
    print(f"🔍 Fetching injuries from ESPN...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(ESPN_INJURY_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        injuries = []
        
        main_wrapper = soup.find('div', class_='Wrapper')
        if not main_wrapper:
            print("❌ Could not find main Wrapper on ESPN page")
            return []
        
        all_elements = main_wrapper.find_all(['div'], class_=['Table__Title', 'ResponsiveTable'])
        
        teams_and_tables = []
        pending_tables = []
        
        for element in all_elements:
            if 'Table__Title' in element.get('class', []):
                team_name = element.text.strip()
                teams_and_tables.append({
                    'team': team_name,
                    'tables': pending_tables + []
                })
                pending_tables = []
            
            elif 'ResponsiveTable' in element.get('class', []):
                pending_tables.append(element)
        
        team_count = 0
        for team_data in teams_and_tables:
            team_name = team_data['team']
            team_count += 1
            
            for table in team_data['tables']:
                rows = table.find_all('tr')[1:]
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 4:
                        continue
                    
                    player_name = cols[0].text.strip()
                    position = cols[1].text.strip()
                    injury_description = cols[2].text.strip()
                    injury_status = cols[3].text.strip()
                    
                    injuries.append({
                        'player_name': player_name,
                        'team': team_name,
                        'position': position,
                        'injury_status': injury_status,
                        'injury_description': injury_description,
                        'date_reported': datetime.now().strftime('%Y-%m-%d'),
                        'season': 2025,
                        'week': get_current_week()
                    })
        
        print(f"✓ Processed {team_count} teams")
        print(f"✅ Found {len(injuries)} injuries across all teams")
        return injuries
        
    except Exception as e:
        print(f"❌ Error fetching injuries: {e}")
        import traceback
        traceback.print_exc()
        return []


def find_player_id(db, player_name, team_id, player_cache):
    normalized_name = normalize_player_name(player_name)
    
    cache_key = f"{normalized_name}_{team_id}"
    if cache_key in player_cache:
        return player_cache[cache_key]
    
    result = db.execute_query("""
        SELECT p.player_id
        FROM players p
        JOIN player_seasons ps ON p.player_id = ps.player_id
        WHERE LOWER(p.name) = %s 
        AND ps.team_id = %s 
        AND ps.season = 2025
        LIMIT 1
    """, (normalized_name, team_id))
    
    player_id = result[0]['player_id'] if result else None
    player_cache[cache_key] = player_id
    
    return player_id


def update_injuries_smart(db: DatabaseManager, injuries: List[Dict]) -> Dict[str, int]:
    stats = {
        'new': 0,
        'updated': 0,
        'unchanged': 0,
        'resolved': 0,
        'not_found': 0
    }
    
    current_week = get_current_week()
    player_cache = {}
    
    existing = db.execute_query("""
        SELECT 
            p.name,
            t.abbreviation,
            i.injury_status,
            i.week,
            i.injury_id,
            i.player_id
        FROM injuries i
        JOIN players p ON i.player_id = p.player_id
        LEFT JOIN player_seasons ps ON i.player_id = ps.player_id AND i.season = ps.season
        LEFT JOIN teams t ON ps.team_id = t.team_id
        WHERE i.season = 2025
    """)
    
    existing_map = {
        (row['name'], row['abbreviation']): {
            'status': row['injury_status'],
            'week': row['week'],
            'injury_id': row['injury_id'],
            'player_id': row['player_id']
        }
        for row in existing if row['abbreviation']
    }
    
    fetched_players = set()
    
    for injury in injuries:
        team_abbrev = get_team_abbreviation(injury['team'])
        
        team_data = db.get_team_by_abbreviation(team_abbrev)
        if not team_data:
            stats['not_found'] += 1
            continue
        
        team_id = team_data['team_id']
        
        player_id = find_player_id(db, injury['player_name'], team_id, player_cache)
        
        if not player_id:
            stats['not_found'] += 1
            continue
        
        player_key = (injury['player_name'], team_abbrev)
        fetched_players.add(player_key)
        
        if player_key in existing_map:
            old_status = existing_map[player_key]['status']
            new_status = injury['injury_status']
            old_week = existing_map[player_key]['week']
            injury_id = existing_map[player_key]['injury_id']
            
            if old_status != new_status or old_week != current_week:
                db.execute_update("""
                    UPDATE injuries
                    SET injury_status = %s,
                        body_part = %s,
                        date_reported = %s,
                        week = %s,
                        notes = %s
                    WHERE injury_id = %s
                """, (
                    new_status,
                    injury['injury_description'],
                    injury['date_reported'],
                    current_week,
                    injury['injury_description'],
                    injury_id
                ))
                stats['updated'] += 1
            else:
                stats['unchanged'] += 1
        else:
            try:
                existing_ps = db.execute_query("""
                    SELECT player_id FROM player_seasons
                    WHERE player_id = %s AND season = %s
                """, (player_id, injury['season']))
                
                if not existing_ps:
                    db.add_player_season(
                        player_id=player_id,
                        season=injury['season'],
                        team_id=team_id,
                        position=injury['position'],
                        roster_status='Active'
                    )
                
                db.add_injury(
                    player_id=player_id,
                    season=injury['season'],
                    injury_status=injury['injury_status'],
                    date_reported=injury['date_reported'],
                    body_part=injury['injury_description'],
                    notes=injury['injury_description']
                )
                
                db.execute_update("""
                    UPDATE injuries
                    SET week = %s
                    WHERE player_id = %s
                    AND season = %s
                    AND date_reported = %s
                """, (current_week, player_id, injury['season'], injury['date_reported']))
                
                stats['new'] += 1
            except Exception as e:
                print(f"⚠️  Error adding injury for {injury['player_name']}: {e}")
    
    for player_key, data in existing_map.items():
        if player_key not in fetched_players and data['week'] == current_week:
            db.execute_update("""
                DELETE FROM injuries
                WHERE injury_id = %s
            """, (data['injury_id'],))
            stats['resolved'] += 1
    
    return stats


def get_team_abbreviation(team_name: str) -> str:
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
        'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS'
    }
    return team_map.get(team_name, team_name)


def main():
    db = DatabaseManager()
    
    try:
        print("\n" + "="*60)
        print("🏥 SMART INJURY UPDATER")
        print("="*60)
        print(f"📅 Current Week: {get_current_week()}")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
        
        injuries = fetch_espn_injuries()
        
        if not injuries:
            print("\n⚠️  No injuries fetched. Exiting.")
            return
        
        print(f"\n💾 Updating database...")
        stats = update_injuries_smart(db, injuries)
        
        print("\n" + "-"*60)
        print("✅ UPDATE COMPLETE:")
        print(f"  🆕 New Injuries: {stats['new']}")
        print(f"  🔄 Updated: {stats['updated']}")
        print(f"  ➖ Unchanged: {stats['unchanged']}")
        print(f"  ✅ Resolved: {stats['resolved']}")
        print(f"  ⚠️  Not Found in Roster: {stats['not_found']}")
        print("-"*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()