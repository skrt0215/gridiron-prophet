import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from models.game_predictor import NFLGamePredictor
from datetime import datetime

def weekly_model_update(season=2025, completed_week=None):
    """
    Retrain model after a week completes
    
    Args:
        season: Current season
        completed_week: Week that just finished (None = auto-detect)
    """
    db = DatabaseManager()
    
    print("=" * 70)
    print(f"WEEKLY MODEL UPDATE - {season}")
    print("=" * 70)
    
    if not completed_week:
        result = db.execute_query("""
            SELECT MAX(week) as last_week
            FROM games
            WHERE season = %s
            AND game_status = 'Final'
        """, (season,))
        completed_week = result[0]['last_week'] if result else 0
    
    print(f"\n✓ Training on all games through Week {completed_week}")
    
    completed_games = db.execute_query("""
        SELECT COUNT(*) as count
        FROM games
        WHERE season = %s
        AND week <= %s
        AND game_status = 'Final'
    """, (season, completed_week))
    
    print(f"✓ {completed_games[0]['count']} completed games in {season}")
    
    predictor = NFLGamePredictor()
    
    predictor.train_model(
        seasons=[2022, 2023, 2024, 2025],
        max_week=completed_week
    )
    
    print("\n" + "=" * 70)
    print(f"EVALUATING {season} ACCURACY (Weeks 1-{completed_week})")
    print("=" * 70)
    
    accuracy_check = db.execute_query("""
        SELECT 
            p.predicted_winner,
            CASE WHEN g.home_score > g.away_score THEN 'HOME' ELSE 'AWAY' END as actual_winner,
            p.confidence_level
        FROM predictions p
        JOIN games g ON p.game_id = g.game_id
        WHERE g.season = %s
        AND g.week <= %s
        AND g.game_status = 'Final'
    """, (season, completed_week))
    
    if accuracy_check:
        correct = sum(1 for p in accuracy_check if p['predicted_winner'] == p['actual_winner'])
        total = len(accuracy_check)
        accuracy = (correct / total) * 100
        
        print(f"\n{season} Season Accuracy: {correct}/{total} = {accuracy:.2f}%")
        
        for conf in ['HIGH', 'MEDIUM', 'LOW']:
            conf_preds = [p for p in accuracy_check if p['confidence_level'] == conf]
            if conf_preds:
                conf_correct = sum(1 for p in conf_preds if p['predicted_winner'] == p['actual_winner'])
                conf_total = len(conf_preds)
                conf_acc = (conf_correct / conf_total) * 100
                print(f"  {conf} confidence: {conf_correct}/{conf_total} = {conf_acc:.1f}%")
    
    print("\n" + "=" * 70)
    print(f"✓ Model updated with Week {completed_week} results!")
    print(f"✓ Ready to predict Week {completed_week + 1}")
    print("=" * 70)
    
    db.execute_insert("""
        INSERT INTO model_training_log 
        (training_date, seasons_included, latest_week, total_games, notes)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        datetime.now(),
        '2022-2024, 2025 W1-' + str(completed_week),
        completed_week,
        completed_games[0]['count'],
        f"Weekly update after Week {completed_week}"
    ))

if __name__ == "__main__":
    weekly_model_update(season=2025)