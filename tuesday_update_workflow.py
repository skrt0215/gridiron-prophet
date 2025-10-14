import sys
from pathlib import Path
from datetime import datetime
import subprocess
import time

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager


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
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"❌ Error in {description}:")
            print(result.stderr)
            return False
        
        print(f"✅ {description} completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to run {description}: {e}")
        return False


def get_current_nfl_week() -> int:
    db = DatabaseManager()
    try:
        result = db.fetch_one("""
            SELECT MAX(week) 
            FROM games 
            WHERE season = 2025 
            AND home_score IS NOT NULL
        """)
        
        completed_week = result[0] if result and result[0] else 0
        return completed_week + 1
        
    finally:
        db.close()


def verify_data_quality(db: DatabaseManager, current_week: int) -> dict:
    print("\n🔍 Verifying data quality...")
    
    games_count = db.fetch_one("""
        SELECT COUNT(*) 
        FROM games 
        WHERE season = 2025 
        AND week = ? 
        AND home_score IS NOT NULL
    """, (current_week - 1,))[0]
    
    injuries_count = db.fetch_one("""
        SELECT COUNT(*) 
        FROM injuries 
        WHERE season = 2025 
        AND week = ?
    """, (current_week,))[0]
    
    snap_counts = db.fetch_one("""
        SELECT COUNT(*) 
        FROM snap_counts 
        WHERE season = 2025 
        AND week = ?
    """, (current_week - 1,))[0]
    
    quality = {
        'games': games_count,
        'injuries': injuries_count,
        'snap_counts': snap_counts,
        'week': current_week
    }
    
    print(f"  ✓ Games from Week {current_week - 1}: {games_count}")
    print(f"  ✓ Injuries for Week {current_week}: {injuries_count}")
    print(f"  ✓ Snap counts from Week {current_week - 1}: {snap_counts}")
    
    return quality


def main():
    start_time = datetime.now()
    
    print_header("🏈 TUESDAY NFL UPDATE WORKFLOW 🏈")
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
    analysis_dir = src_dir / 'analysis'
    
    print_step(1, total_steps, "Fetch Latest Game Results")
    if run_script(data_collection_dir / 'fetch_games.py', "Game Results Fetch"):
        completed_steps += 1
    else:
        failed_steps.append("Game Results")
    
    time.sleep(2)
    
    print_step(2, total_steps, "Fetch Snap Counts")
    if run_script(data_collection_dir / 'fetch_snap_counts.py', "Snap Counts Fetch"):
        completed_steps += 1
    else:
        failed_steps.append("Snap Counts")
    
    time.sleep(2)
    
    print_step(3, total_steps, "Smart Injury Update (Week-Aware)")
    if run_script(data_collection_dir / 'smart_injury_updater.py', "Injury Update"):
        completed_steps += 1
    else:
        failed_steps.append("Injuries")
    
    time.sleep(2)
    
    print_step(4, total_steps, "Fetch Latest Betting Lines")
    if run_script(data_collection_dir / 'fetch_betting_lines.py', "Betting Lines Fetch"):
        completed_steps += 1
    else:
        failed_steps.append("Betting Lines")
    
    time.sleep(2)
    
    print_step(5, total_steps, "Verify Data Quality")
    db = DatabaseManager()
    try:
        quality = verify_data_quality(db, current_week)
        
        if quality['games'] > 0 and quality['injuries'] >= 0:
            print("✅ Data quality check passed")
            completed_steps += 1
        else:
            print("⚠️  Warning: Some data may be incomplete")
            failed_steps.append("Data Quality")
    finally:
        db.close()
    
    print_step(6, total_steps, "Retrain Enhanced Model")
    if run_script(models_dir / 'enhanced_model_with_injuries.py', "Model Training"):
        completed_steps += 1
    else:
        failed_steps.append("Model Training")
    
    time.sleep(2)
    
    print_step(7, total_steps, "Generate Week Predictions")
    if run_script(models_dir / 'master_betting_predictor.py', "Predictions Generation"):
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
        print(f"❌ Failed Steps: {', '.join(failed_steps)}")
        print("\n⚠️  WORKFLOW COMPLETED WITH ERRORS")
    else:
        print("\n🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
    
    print("\n📋 NEXT STEPS:")
    print("  1. Review predictions in reports/weekly_predictions.txt")
    print("  2. Check injury impact analysis")
    print("  3. Compare with Vegas lines using odds_comparator.py")
    print("  4. Track ROI with roi_tracker.py")
    
    print("\n" + "="*70)
    print("✨ Tuesday Update Complete! Good luck this week! ✨")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()