import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from analysis.defensive_rankings import DefensiveRankings
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import pickle
import warnings
warnings.filterwarnings('ignore')

class SpreadPredictor:
    """Predicts point differential (spread) for NFL games"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.defensive_ranker = DefensiveRankings()
        self.model = None
        self.feature_columns = []
    
    def get_team_recent_performance(self, team_id, season, through_week, last_n_games=5):
        """Get team's recent performance (last N games)"""
        query = """
            SELECT 
                AVG(CASE 
                    WHEN g.home_team_id = %s THEN g.home_score - g.away_score
                    ELSE g.away_score - g.home_score
                END) as avg_point_diff,
                AVG(CASE 
                    WHEN g.home_team_id = %s THEN g.home_score
                    ELSE g.away_score
                END) as avg_points_scored,
                AVG(CASE 
                    WHEN g.home_team_id = %s THEN g.away_score
                    ELSE g.home_score
                END) as avg_points_allowed,
                COUNT(*) as games_played,
                SUM(CASE 
                    WHEN (g.home_team_id = %s AND g.home_score > g.away_score) 
                    OR (g.away_team_id = %s AND g.away_score > g.home_score)
                    THEN 1 ELSE 0
                END) as wins
            FROM games g
            WHERE (g.home_team_id = %s OR g.away_team_id = %s)
            AND g.season = %s
            AND g.week < %s
            AND g.game_status = 'Final'
            ORDER BY g.week DESC
            LIMIT %s
        """
        result = self.db.execute_query(query, (
            team_id, team_id, team_id, team_id, team_id, 
            team_id, team_id, season, through_week, last_n_games
        ))
        
        if result and result[0]['games_played']:
            return result[0]
        return {
            'avg_point_diff': 0, 'avg_points_scored': 0, 
            'avg_points_allowed': 0, 'games_played': 0, 'wins': 0
        }
    
    def get_team_offensive_stats(self, team_id, season, through_week):
        """Get offensive statistics"""
        query = """
            SELECT 
                AVG(pgs.pass_yards) as avg_pass_yards,
                AVG(pgs.pass_touchdowns) as avg_pass_tds,
                AVG(pgs.rush_yards) as avg_rush_yards,
                AVG(pgs.rush_touchdowns) as avg_rush_tds,
                AVG(pgs.receiving_yards) as avg_rec_yards
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id
            WHERE pgs.team_id = %s
            AND g.season = %s
            AND g.week < %s
            AND g.game_status = 'Final'
        """
        result = self.db.execute_query(query, (team_id, season, through_week))
        return result[0] if result else {
            'avg_pass_yards': 0, 'avg_pass_tds': 0,
            'avg_rush_yards': 0, 'avg_rush_tds': 0,
            'avg_rec_yards': 0
        }
    
    def build_features_for_prediction(self, seasons):
        """Build feature set for spread prediction"""
        print("Building features for spread prediction...")
        
        games_query = """
            SELECT 
                g.game_id, g.season, g.week,
                g.home_team_id, g.away_team_id,
                g.home_score, g.away_score,
                (g.home_score - g.away_score) as point_differential,
                ht.abbreviation as home_abbr,
                at.abbreviation as away_abbr
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE g.season IN ({})
            AND g.game_status = 'Final'
            AND g.home_score IS NOT NULL
            AND g.week > 3
            ORDER BY g.season, g.week
        """.format(','.join(['%s'] * len(seasons)))
        
        games = self.db.execute_query(games_query, tuple(seasons))
        
        features_list = []
        
        for idx, game in enumerate(games):
            if idx % 50 == 0:
                print(f"  Processing game {idx + 1}/{len(games)}...")
            
            season = game['season']
            week = game['week']
            home_id = game['home_team_id']
            away_id = game['away_team_id']
            
            # Recent performance (last 5 games)
            home_recent = self.get_team_recent_performance(home_id, season, week, 5)
            away_recent = self.get_team_recent_performance(away_id, season, week, 5)
            
            # Season-to-date stats
            home_offense = self.get_team_offensive_stats(home_id, season, week)
            away_offense = self.get_team_offensive_stats(away_id, season, week)
            
            # Defensive rankings
            def_rankings = self.defensive_ranker.get_all_defensive_rankings(season, week - 1)
            home_def = def_rankings[def_rankings['team_id'] == home_id]
            away_def = def_rankings[def_rankings['team_id'] == away_id]
            
            feature_dict = {
                'game_id': game['game_id'],
                'season': season,
                'week': week,
                
                # Home team recent performance
                'home_recent_point_diff': home_recent['avg_point_diff'] or 0,
                'home_recent_pts_scored': home_recent['avg_points_scored'] or 0,
                'home_recent_pts_allowed': home_recent['avg_points_allowed'] or 0,
                'home_recent_win_pct': (home_recent['wins'] or 0) / max(home_recent['games_played'] or 1, 1),
                
                # Away team recent performance
                'away_recent_point_diff': away_recent['avg_point_diff'] or 0,
                'away_recent_pts_scored': away_recent['avg_points_scored'] or 0,
                'away_recent_pts_allowed': away_recent['avg_points_allowed'] or 0,
                'away_recent_win_pct': (away_recent['wins'] or 0) / max(away_recent['games_played'] or 1, 1),
                
                # Offensive stats
                'home_pass_yards': home_offense['avg_pass_yards'] or 0,
                'home_rush_yards': home_offense['avg_rush_yards'] or 0,
                'away_pass_yards': away_offense['avg_pass_yards'] or 0,
                'away_rush_yards': away_offense['avg_rush_yards'] or 0,
                
                # Defensive rankings
                'home_def_rank': home_def.iloc[0]['overall_defense_rank'] if len(home_def) > 0 else 16,
                'away_def_rank': away_def.iloc[0]['overall_defense_rank'] if len(away_def) > 0 else 16,
                
                # Matchup advantages
                'offense_advantage': (home_recent['avg_points_scored'] or 0) - (away_recent['avg_points_allowed'] or 0),
                'defense_advantage': (away_recent['avg_points_scored'] or 0) - (home_recent['avg_points_allowed'] or 0),
                
                # Target (point differential)
                'point_differential': game['point_differential']
            }
            
            features_list.append(feature_dict)
        
        return pd.DataFrame(features_list)
    
    def train_model(self, seasons, save_model=True):
        """Train spread prediction model"""
        print("=" * 70)
        print("TRAINING SPREAD PREDICTION MODEL")
        print("=" * 70)
        
        # Build features
        features_df = self.build_features_for_prediction(seasons)
        
        print(f"\nTotal games: {len(features_df)}")
        
        # Define features
        self.feature_columns = [col for col in features_df.columns 
                               if col not in ['game_id', 'season', 'week', 'point_differential']]
        
        X = features_df[self.feature_columns].fillna(0)
        y = features_df['point_differential']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        print(f"Training set: {len(X_train)} games")
        print(f"Test set: {len(X_test)} games")
        
        # Train Gradient Boosting Regressor
        print("\nTraining Gradient Boosting model...")
        self.model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        
        # Predictions
        y_pred = self.model.predict(X_test)
        
        # Evaluate
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        print("\n" + "=" * 70)
        print("MODEL PERFORMANCE")
        print("=" * 70)
        print(f"\nMean Absolute Error: {mae:.2f} points")
        print(f"Root Mean Squared Error: {rmse:.2f} points")
        print(f"R² Score: {r2:.3f}")
        
        # Analysis
        print("\nPrediction Analysis:")
        errors = np.abs(y_test - y_pred)
        print(f"  Within 3 points: {(errors <= 3).sum() / len(errors):.1%}")
        print(f"  Within 7 points: {(errors <= 7).sum() / len(errors):.1%}")
        print(f"  Within 10 points: {(errors <= 10).sum() / len(errors):.1%}")
        
        # Feature importance
        print("\nTop 10 Most Important Features:")
        importances = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False).head(10)
        
        for _, row in importances.iterrows():
            print(f"  {row['feature']:35s}: {row['importance']:.4f}")
        
        # Sample predictions
        print("\nSample Predictions vs Actual:")
        sample_df = pd.DataFrame({
            'Predicted': y_pred[:10],
            'Actual': y_test.values[:10],
            'Error': y_pred[:10] - y_test.values[:10]
        })
        print(sample_df.to_string(index=False))
        
        # Save model
        if save_model:
            model_path = 'src/models/spread_model.pkl'
            with open(model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'feature_columns': self.feature_columns
                }, f)
            print(f"\n✓ Model saved to {model_path}")
        
        return mae, rmse

def main():
    predictor = SpreadPredictor()
    
    # Train on 2022-2023
    seasons = [2022, 2023]
    mae, rmse = predictor.train_model(seasons)
    
    print(f"\n{'=' * 70}")
    print(f"✓ Spread prediction model trained!")
    print(f"  Average error: {mae:.2f} points")
    print(f"{'=' * 70}")

if __name__ == "__main__":
    main()