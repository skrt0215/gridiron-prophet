import sys
from pathlib import Path
from datetime import datetime
import subprocess
import time

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager
from src.utils.nfl_week import get_current_nfl_week as _calendar_week


def print_header(title: str):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_step(step_num: int, total_steps: int, description: str):
    print(f"\n📍 STEP {step_num}/{total_steps}: {description}")
    print("-" * 70)


def run_script(script_path: Path, description: str) -> bool:
    try:
        print(f"▶️  Running {script_path.name}...")
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=False,
            text=True,
            cwd=project_root
        )
        
        if result.returncode != 0:
            print(f"❌ Error in {description}")
            return False
        
        print(f"✅ {description} completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to run {description}: {e}")
        return False


def get_current_nfl_week() -> int:
    try:
        return _calendar_week()

    except Exception as e:
        print(f"⚠️  Error getting current week from date: {e}")
        db = DatabaseManager()
        try:
            result = db.execute_query("""
                SELECT MAX(week) AS max_week
                FROM games
                WHERE season = 2025
                AND home_score IS NOT NULL
            """)
            completed_week = result[0]['max_week'] if result and result[0]['max_week'] else 0
            return completed_week + 1
        except Exception as inner_e:
            print(f"⚠️  Could not derive week from database: {inner_e}")
            return 1


def verify_data_quality(db: DatabaseManager, current_week: int) -> dict:
    print("\n🔍 Verifying data quality...")
    
    games_result = db.execute_query("""
        SELECT COUNT(*) as count
        FROM games 
        WHERE season = 2025 
        AND week = %s
        AND home_score IS NOT NULL
    """, (current_week - 1,))
    games_count = games_result[0]['count'] if games_result else 0
    
    injuries_result = db.execute_query("""
        SELECT COUNT(*) as count
        FROM injuries 
        WHERE season = 2025 
        AND week = %s
    """, (current_week,))
    injuries_count = injuries_result[0]['count'] if injuries_result else 0
    
    upcoming_result = db.execute_query("""
        SELECT COUNT(*) as count
        FROM games 
        WHERE season = 2025 
        AND week = %s
    """, (current_week,))
    upcoming_count = upcoming_result[0]['count'] if upcoming_result else 0
    
    quality = {
        'games_completed': games_count,
        'injuries': injuries_count,
        'upcoming_games': upcoming_count,
        'week': current_week
    }
    
    print(f"  ✓ Completed games (Week {current_week - 1}): {games_count}")
    print(f"  ✓ Current injuries (Week {current_week}): {injuries_count}")
    print(f"  ✓ Upcoming games (Week {current_week}): {upcoming_count}")
    
    return quality


def main():
    start_time = datetime.now()
    
    print_header("🏈 GRIDIRON PROPHET - WEEKLY UPDATE 🏈")
    print(f"📅 Date: {start_time.strftime('%A, %B %d, %Y')}")
    print(f"⏰ Started: {start_time.strftime('%I:%M %p')}")
    
    current_week = get_current_nfl_week()
    print(f"📊 Current NFL Week: {current_week}")
    
    total_steps = 7
    completed_steps = 0
    failed_steps = []
    
    src_dir = project_root / 'src'
    data_collection_dir = src_dir / 'data_collection'
    models_dir = src_dir / 'models'
    
    print_step(1, total_steps, "Update Game Results")
    if run_script(data_collection_dir / 'fetch_games.py', "Game Results"):
        completed_steps += 1
    else:
        failed_steps.append("Game Results")
    
    time.sleep(2)
    
    print_step(2, total_steps, "Update Rosters (Trades & New Signings)")
    if run_script(data_collection_dir / 'smart_roster_updater.py', "Roster Updates"):
        completed_steps += 1
    else:
        print("⚠️  Roster update failed - continuing with existing rosters")
        failed_steps.append("Roster Updates (non-critical)")
    
    time.sleep(2)
    
    print_step(3, total_steps, "Calculate Previous Week Accuracy")
    previous_week = current_week - 1
    if previous_week > 0:
        print(f"\n📊 Calculating accuracy for completed Week {previous_week}...")
        try:
            result = subprocess.run(
                [sys.executable, str(src_dir / 'analysis' / 'calculate_weekly_accuracy.py'),
                 '--season', '2025', '--week', str(previous_week)],
                capture_output=False,
                text=True,
                cwd=project_root
            )
            
            if result.returncode == 0:
                print(f"✅ Week {previous_week} accuracy calculated and stored")
                completed_steps += 1
            else:
                print(f"⚠️  Could not calculate Week {previous_week} accuracy (games may not be complete)")
                failed_steps.append("Accuracy Calculation (non-critical)")
        except Exception as e:
            print(f"⚠️  Accuracy calculation skipped: {e}")
            failed_steps.append("Accuracy Calculation (non-critical)")
    else:
        print("\n⏭️  Skipping accuracy calculation (no previous week)")
        completed_steps += 1
    
    time.sleep(2)
    
    print_step(4, total_steps, "Update Injuries (ESPN Scraper)")
    if run_script(data_collection_dir / 'smart_injury_updater.py', "Injury Data"):
        completed_steps += 1
    else:
        failed_steps.append("Injury Data")
    
    time.sleep(2)
    
    print_step(5, total_steps, "Fetch Betting Lines (DraftKings)")
    if run_script(data_collection_dir / 'fetch_betting_lines.py', "Betting Lines"):
        completed_steps += 1
    else:
        print("⚠️  Betting lines failed - continuing without them")
        failed_steps.append("Betting Lines (non-critical)")
    
    time.sleep(2)
    
    print_step(6, total_steps, "Verify Data Quality")
    db = DatabaseManager()
    try:
        quality = verify_data_quality(db, current_week)
        
        if quality['injuries'] > 0 and quality['upcoming_games'] > 0:
            print("✅ Data quality check passed")
            completed_steps += 1
        else:
            print("⚠️  Warning: Data may be incomplete")
            if quality['injuries'] == 0:
                print("    - No injury data found")
            if quality['upcoming_games'] == 0:
                print("    - No upcoming games found")
            failed_steps.append("Data Quality")
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        failed_steps.append("Data Quality")
    
    time.sleep(2)
    
    print_step(7, total_steps, "Generate Predictions (Master Betting Predictor)")
    if run_script(models_dir / 'master_betting_predictor.py', "Predictions"):
        completed_steps += 1
    else:
        failed_steps.append("Predictions")
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print_header("📊 WORKFLOW SUMMARY")
    print(f"⏰ Completed: {end_time.strftime('%I:%M %p')}")
    print(f"⏱️  Duration: {duration.total_seconds() / 60:.1f} minutes")
    print(f"✅ Successful Steps: {completed_steps}/{total_steps}")
    
    if failed_steps:
        print(f"\n⚠️  Issues: {', '.join(failed_steps)}")
        if 'Predictions' in ' '.join(failed_steps):
            print("\n❌ WORKFLOW FAILED - Predictions not generated")
        else:
            print("\n⚠️  WORKFLOW COMPLETED WITH WARNINGS")
    else:
        print("\n🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
    
    print("\n📋 NEXT STEPS:")
    print("  1. Launch Streamlit dashboard:")
    print("     streamlit run streamlit_app.py")
    print("  2. Review predictions in the dashboard")
    print("  3. Check injury impacts for key matchups")
    print(f"  4. Look for betting opportunities with ≥5pt edge")
    
    print("\n💡 OPTIONAL:")
    print("  - Track ROI after games complete:")
    print("    python src/betting/roi_tracker.py")
    print("  - View season accuracy trend:")
    print("    python src/analysis/calculate_weekly_accuracy.py --season 2025 --view --detailed")
    
    print("\n" + "="*70)
    print("✨ Weekly Update Complete! Good luck this week! ✨")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()