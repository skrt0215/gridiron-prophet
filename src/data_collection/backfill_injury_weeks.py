import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional

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


def date_to_week(date_str: str) -> Optional[int]:
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        for week, (start_str, end_str) in SEASON_2025_WEEKS.items():
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_str, "%Y-%m-%d").date()
            
            if start <= date <= end:
                return week
        
        last_week_end = datetime.strptime(SEASON_2025_WEEKS[18][1], "%Y-%m-%d").date()
        if date > last_week_end:
            return 18
            
        return None
        
    except Exception as e:
        print(f"⚠️  Error parsing date {date_str}: {e}")
        return None


def backfill_injury_weeks(db: DatabaseManager, dry_run: bool = False) -> Dict[str, int]:
    print("\n" + "="*60)
    print("🏈 BACKFILLING INJURY WEEKS")
    print("="*60)
    
    injuries = db.execute_query("""
        SELECT 
            i.injury_id,
            p.name as player_name,
            COALESCE(t.abbreviation, 'UNK') as team,
            i.date_reported,
            i.week
        FROM injuries i
        JOIN players p ON i.player_id = p.player_id
        LEFT JOIN player_seasons ps ON i.player_id = ps.player_id AND i.season = ps.season
        LEFT JOIN teams t ON ps.team_id = t.team_id
        WHERE i.season = 2025
        ORDER BY i.date_reported
    """)
    
    if not injuries:
        print("❌ No injuries found for 2025 season")
        return {"total": 0, "updated": 0, "skipped": 0, "failed": 0}
    
    print(f"📊 Found {len(injuries)} injuries to process")
    
    stats = {
        "total": len(injuries),
        "updated": 0,
        "skipped": 0,
        "failed": 0
    }
    
    week_distribution = {}
    
    for injury in injuries:
        injury_id = injury['injury_id']
        player_name = injury['player_name']
        team = injury['team'] or 'Unknown'
        date_reported = injury['date_reported']
        current_week = injury['week']
        
        if current_week is not None:
            stats["skipped"] += 1
            continue
        
        week = date_to_week(str(date_reported))
        
        if week is None:
            print(f"⚠️  Cannot determine week for {player_name} ({team}) - {date_reported}")
            stats["failed"] += 1
            continue
        
        if not dry_run:
            db.execute_update("""
                UPDATE injuries
                SET week = ?
                WHERE injury_id = ?
            """, (week, injury_id))
        
        week_distribution[week] = week_distribution.get(week, 0) + 1
        stats["updated"] += 1
    
    print("\n" + "-"*60)
    print("📈 WEEK DISTRIBUTION:")
    for week in sorted(week_distribution.keys()):
        count = week_distribution[week]
        bar = "█" * (count // 5)
        print(f"  Week {week:2d}: {count:3d} injuries {bar}")
    
    print("\n" + "-"*60)
    print("✅ BACKFILL SUMMARY:")
    print(f"  Total Injuries: {stats['total']}")
    print(f"  ✅ Updated: {stats['updated']}")
    print(f"  ⏭️  Skipped (already had week): {stats['skipped']}")
    print(f"  ❌ Failed: {stats['failed']}")
    
    if dry_run:
        print("\n🔍 DRY RUN - No changes made to database")
    else:
        print("\n💾 Changes committed to database")
    
    return stats


def main():
    db = DatabaseManager()
    
    try:
        print("\n🔍 Running in DRY RUN mode first...")
        backfill_injury_weeks(db, dry_run=True)
        
        response = input("\n❓ Apply changes to database? (yes/no): ").strip().lower()
        
        if response == 'yes':
            print("\n🚀 Applying changes...")
            backfill_injury_weeks(db, dry_run=False)
            print("\n✅ BACKFILL COMPLETE!")
        else:
            print("\n❌ Cancelled - No changes made")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()