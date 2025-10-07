import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from betting.roi_tracker import ROITracker
from data_collection.fetch_games import NFLGameFetcher
import pandas as pd

class ResultsUpdater:
    """Update prediction results with actual game outcomes"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.roi_tracker = ROITracker()
        self.game_fetcher = NFLGameFetcher()
    
    def fetch_completed_games(self, season, week):
        """Fetch completed games for a specific week"""
        print(f"Fetching completed games for {season} Week {week}...")
        
        games = self.game_fetcher.fetch_scoreboard(season=season, week=week)
        
        if games:
            # Save to database (will update existing games)
            self.game_fetcher.save_games_to_db(games)
            print(f"✓ Updated {len(games)} games")
        
        return games
    
    def update_pending_predictions(self):
        """Update all predictions that don't have results yet"""
        
        print("\nChecking for predictions with completed games...")
        
        # Get predictions without results
        pending = self.db.execute_query("""
            SELECT 
                pl.prediction_id,
                pl.season,
                pl.week,
                pl.home_team_id,
                pl.away_team_id,
                pl.predicted_spread,
                pl.vegas_spread,
                pl.edge,
                pl.recommendation,
                pl.bet_amount,
                g.home_score,
                g.away_score,
                g.game_status,
                ht.name as home_team,
                at.name as away_team
            FROM prediction_log pl
            LEFT JOIN games g ON (
                g.home_team_id = pl.home_team_id 
                AND g.away_team_id = pl.away_team_id
                AND g.season = pl.season
                AND g.week = pl.week
            )
            LEFT JOIN teams ht ON pl.home_team_id = ht.team_id
            LEFT JOIN teams at ON pl.away_team_id = at.team_id
            WHERE pl.bet_result IS NULL
            AND g.game_status = 'Final'
            AND g.home_score IS NOT NULL
            ORDER BY pl.season, pl.week
        """)
        
        if not pending:
            print("No completed games to update.")
            return 0
        
        print(f"Found {len(pending)} predictions to update\n")
        
        updated_count = 0
        
        for pred in pending:
            home_score = pred['home_score']
            away_score = pred['away_score']
            
            # Update prediction with results
            result, profit = self.roi_tracker.update_prediction_result(
                pred['prediction_id'],
                home_score,
                away_score
            )
            
            # Display result
            actual_spread = home_score - away_score
            result_emoji = "✅" if result == "WIN" else "❌" if result == "LOSS" else "➖"
            
            print(f"{result_emoji} Week {pred['week']}: {pred['away_team']} @ {pred['home_team']}")
            print(f"   Score: {away_score}-{home_score} (Spread: {actual_spread:+.1f})")
            print(f"   Vegas: {pred['vegas_spread']:+.1f} | Model: {pred['predicted_spread']:+.1f}")
            print(f"   Result: {result} | P/L: ${profit:+.2f}")
            print()
            
            updated_count += 1
        
        return updated_count
    
    def show_summary(self, season=None):
        """Display performance summary"""
        
        print("\n" + "=" * 70)
        print("UPDATED PERFORMANCE SUMMARY")
        print("=" * 70)
        
        self.roi_tracker.print_performance_summary(season)

def main():
    updater = ResultsUpdater()
    
    print("=" * 70)
    print("GRIDIRON PROPHET - RESULTS UPDATER")
    print("=" * 70)
    
    # Option 1: Auto-update all pending predictions
    print("\n1. Update all pending predictions")
    print("2. Fetch specific week and update")
    
    choice = input("\nChoice (1 or 2): ").strip()
    
    if choice == "2":
        season = int(input("Season: "))
        week = int(input("Week: "))
        
        # Fetch games for that week
        updater.fetch_completed_games(season, week)
    
    # Update predictions
    updated = updater.update_pending_predictions()
    
    if updated > 0:
        # Show updated summary
        season = int(input("\nShow summary for season (e.g., 2025): "))
        updater.show_summary(season)
    
    print("\n" + "=" * 70)
    print(f"✓ Updated {updated} predictions")
    print("=" * 70)

if __name__ == "__main__":
    main()