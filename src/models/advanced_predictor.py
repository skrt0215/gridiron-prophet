import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from analysis.defensive_rankings import DefensiveRankings
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

class AdvancedNFLPredictor:
    """Advanced NFL game predictor with player stats, snap counts, and matchup analysis"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.defensive_ranker = DefensiveRankings()
        self.model = None
        self.feature_columns = []
    
    def get_team_qb_performance(self, team_id, season, through_week):
        """Get QB performance for a team up to a certain week"""
        query = """
            SELECT 
                AVG(pgs.pass_yards) as avg_pass_yards,
                AVG(pgs.pass_touchdowns) as avg_pass_tds,
                AVG(pgs.interceptions) as avg_interceptions,
                AVG(pgs.pass_completions * 100.0 / NULLIF(pgs.pass_attempts, 0)) as completion_pct,
                SUM(pgs.pass_yards) as total_pass_yards
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id
            WHERE pgs.team_id = %s
            AND g.season = %s
            AND g.week < %s
            AND pgs.pass_attempts > 5
            AND g.game_status = 'Final'
        """
        result = self.db.execute_query(query, (team_id, season, through_week))
        return result[0] if result else {
            'avg_pass_yards': 0, 'avg_pass_tds': 0, 
            'avg_interceptions': 0, 'completion_pct': 0,
            'total_pass_yards': 0
        }
    
    def get_team_rushing_performance(self, team_id, season, through_week):
        """Get rushing performance for a team"""
        query = """
            SELECT 
                AVG(pgs.rush_yards) as avg_rush_yards,
                AVG(pgs.rush_touchdowns) as avg_rush_tds,
                SUM(pgs.rush_yards) as total_rush_yards
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id
            WHERE pgs.team_id = %s
            AND g.season = %s
            AND g.week < %s
            AND pgs.rush_attempts > 0
            AND g.game_status = 'Final'
        """
        result = self.db.execute_query(query, (team_id, season, through_week))
        return result[0] if result else {
            'avg_rush_yards': 0, 'avg_rush_tds': 0, 'total_rush_yards': 0
        }
    
    def get_key_player_snap_counts(self, team_id, season, week):
        """Get average snap counts for key positions"""
        query = """
            SELECT 
                position,
                AVG(snap_percentage) as avg_snap_pct,
                MAX(snap_percentage) as max_snap_pct
            FROM depth_charts
            WHERE team_id = %s
            AND season = %s
            AND week < %s
            AND snap_percentage IS NOT NULL
            GROUP BY position
        """
        results = self.db.execute_query(query, (team_id, season, week))
        snap_dict = {}
        for row in results:
            pos = row['position']
            snap_dict[f'{pos}_avg_snap'] = row['avg_snap_pct'] or 0
            snap_dict[f'{pos}_max_snap'] = row['max_snap_pct'] or 0
        return snap_dict
    
    def build_features(self, seasons):
        """Build comprehensive feature set"""
        print("Building advanced feature set...")
        games_query = """
            SELECT 
                g.game_id, g.season, g.week,
                g.home_team_id, g.away_team_id,
                g.home_score, g.away_score,
                ht.abbreviation as home_abbr,
                at.abbreviation as away_abbr
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE g.season IN ({})
            AND g.game_status = 'Final'
            AND g.home_score IS NOT NULL
            AND g.week > 2
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
            def_rankings = self.defensive_ranker.get_all_defensive_rankings(season, week - 1)
            home_def = def_rankings[def_rankings['team_id'] == home_id]
            away_def = def_rankings[def_rankings['team_id'] == away_id]
            home_qb = self.get_team_qb_performance(home_id, season, week)
            away_qb = self.get_team_qb_performance(away_id, season, week)
            home_rush = self.get_team_rushing_performance(home_id, season, week)
            away_rush = self.get_team_rushing_performance(away_id, season, week)
            home_snaps = self.get_key_player_snap_counts(home_id, season, week)
            away_snaps = self.get_key_player_snap_counts(away_id, season, week)
            feature_dict = {
                'game_id': game['game_id'],
                'season': season,
                'week': week,
                'home_avg_pass_yards': home_qb.get('avg_pass_yards', 0) or 0,
                'home_avg_pass_tds': home_qb.get('avg_pass_tds', 0) or 0,
                'home_avg_interceptions': home_qb.get('avg_interceptions', 0) or 0,
                'home_completion_pct': home_qb.get('completion_pct', 0) or 0,
                'home_avg_rush_yards': home_rush.get('avg_rush_yards', 0) or 0,
                'home_avg_rush_tds': home_rush.get('avg_rush_tds', 0) or 0,
                'away_avg_pass_yards': away_qb.get('avg_pass_yards', 0) or 0,
                'away_avg_pass_tds': away_qb.get('avg_pass_tds', 0) or 0,
                'away_avg_interceptions': away_qb.get('avg_interceptions', 0) or 0,
                'away_completion_pct': away_qb.get('completion_pct', 0) or 0,
                'away_avg_rush_yards': away_rush.get('avg_rush_yards', 0) or 0,
                'away_avg_rush_tds': away_rush.get('avg_rush_tds', 0) or 0,
                'home_pass_def_rank': home_def.iloc[0]['pass_defense_rank'] if len(home_def) > 0 else 16,
                'home_run_def_rank': home_def.iloc[0]['run_defense_rank'] if len(home_def) > 0 else 16,
                'home_overall_def_rank': home_def.iloc[0]['overall_defense_rank'] if len(home_def) > 0 else 16,
                'away_pass_def_rank': away_def.iloc[0]['pass_defense_rank'] if len(away_def) > 0 else 16,
                'away_run_def_rank': away_def.iloc[0]['run_defense_rank'] if len(away_def) > 0 else 16,
                'away_overall_def_rank': away_def.iloc[0]['overall_defense_rank'] if len(away_def) > 0 else 16,
                'home_pass_vs_away_pass_def': (home_qb.get('avg_pass_yards', 0) or 0) - (away_def.iloc[0]['avg_pass_yards_per_game'] if len(away_def) > 0 else 250),
                'away_pass_vs_home_pass_def': (away_qb.get('avg_pass_yards', 0) or 0) - (home_def.iloc[0]['avg_pass_yards_per_game'] if len(home_def) > 0 else 250),
                'home_win': 1 if game['home_score'] > game['away_score'] else 0
            }
            
            for key in ['QB', 'RB', 'WR', 'TE']:
                feature_dict[f'home_{key}_snap'] = home_snaps.get(f'{key}_avg_snap', 0)
                feature_dict[f'away_{key}_snap'] = away_snaps.get(f'{key}_avg_snap', 0)
            
            features_list.append(feature_dict)
        
        return pd.DataFrame(features_list)
    
    def train_model(self, seasons):
        """Train advanced prediction model"""
        print("=" * 70)
        print("TRAINING ADVANCED NFL PREDICTION MODEL")
        print("=" * 70)
        features_df = self.build_features(seasons)
        
        print(f"\nTotal games for training: {len(features_df)}")
        self.feature_columns = [col for col in features_df.columns 
                               if col not in ['game_id', 'season', 'week', 'home_win']]
        
        X = features_df[self.feature_columns]
        y = features_df['home_win']
        X = X.fillna(0)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        print(f"Training set: {len(X_train)} games")
        print(f"Test set: {len(X_test)} games")
        print("\nTraining Gradient Boosting model...")
        self.model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print("\n" + "=" * 70)
        print("MODEL PERFORMANCE")
        print("=" * 70)
        print(f"\nAccuracy: {accuracy:.2%}")
        
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, 
                                   target_names=['Away Win', 'Home Win']))
        
        print("\nConfusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(f"                  Predicted Away | Predicted Home")
        print(f"Actual Away Win:  {cm[0][0]:4d}           {cm[0][1]:4d}")
        print(f"Actual Home Win:  {cm[1][0]:4d}           {cm[1][1]:4d}")
        print("\nTop 15 Most Important Features:")
        importances = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False).head(15)
        
        for _, row in importances.iterrows():
            print(f"  {row['feature']:40s}: {row['importance']:.4f}")
        
        return accuracy

def main():
    predictor = AdvancedNFLPredictor()
    seasons = [2022, 2023]
    accuracy = predictor.train_model(seasons)
    
    print(f"\n{'=' * 70}")
    print(f"✓ Advanced model trained with {accuracy:.2%} accuracy!")
    print(f"{'=' * 70}")

if __name__ == "__main__":
    main()