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
        
        injury_tables = soup.find_all('div', class_='ResponsiveTable')
        
        for table in injury_tables:
            team_header = table.find_previous('div', class_='Table__Title')
            if not team_header:
                continue
                
            team_name = team_header.text.strip()
            
            rows = table.find_all('tr')[1:]
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                
                player_name = cols[0].text.strip()
                position = cols[1].text.strip()
                injury_status = cols[2].text.strip()
                injury_description = cols[3].text.strip()
                
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
        
        print(f"✅ Found {len(injuries)} injuries")
        return injuries
        
    except Exception as e:
        print(f"❌ Error fetching injuries: {e}")
        return []


def update_injuries_smart(db: DatabaseManager, injuries: List[Dict]) -> Dict[str, int]:
    stats = {
        'new': 0,
        'updated': 0,
        'unchanged': 0,
        'resolved': 0
    }
    
    current_week = get_current_week()
    
    existing = db.fetch_all("""
        SELECT player_name, team, injury_status, week
        FROM injuries
        WHERE season = 2025
    """)
    
    existing_map = {
        (row[0], row[1]): {'status': row[2], 'week': row[3]}
        for row in existing
    }
    
    fetched_players = set()
    
    for injury in injuries:
        player_key = (injury['player_name'], injury['team'])
        fetched_players.add(player_key)
        
        if player_key in existing_map:
            old_status = existing_map[player_key]['status']
            new_status = injury['injury_status']
            old_week = existing_map[player_key]['week']
            
            if old_status != new_status or old_week != current_week:
                db.execute("""
                    UPDATE injuries
                    SET injury_status = ?,
                        injury_description = ?,
                        date_reported = ?,
                        week = ?
                    WHERE player_name = ?
                    AND team = ?
                    AND season = 2025
                """, (
                    new_status,
                    injury['injury_description'],
                    injury['date_reported'],
                    current_week,
                    injury['player_name'],
                    injury['team']
                ))
                stats['updated'] += 1
            else:
                stats['unchanged'] += 1
        else:
            db.execute("""
                INSERT INTO injuries (
                    player_name, team, position, injury_status,
                    injury_description, date_reported, season, week
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                injury['player_name'],
                injury['team'],
                injury['position'],
                injury['injury_status'],
                injury['injury_description'],
                injury['date_reported'],
                injury['season'],
                injury['week']
            ))
            stats['new'] += 1
    
    for player_key, data in existing_map.items():
        if player_key not in fetched_players and data['week'] == current_week:
            db.execute("""
                DELETE FROM injuries
                WHERE player_name = ?
                AND team = ?
                AND season = 2025
            """, player_key)
            stats['resolved'] += 1
    
    return stats


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
        print("-"*60)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()