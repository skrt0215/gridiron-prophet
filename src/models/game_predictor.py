import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import numpy as np

class NFLGamePredictor:
    """Predicts NFL game winners using machine learning"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.model = None
        self.feature_columns = []
    
    def fetch_training_data(self, seasons):
        """Fetch game data and calculate features"""
        print("Fetching game data from database...")
        
        query = """
            SELECT 
                g.game_id,
                g.season,
                g.week,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
                ht.name as home_team_name,
                at.name as away_team_name
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE g.season IN ({})
            AND g.game_status = 'Final'
            AND g.home_score IS NOT NULL
            AND g.away_score IS NOT NULL
            ORDER BY g.season, g.week, g.game_date
        """.format(','.join(['%s'] * len(seasons)))
        
        games = self.db.execute_query(query, tuple(seasons))
        df = pd.DataFrame(games)
        
        print(f"Found {len(df)} completed games")
        
        return df
    
    def calculate_team_stats(self, df):
        """Calculate rolling team statistics"""
        print("Calculating team statistics...")
        
        team_stats = {}
        
        for team_id in df['home_team_id'].unique():
            team_stats[team_id] = {
                'wins': 0,
                'losses': 0,
                'points_scored': [],
                'points_allowed': [],
                'games_played': 0
            }
        
        # Add features for each game
        features = []
        
        for idx, game in df.iterrows():
            home_id = game['home_team_id']
            away_id = game['away_team_id']
            
            # Get current team stats (before this game)
            home_stats = team_stats[home_id]
            away_stats = team_stats[away_id]
            
            # Calculate features
            feature_dict = {
                'game_id': game['game_id'],
                'season': game['season'],
                'week': game['week'],
                'home_team_id': home_id,
                'away_team_id': away_id,
                
                # Home team features
                'home_wins': home_stats['wins'],
                'home_losses': home_stats['losses'],
                'home_win_pct': home_stats['wins'] / max(home_stats['games_played'], 1),
                'home_avg_points_scored': np.mean(home_stats['points_scored']) if home_stats['points_scored'] else 0,
                'home_avg_points_allowed': np.mean(home_stats['points_allowed']) if home_stats['points_allowed'] else 0,
                
                # Away team features
                'away_wins': away_stats['wins'],
                'away_losses': away_stats['losses'],
                'away_win_pct': away_stats['wins'] / max(away_stats['games_played'], 1),
                'away_avg_points_scored': np.mean(away_stats['points_scored']) if away_stats['points_scored'] else 0,
                'away_avg_points_allowed': np.mean(away_stats['points_allowed']) if away_stats['points_allowed'] else 0,
                
                # Target variable (1 = home win, 0 = away win)
                'home_win': 1 if game['home_score'] > game['away_score'] else 0,
                
                # Actual scores (for analysis)
                'home_score': game['home_score'],
                'away_score': game['away_score']
            }
            
            features.append(feature_dict)
            
            # Update team stats after this game
            home_score = game['home_score']
            away_score = game['away_score']
            
            team_stats[home_id]['games_played'] += 1
            team_stats[home_id]['points_scored'].append(home_score)
            team_stats[home_id]['points_allowed'].append(away_score)
            
            team_stats[away_id]['games_played'] += 1
            team_stats[away_id]['points_scored'].append(away_score)
            team_stats[away_id]['points_allowed'].append(home_score)
            
            if home_score > away_score:
                team_stats[home_id]['wins'] += 1
                team_stats[away_id]['losses'] += 1
            else:
                team_stats[away_id]['wins'] += 1
                team_stats[home_id]['losses'] += 1
        
        return pd.DataFrame(features)
    
    def train_model(self, seasons):
        """Train the prediction model"""
        print("=" * 70)
        print("TRAINING NFL GAME PREDICTION MODEL")
        print("=" * 70)
        
        # Fetch and prepare data
        games_df = self.fetch_training_data(seasons)
        features_df = self.calculate_team_stats(games_df)
        
        # Remove early season games where teams have no history
        features_df = features_df[features_df['week'] > 1].copy()
        
        print(f"\nUsing {len(features_df)} games for training")
        
        # Define feature columns
        self.feature_columns = [
            'home_wins', 'home_losses', 'home_win_pct',
            'home_avg_points_scored', 'home_avg_points_allowed',
            'away_wins', 'away_losses', 'away_win_pct',
            'away_avg_points_scored', 'away_avg_points_allowed'
        ]
        
        X = features_df[self.feature_columns]
        y = features_df['home_win']
        
        # Split data: train on earlier games, test on later games
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        print(f"Training set: {len(X_train)} games")
        print(f"Test set: {len(X_test)} games")
        
        # Train Random Forest model
        print("\nTraining Random Forest model...")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        
        # Make predictions
        y_pred = self.model.predict(X_test)
        
        # Evaluate
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
        
        # Feature importance
        print("\nFeature Importance:")
        importances = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for _, row in importances.iterrows():
            print(f"  {row['feature']:30s}: {row['importance']:.4f}")
        
        # Home field advantage analysis
        home_wins = y_test.sum()
        total_games = len(y_test)
        print(f"\nHome Field Advantage in Test Set:")
        print(f"  Home team wins: {home_wins}/{total_games} ({home_wins/total_games:.1%})")
        
        return accuracy

def main():
    predictor = NFLGamePredictor()
    
    # Train on 2022-2023 seasons
    seasons = [2022, 2023]
    accuracy = predictor.train_model(seasons)
    
    print(f"\n{'=' * 70}")
    print(f"Model trained successfully with {accuracy:.2%} accuracy!")
    print(f"{'=' * 70}")

if __name__ == "__main__":
    main()