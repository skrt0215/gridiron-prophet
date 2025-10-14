import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from datetime import datetime

class WeeklyAccuracyCalculator:
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def store_prediction(self, season, week, game_id, home_team, away_team, 
                        predicted_home_score, predicted_away_score, 
                        predicted_winner, model_spread, confidence, 
                        recommended_bet=None, edge=None):
        
        try:
            self.db.execute_query("""
                INSERT INTO predictions 
                (season, week, game_id, home_team, away_team, 
                 predicted_home_score, predicted_away_score, predicted_winner,
                 model_spread, confidence, recommended_bet, edge, prediction_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                predicted_home_score = VALUES(predicted_home_score),
                predicted_away_score = VALUES(predicted_away_score),
                predicted_winner = VALUES(predicted_winner),
                model_spread = VALUES(model_spread),
                confidence = VALUES(confidence),
                recommended_bet = VALUES(recommended_bet),
                edge = VALUES(edge),
                prediction_date = NOW()
            """, (season, week, game_id, home_team, away_team,
                  predicted_home_score, predicted_away_score, predicted_winner,
                  model_spread, confidence, recommended_bet, edge))
            
            return True
        except Exception as e:
            print(f"Error storing prediction: {e}")
            return False
    
    def calculate_week_accuracy(self, season, week):
        
        print(f"\n{'=' * 70}")
        print(f"CALCULATING ACCURACY FOR {season} WEEK {week}")
        print(f"{'=' * 70}\n")
        
        games = self.db.execute_query("""
            SELECT 
                g.game_id,
                g.home_score,
                g.away_score,
                CASE WHEN g.home_score > g.away_score THEN 'HOME' ELSE 'AWAY' END as actual_winner,
                ABS(g.home_score - g.away_score) as actual_margin,
                ht.abbreviation as home_team,
                at.abbreviation as away_team
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE g.season = %s 
            AND g.week = %s
            AND g.game_status = 'Final'
            ORDER BY g.game_id
        """, (season, week))
        
        if not games:
            print(f"❌ No completed games found for Week {week}")
            return None
        
        print(f"Found {len(games)} completed games\n")
        
        predictions = self.db.execute_query("""
            SELECT 
                p.game_id,
                p.home_team,
                p.away_team,
                p.predicted_home_score,
                p.predicted_away_score,
                p.predicted_winner,
                p.model_spread,
                p.confidence,
                p.recommended_bet,
                p.edge
            FROM predictions p
            WHERE p.season = %s AND p.week = %s
        """, (season, week))
        
        if not predictions:
            print("❌ No predictions found for this week!")
            print("💡 Make sure to run predictions BEFORE games are played")
            return None
        
        pred_dict = {p['game_id']: p for p in predictions}
        
        total_games = 0
        correct_winners = 0
        correct_spreads_3pt = 0
        correct_spreads_7pt = 0
        total_point_diff = 0
        
        high_conf_correct = 0
        high_conf_total = 0
        
        print(f"{'Game':<30} {'Predicted':<12} {'Actual':<12} {'Result':<10} {'Spread Acc'}")
        print("-" * 80)
        
        for game in games:
            game_id = game['game_id']
            
            if game_id not in pred_dict:
                print(f"⚠️  No prediction for {game['away_team']} @ {game['home_team']}")
                continue
            
            pred = pred_dict[game_id]
            total_games += 1
            
            correct_winner = (pred['predicted_winner'] == game['actual_winner'])
            if correct_winner:
                correct_winners += 1
            
            predicted_margin = abs(pred['predicted_home_score'] - pred['predicted_away_score'])
            actual_margin = game['actual_margin']
            margin_diff = abs(predicted_margin - actual_margin)
            
            total_point_diff += margin_diff
            
            if margin_diff <= 3:
                correct_spreads_3pt += 1
            if margin_diff <= 7:
                correct_spreads_7pt += 1
            
            if pred['confidence'] == 'HIGH':
                high_conf_total += 1
                if correct_winner:
                    high_conf_correct += 1
            
            away = game['away_team']
            home = game['home_team']
            pred_score = f"{pred['predicted_away_score']:.0f}-{pred['predicted_home_score']:.0f}"
            actual_score = f"{game['away_score']}-{game['home_score']}"
            result = "✓" if correct_winner else "✗"
            spread_acc = f"±{margin_diff:.1f} pts"
            
            print(f"{away} @ {home:<25} {pred_score:<12} {actual_score:<12} {result:<10} {spread_acc}")
        
        winner_accuracy = (correct_winners / total_games * 100) if total_games > 0 else 0
        spread_3pt_accuracy = (correct_spreads_3pt / total_games * 100) if total_games > 0 else 0
        spread_7pt_accuracy = (correct_spreads_7pt / total_games * 100) if total_games > 0 else 0
        avg_margin_error = total_point_diff / total_games if total_games > 0 else 0
        high_conf_accuracy = (high_conf_correct / high_conf_total * 100) if high_conf_total > 0 else None
        
        print("\n" + "=" * 70)
        print(f"WEEK {week} ACCURACY RESULTS")
        print("=" * 70)
        print(f"Winner Prediction:     {correct_winners}/{total_games} ({winner_accuracy:.1f}%)")
        print(f"Spread within 3 pts:   {correct_spreads_3pt}/{total_games} ({spread_3pt_accuracy:.1f}%)")
        print(f"Spread within 7 pts:   {correct_spreads_7pt}/{total_games} ({spread_7pt_accuracy:.1f}%)")
        print(f"Avg Margin Error:      {avg_margin_error:.1f} points")
        
        if high_conf_total > 0:
            print(f"HIGH Confidence Bets:  {high_conf_correct}/{high_conf_total} ({high_conf_accuracy:.1f}%)")
        
        print("=" * 70)
        
        try:
            self.db.execute_query("""
                INSERT INTO weekly_accuracy 
                (season, week, total_predictions, correct_predictions, accuracy_pct,
                 spread_3pt_accuracy, spread_7pt_accuracy, avg_margin_error,
                 high_conf_total, high_conf_correct, calculated_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                correct_predictions = VALUES(correct_predictions),
                accuracy_pct = VALUES(accuracy_pct),
                spread_3pt_accuracy = VALUES(spread_3pt_accuracy),
                spread_7pt_accuracy = VALUES(spread_7pt_accuracy),
                avg_margin_error = VALUES(avg_margin_error),
                high_conf_total = VALUES(high_conf_total),
                high_conf_correct = VALUES(high_conf_correct),
                calculated_date = NOW()
            """, (season, week, total_games, correct_winners, winner_accuracy,
                  spread_3pt_accuracy, spread_7pt_accuracy, avg_margin_error,
                  high_conf_total, high_conf_correct))
            
            print(f"\n✓ Accuracy data saved to database")
            
            return {
                'season': season,
                'week': week,
                'total': total_games,
                'correct_winners': correct_winners,
                'winner_accuracy': winner_accuracy,
                'spread_3pt_accuracy': spread_3pt_accuracy,
                'spread_7pt_accuracy': spread_7pt_accuracy,
                'avg_margin_error': avg_margin_error,
                'high_conf_accuracy': high_conf_accuracy
            }
            
        except Exception as e:
            print(f"\n❌ Error storing accuracy: {e}")
            return None
    
    def get_season_accuracy_trend(self, season, detailed=False):
        
        query = """
            SELECT 
                week,
                total_predictions,
                correct_predictions,
                accuracy_pct,
                spread_3pt_accuracy,
                spread_7pt_accuracy,
                avg_margin_error,
                high_conf_total,
                high_conf_correct,
                calculated_date
            FROM weekly_accuracy
            WHERE season = %s
            ORDER BY week
        """
        
        results = self.db.execute_query(query, (season,))
        
        if not results:
            print(f"\n❌ No accuracy data found for {season}")
            return None
        
        print(f"\n{'=' * 80}")
        print(f"{season} SEASON ACCURACY TREND")
        print(f"{'=' * 80}\n")
        
        if detailed:
            print(f"{'Week':<6} {'Record':<10} {'Winner%':<10} {'±3pts%':<10} {'±7pts%':<10} {'AvgErr':<8}")
            print("-" * 80)
            
            for r in results:
                record = f"{r['correct_predictions']}-{r['total_predictions'] - r['correct_predictions']}"
                winner_pct = f"{r['accuracy_pct']:.1f}%"
                spread_3 = f"{r.get('spread_3pt_accuracy', 0):.1f}%" if r.get('spread_3pt_accuracy') else "N/A"
                spread_7 = f"{r.get('spread_7pt_accuracy', 0):.1f}%" if r.get('spread_7pt_accuracy') else "N/A"
                avg_err = f"{r.get('avg_margin_error', 0):.1f}" if r.get('avg_margin_error') else "N/A"
                
                print(f"{r['week']:<6} {record:<10} {winner_pct:<10} {spread_3:<10} {spread_7:<10} {avg_err:<8}")
        else:
            print(f"{'Week':<8} {'Record':<15} {'Accuracy':<12} {'Date'}")
            print("-" * 70)
            
            for r in results:
                record = f"{r['correct_predictions']}-{r['total_predictions'] - r['correct_predictions']}"
                date = r['calculated_date'].strftime('%Y-%m-%d')
                print(f"{r['week']:<8} {record:<15} {r['accuracy_pct']:.1f}%{' ' * 7} {date}")
        
        total_correct = sum(r['correct_predictions'] for r in results)
        total_games = sum(r['total_predictions'] for r in results)
        overall = (total_correct / total_games * 100) if total_games > 0 else 0
        
        print("-" * 80)
        print(f"{'TOTAL':<8} {total_correct}-{total_games - total_correct:<14} {overall:.1f}%")
        print("=" * 80)
        
        return results

if __name__ == "__main__":
    calculator = WeeklyAccuracyCalculator()
    
    import argparse
    parser = argparse.ArgumentParser(description='Calculate weekly prediction accuracy')
    parser.add_argument('--season', type=int, default=2025)
    parser.add_argument('--week', type=int)
    parser.add_argument('--view', action='store_true')
    parser.add_argument('--detailed', action='store_true')
    
    args = parser.parse_args()
    
    if args.view:
        calculator.get_season_accuracy_trend(args.season, detailed=args.detailed)
    elif args.week:
        calculator.calculate_week_accuracy(season=args.season, week=args.week)
        print("\nTo view season trend:")
        print(f"  python src/analysis/calculate_weekly_accuracy.py --season {args.season} --view --detailed")
    else:
        print("Error: Either --week or --view is required")
        parser.print_help()