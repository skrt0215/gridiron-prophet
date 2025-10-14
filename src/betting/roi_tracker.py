import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
import pandas as pd
from datetime import datetime

class ROITracker:
    """Track betting performance and calculate ROI"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.standard_bet = 100
    
    def log_prediction(self, prediction_data):
        """
        Log a prediction to the database
        
        prediction_data = {
            'season': int,
            'week': int,
            'home_team_id': int,
            'away_team_id': int,
            'predicted_spread': float,
            'vegas_spread': float,
            'edge': float,
            'confidence_level': str,
            'recommendation': str,
            'game_date': date
        }
        """
        query = """
            INSERT INTO prediction_log 
            (season, week, home_team_id, away_team_id, predicted_spread, 
             vegas_spread, edge, confidence_level, recommendation, 
             bet_amount, game_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        bet_multiplier = {
            'HIGH': 2.0,
            'MEDIUM': 1.0,
            'LOW': 0.5
        }
        bet_amount = self.standard_bet * bet_multiplier.get(prediction_data['confidence_level'], 1.0)
        
        return self.db.execute_insert(query, (
            prediction_data['season'],
            prediction_data['week'],
            prediction_data['home_team_id'],
            prediction_data['away_team_id'],
            prediction_data['predicted_spread'],
            prediction_data['vegas_spread'],
            prediction_data['edge'],
            prediction_data['confidence_level'],
            prediction_data['recommendation'],
            bet_amount,
            prediction_data['game_date']
        ))
    
    def update_prediction_result(self, prediction_id, home_score, away_score):
        """Update prediction with actual game result and calculate profit/loss"""
        pred = self.db.execute_query("""
            SELECT * FROM prediction_log WHERE prediction_id = %s
        """, (prediction_id,))[0]
        
        actual_spread = home_score - away_score
        vegas_spread = pred['vegas_spread']
        bet_amount = pred['bet_amount']
        recommendation = pred['recommendation']

        if 'HOME' in recommendation:
            bet_result = 'WIN' if actual_spread > vegas_spread else 'LOSS'
            if abs(actual_spread - vegas_spread) < 0.5:
                bet_result = 'PUSH'
        else:  
            bet_result = 'WIN' if actual_spread < vegas_spread else 'LOSS'
            if abs(actual_spread - vegas_spread) < 0.5:
                bet_result = 'PUSH'
        
        if bet_result == 'WIN':
            profit_loss = bet_amount * 0.909
        elif bet_result == 'PUSH':
            profit_loss = 0
        else:
            profit_loss = -bet_amount
        
        self.db.execute_update("""
            UPDATE prediction_log
            SET actual_home_score = %s,
                actual_away_score = %s,
                actual_spread = %s,
                bet_result = %s,
                profit_loss = %s
            WHERE prediction_id = %s
        """, (home_score, away_score, actual_spread, bet_result, profit_loss, prediction_id))
        
        self.update_roi_summary(pred['season'], pred['week'])
        
        return bet_result, profit_loss
    
    def update_roi_summary(self, season, week):
        """Calculate and update ROI summary for a season/week"""
        
        stats = self.db.execute_query("""
            SELECT 
                COUNT(*) as total_bets,
                SUM(CASE WHEN bet_result = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN bet_result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN bet_result = 'PUSH' THEN 1 ELSE 0 END) as pushes,
                SUM(bet_amount) as total_wagered,
                SUM(profit_loss) as total_profit_loss,
                AVG(edge) as avg_edge
            FROM prediction_log
            WHERE season = %s
            AND (week = %s OR %s IS NULL)
            AND bet_result IS NOT NULL
        """, (season, week, week))
        
        if stats and stats[0]['total_bets'] > 0:
            s = stats[0]
            roi = (s['total_profit_loss'] / s['total_wagered'] * 100) if s['total_wagered'] > 0 else 0
            win_rate = (s['wins'] / (s['wins'] + s['losses']) * 100) if (s['wins'] + s['losses']) > 0 else 0
            
            self.db.execute_query("""
                INSERT INTO roi_summary 
                (season, week, total_bets, winning_bets, losing_bets, push_bets,
                 total_wagered, total_profit_loss, roi_percentage, win_rate, avg_edge)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                total_bets = VALUES(total_bets),
                winning_bets = VALUES(winning_bets),
                losing_bets = VALUES(losing_bets),
                push_bets = VALUES(push_bets),
                total_wagered = VALUES(total_wagered),
                total_profit_loss = VALUES(total_profit_loss),
                roi_percentage = VALUES(roi_percentage),
                win_rate = VALUES(win_rate),
                avg_edge = VALUES(avg_edge)
            """, (season, week, s['total_bets'], s['wins'], s['losses'], 
                  s['pushes'], s['total_wagered'], s['total_profit_loss'], 
                  roi, win_rate, s['avg_edge']))
    
    def get_performance_report(self, season=None, week=None):
        """Generate performance report"""
        
        where_clause = []
        params = []
        
        if season:
            where_clause.append("season = %s")
            params.append(season)
        if week:
            where_clause.append("week = %s")
            params.append(week)
        
        where_str = "WHERE " + " AND ".join(where_clause) if where_clause else ""
        
        query = f"""
            SELECT * FROM roi_summary
            {where_str}
            ORDER BY season DESC, week DESC
        """
        
        results = self.db.execute_query(query, tuple(params))
        
        return pd.DataFrame(results)
    
    def print_performance_summary(self, season=None):
        """Print detailed performance summary"""
        
        print("=" * 70)
        print("BETTING PERFORMANCE SUMMARY")
        print("=" * 70)
        
        report = self.get_performance_report(season)
        
        if report.empty:
            print("\nNo betting history found.")
            return
        
        total_bets = report['total_bets'].sum()
        total_wins = report['winning_bets'].sum()
        total_losses = report['losing_bets'].sum()
        total_pushes = report['push_bets'].sum()
        total_wagered = report['total_wagered'].sum()
        total_profit = report['total_profit_loss'].sum()
        
        overall_roi = (total_profit / total_wagered * 100) if total_wagered > 0 else 0
        overall_win_rate = (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) > 0 else 0
        
        print(f"\nOverall Performance:")
        print(f"  Total Bets: {total_bets}")
        print(f"  Record: {total_wins}-{total_losses}-{total_pushes}")
        print(f"  Win Rate: {overall_win_rate:.1f}%")
        print(f"  Total Wagered: ${total_wagered:,.2f}")
        print(f"  Total Profit/Loss: ${total_profit:,.2f}")
        print(f"  ROI: {overall_roi:+.2f}%")
        
        break_even_rate = 52.4
        print(f"\n  Break-even Win Rate: {break_even_rate}%")
        if overall_win_rate > break_even_rate:
            print(f"  ✓ PROFITABLE! ({overall_win_rate - break_even_rate:.1f}% above break-even)")
        else:
            print(f"  ✗ Need {break_even_rate - overall_win_rate:.1f}% improvement to be profitable")
        
        print(f"\nWeekly Breakdown:")
        print(f"{'Week':<6} {'Bets':<6} {'Record':<12} {'Win%':<8} {'Profit/Loss':<12} {'ROI':<8}")
        print("-" * 70)
        
        for _, row in report.iterrows():
            week_str = f"Week {row['week']}" if row['week'] else "Season"
            record = f"{row['winning_bets']}-{row['losing_bets']}-{row['push_bets']}"
            profit_str = f"${row['total_profit_loss']:+,.2f}"
            roi_str = f"{row['roi_percentage']:+.1f}%"
            
            print(f"{week_str:<6} {row['total_bets']:<6} {record:<12} "
                  f"{row['win_rate']:.1f}%    {profit_str:<12} {roi_str:<8}")

def main():
    tracker = ROITracker()
    
    tracker.print_performance_summary(season=2025)

if __name__ == "__main__":
    main()