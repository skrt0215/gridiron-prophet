import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pickle

class NFLGamePredictor:
    """
    Machine Learning model for predicting NFL game outcomes
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.model = None
        self.feature_columns = None
    
    def fetch_training_data(self, seasons, max_week_2025=None):
        """
        Fetch historical game data for training
        
        Args:
            seasons: List of seasons (e.g., [2022, 2023, 2024, 2025])
            max_week_2025: Only include 2025 games up to this week
        """
        print("Fetching game data from database...")
        where_clauses = [f"g.season IN ({','.join(['%s'] * len(seasons))})"]
        params = list(seasons)
        if max_week_2025 and 2025 in seasons:
            where_clauses.append("(g.season < 2025 OR g.week <= %s)")
            params.append(max_week_2025)
        where_clauses.append("g.game_status = 'Final'")
        query = f"""
            SELECT 
                g.game_id,
                g.season,
                g.week,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
                ht.abbreviation as home_team,
                at.abbreviation as away_team,
                CASE WHEN g.home_score > g.away_score THEN 1 ELSE 0 END as home_win
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY g.season, g.week
        """
        
        games = self.db.execute_query(query, tuple(params))
        
        print(f"Found {len(games)} completed games")
        
        return pd.DataFrame(games)
    
    def calculate_team_stats(self, games_df):
        """
        Calculate cumulative team statistics for each game
        """
        print("Calculating team statistics...")
        features_list = []
        for season in games_df['season'].unique():
            season_games = games_df[games_df['season'] == season].copy()
            team_stats = {}
            for idx, game in season_games.iterrows():
                home_team = game['home_team']
                away_team = game['away_team']
                if home_team not in team_stats:
                    team_stats[home_team] = {
                        'wins': 0, 'losses': 0,
                        'points_scored': [], 'points_allowed': []
                    }
                if away_team not in team_stats:
                    team_stats[away_team] = {
                        'wins': 0, 'losses': 0,
                        'points_scored': [], 'points_allowed': []
                    }

                home_stats = team_stats[home_team]
                away_stats = team_stats[away_team]
                home_games = home_stats['wins'] + home_stats['losses']
                away_games = away_stats['wins'] + away_stats['losses']
                
                features = {
                    'game_id': game['game_id'],
                    'season': game['season'],
                    'week': game['week'],
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_wins': home_stats['wins'],
                    'home_losses': home_stats['losses'],
                    'home_win_pct': home_stats['wins'] / max(home_games, 1),
                    'home_avg_points_scored': np.mean(home_stats['points_scored']) if home_stats['points_scored'] else 0,
                    'home_avg_points_allowed': np.mean(home_stats['points_allowed']) if home_stats['points_allowed'] else 0,
                    'away_wins': away_stats['wins'],
                    'away_losses': away_stats['losses'],
                    'away_win_pct': away_stats['wins'] / max(away_games, 1),
                    'away_avg_points_scored': np.mean(away_stats['points_scored']) if away_stats['points_scored'] else 0,
                    'away_avg_points_allowed': np.mean(away_stats['points_allowed']) if away_stats['points_allowed'] else 0,
                    'home_win': game['home_win']
                }
                
                features_list.append(features)
                home_scored = game['home_score']
                away_scored = game['away_score']
                team_stats[home_team]['points_scored'].append(home_scored)
                team_stats[home_team]['points_allowed'].append(away_scored)
                if game['home_win']:
                    team_stats[home_team]['wins'] += 1
                else:
                    team_stats[home_team]['losses'] += 1
                team_stats[away_team]['points_scored'].append(away_scored)
                team_stats[away_team]['points_allowed'].append(home_scored)
                if not game['home_win']:
                    team_stats[away_team]['wins'] += 1
                else:
                    team_stats[away_team]['losses'] += 1
        
        return pd.DataFrame(features_list)
    
    def train_model(self, seasons, max_week_2025=None):
        """
        Train the prediction model
        
        Args:
            seasons: List of seasons to train on (e.g., [2022, 2023, 2024, 2025])
            max_week_2025: For 2025, only include games up to this week (for weekly updates)
        """
        print("=" * 70)
        print("TRAINING NFL GAME PREDICTION MODEL")
        print("=" * 70)
        
        if max_week_2025:
            print(f"Including 2025 games through Week {max_week_2025}")
        games_df = self.fetch_training_data(seasons, max_week_2025)
        features_df = self.calculate_team_stats(games_df)
        features_df = features_df[features_df['week'] > 1].copy()
        print(f"\nUsing {len(features_df)} games for training")
        self.feature_columns = [
            'home_wins', 'home_losses', 'home_win_pct',
            'home_avg_points_scored', 'home_avg_points_allowed',
            'away_wins', 'away_losses', 'away_win_pct',
            'away_avg_points_scored', 'away_avg_points_allowed'
        ]
        
        X = features_df[self.feature_columns]
        y = features_df['home_win']
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        print(f"Training set: {len(X_train)} games")
        print(f"Test set: {len(X_test)} games")
        print("\nTraining Random Forest model...")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        print("\n" + "=" * 70)
        print("MODEL PERFORMANCE")
        print("=" * 70)
        print(f"\nAccuracy: {accuracy:.2%}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['Away Win', 'Home Win']))
        print("\nConfusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(f"  Predicted Away Win | Predicted Home Win")
        print(f"Actual Away Win:  {cm[0][0]:4d}           {cm[0][1]:4d}")
        print(f"Actual Home Win:  {cm[1][0]:4d}           {cm[1][1]:4d}")
        print("\nFeature Importance:")
        importances = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        for _, row in importances.iterrows():
            print(f"  {row['feature']:30s}: {row['importance']:.4f}")
        home_wins = y_test.sum()
        total_games = len(y_test)
        print(f"\nHome Field Advantage in Test Set:")
        print(f"  Home team wins: {home_wins}/{total_games} ({home_wins/total_games:.1%})")
        return accuracy
    
    def save_model(self, filepath='src/models/spread_model.pkl'):
        """Save the trained model to disk"""
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
        model_data = {
            'model': self.model,
            'feature_columns': self.feature_columns
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        print(f"\n✓ Model saved to {filepath}")
    
    def load_model(self, filepath='src/models/spread_model.pkl'):
        """Load a trained model from disk"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        self.model = model_data['model']
        self.feature_columns = model_data['feature_columns']
        print(f"✓ Model loaded from {filepath}")
    
    def predict_game(self, home_team_stats, away_team_stats):
        """
        Predict outcome of a single game
        
        Args:
            home_team_stats: Dict with keys matching feature_columns (home_*)
            away_team_stats: Dict with keys matching feature_columns (away_*)
        
        Returns:
            Dict with prediction and probability
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train_model() first.")
        features = pd.DataFrame([{
            'home_wins': home_team_stats.get('wins', 0),
            'home_losses': home_team_stats.get('losses', 0),
            'home_win_pct': home_team_stats.get('win_pct', 0),
            'home_avg_points_scored': home_team_stats.get('avg_points_scored', 0),
            'home_avg_points_allowed': home_team_stats.get('avg_points_allowed', 0),
            'away_wins': away_team_stats.get('wins', 0),
            'away_losses': away_team_stats.get('losses', 0),
            'away_win_pct': away_team_stats.get('win_pct', 0),
            'away_avg_points_scored': away_team_stats.get('avg_points_scored', 0),
            'away_avg_points_allowed': away_team_stats.get('avg_points_allowed', 0)
        }])

        prediction = self.model.predict(features)[0]
        probability = self.model.predict_proba(features)[0]
        
        return {
            'home_win_predicted': bool(prediction),
            'home_win_probability': probability[1],
            'away_win_probability': probability[0]
        }

if __name__ == "__main__":
    predictor = NFLGamePredictor()
    accuracy = predictor.train_model([2022, 2023, 2024])
    predictor.save_model()
    print("\n" + "=" * 70)
    print("Training complete! Model ready for predictions.")
    print("=" * 70)