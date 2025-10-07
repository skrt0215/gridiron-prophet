import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from models.spread_predictor import SpreadPredictor
from analysis.defensive_rankings import DefensiveRankings
from betting.roi_tracker import ROITracker
import requests
import pandas as pd
from dotenv import load_dotenv
import pickle

load_dotenv('config/.env')

class OddsComparator:
    """Compare model predictions against live Vegas odds to find betting edge"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.api_key = os.getenv('ODDS_API_KEY')
        self.base_url = "https://api.the-odds-api.com/v4/sports"
        
        # Load trained model
        with open('src/models/spread_model.pkl', 'rb') as f:
            model_data = pickle.load(f)
            self.model = model_data['model']
            self.feature_columns = model_data['feature_columns']
        
        self.predictor = SpreadPredictor()
        self.defensive_ranker = DefensiveRankings()
        self.roi_tracker = ROITracker()
    
    def fetch_current_odds(self):
        """Fetch current NFL odds from The Odds API"""
        
        if not self.api_key:
            print("ERROR: ODDS_API_KEY not found in .env file")
            return None
        
        url = f"{self.base_url}/americanfootball_nfl/odds"
        
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': 'spreads,totals',
            'oddsFormat': 'american'
        }
        
        print("Fetching current NFL odds from The Odds API...")
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            print(f"✓ Found {len(data)} upcoming games")
            print(f"  Remaining API requests: {response.headers.get('x-requests-remaining', 'Unknown')}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds: {e}")
            return None
    
    def parse_odds_data(self, odds_data):
        """Parse odds data into structured format"""
        games = []
        
        for event in odds_data:
            home_team = event['home_team']
            away_team = event['away_team']
            commence_time = event['commence_time']
            
            # Get spread from bookmakers
            spreads = []
            totals = []
            
            for bookmaker in event.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'spreads':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home_team:
                                spreads.append(outcome['point'])
                    
                    if market['key'] == 'totals':
                        for outcome in market['outcomes']:
                            totals.append(outcome['point'])
            
            if spreads:
                avg_spread = sum(spreads) / len(spreads)
                avg_total = sum(totals) / len(totals) if totals else None
                
                games.append({
                    'home_team': home_team,
                    'away_team': away_team,
                    'commence_time': commence_time,
                    'vegas_spread': avg_spread,
                    'vegas_total': avg_total
                })
        
        return games
    
    def generate_model_predictions(self, games_list, season=2025, week=6):
        """Generate predictions for upcoming games"""
        predictions = []
        
        for game in games_list:
            # Map team names to database IDs
            home_team = self.db.execute_query(
                "SELECT team_id, name FROM teams WHERE name LIKE %s LIMIT 1",
                (f"%{game['home_team'].split()[-1]}%",)
            )
            away_team = self.db.execute_query(
                "SELECT team_id, name FROM teams WHERE name LIKE %s LIMIT 1",
                (f"%{game['away_team'].split()[-1]}%",)
            )
            
            if not home_team or not away_team:
                print(f"Warning: Could not find teams for {game['away_team']} @ {game['home_team']}")
                continue
            
            home_id = home_team[0]['team_id']
            away_id = away_team[0]['team_id']
            
            # Build features for this game
            home_recent = self.predictor.get_team_recent_performance(home_id, season, week, 5)
            away_recent = self.predictor.get_team_recent_performance(away_id, season, week, 5)
            
            home_offense = self.predictor.get_team_offensive_stats(home_id, season, week)
            away_offense = self.predictor.get_team_offensive_stats(away_id, season, week)
            
            # Try to get defensive rankings, fall back to defaults if not available
            try:
                def_rankings = self.defensive_ranker.get_all_defensive_rankings(season, week - 1)
                home_def = def_rankings[def_rankings['team_id'] == home_id]
                away_def = def_rankings[def_rankings['team_id'] == away_id]
                
                home_def_rank = home_def.iloc[0]['overall_defense_rank'] if len(home_def) > 0 else 16
                away_def_rank = away_def.iloc[0]['overall_defense_rank'] if len(away_def) > 0 else 16
            except Exception as e:
                print(f"  Using default defensive rankings (not enough 2025 data)")
                home_def_rank = 16
                away_def_rank = 16
            
            feature_dict = {
                'home_recent_point_diff': home_recent['avg_point_diff'] or 0,
                'home_recent_pts_scored': home_recent['avg_points_scored'] or 0,
                'home_recent_pts_allowed': home_recent['avg_points_allowed'] or 0,
                'home_recent_win_pct': (home_recent['wins'] or 0) / max(home_recent['games_played'] or 1, 1),
                
                'away_recent_point_diff': away_recent['avg_point_diff'] or 0,
                'away_recent_pts_scored': away_recent['avg_points_scored'] or 0,
                'away_recent_pts_allowed': away_recent['avg_points_allowed'] or 0,
                'away_recent_win_pct': (away_recent['wins'] or 0) / max(away_recent['games_played'] or 1, 1),
                
                'home_pass_yards': home_offense['avg_pass_yards'] or 0,
                'home_rush_yards': home_offense['avg_rush_yards'] or 0,
                'away_pass_yards': away_offense['avg_pass_yards'] or 0,
                'away_rush_yards': away_offense['avg_rush_yards'] or 0,
                
                'home_def_rank': home_def_rank,
                'away_def_rank': away_def_rank,
                
                'offense_advantage': (home_recent['avg_points_scored'] or 0) - (away_recent['avg_points_allowed'] or 0),
                'defense_advantage': (away_recent['avg_points_scored'] or 0) - (home_recent['avg_points_allowed'] or 0),
            }
            
            # Ensure all features exist
            features_df = pd.DataFrame([feature_dict])[self.feature_columns].fillna(0)
            
            # Predict spread
            predicted_spread = self.model.predict(features_df)[0]
            
            pred_dict = {
                'home_team': home_team[0]['name'],
                'away_team': away_team[0]['name'],
                'home_team_id': home_id,
                'away_team_id': away_id,
                'predicted_spread': predicted_spread,
                'vegas_spread': game['vegas_spread'],
                'edge': predicted_spread - game['vegas_spread'],
                'vegas_total': game['vegas_total'],
                'commence_time': game['commence_time']
            }
            
            # Add confidence score
            pred_dict['confidence'] = self.calculate_confidence(pred_dict)
            
            predictions.append(pred_dict)
        
        return predictions
    
    def calculate_confidence(self, prediction):
        """
        Calculate confidence level for a prediction
        Returns: 'HIGH', 'MEDIUM', or 'LOW'
        """
        edge = abs(prediction['edge'])
        
        # Confidence factors:
        if edge >= 7:
            edge_score = 3
        elif edge >= 5:
            edge_score = 2
        else:
            edge_score = 1
        
        confidence_score = edge_score
        
        if confidence_score >= 3:
            return 'HIGH'
        elif confidence_score >= 2:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def find_betting_opportunities(self, predictions, min_edge=3.0):
        """Find games where model disagrees significantly with Vegas"""
        
        print("\n" + "=" * 70)
        print("BETTING OPPORTUNITIES - MODEL vs VEGAS")
        print("=" * 70)
        
        opportunities = [p for p in predictions if abs(p['edge']) >= min_edge]
        
        if not opportunities:
            print(f"\nNo strong edges found (minimum edge: {min_edge} points)")
            print("\nAll Predictions:")
        else:
            print(f"\n✓ Found {len(opportunities)} games with {min_edge}+ point edge:\n")
        
        # Show all predictions
        for pred in sorted(predictions, key=lambda x: abs(x['edge']), reverse=True):
            edge = pred['edge']
            edge_str = f"+{edge:.1f}" if edge > 0 else f"{edge:.1f}"
            
            marker = "🔥" if abs(edge) >= min_edge else "  "
            confidence_emoji = {'HIGH': '🔥', 'MEDIUM': '⚡', 'LOW': '💡'}
            conf_marker = confidence_emoji.get(pred['confidence'], '')
            
            print(f"{marker} {pred['away_team']:25s} @ {pred['home_team']:25s} {conf_marker}")
            print(f"   Vegas Spread: {pred['vegas_spread']:+.1f}")
            print(f"   Model Spread: {pred['predicted_spread']:+.1f}")
            print(f"   Edge: {edge_str} points")
            print(f"   Confidence: {pred['confidence']}")
            
            if abs(edge) >= min_edge:
                if edge > 0:
                    print(f"   → RECOMMENDATION: Bet {pred['home_team']} to cover")
                else:
                    print(f"   → RECOMMENDATION: Bet {pred['away_team']} to cover")
            print()
        
        return opportunities

def main():
    comparator = OddsComparator()
    
    print("=" * 70)
    print("GRIDIRON PROPHET - LIVE ODDS COMPARISON")
    print("=" * 70)
    
    # Fetch current odds
    odds_data = comparator.fetch_current_odds()
    
    if not odds_data:
        print("\nCould not fetch odds. Check your API key.")
        return
    
    # Parse odds
    games = comparator.parse_odds_data(odds_data)
    
    if not games:
        print("\nNo games with available odds found.")
        return
    
    # Generate predictions (adjust season/week as needed)
    season = 2025
    week = 6
    
    print(f"\nGenerating predictions for {len(games)} games...")
    predictions = comparator.generate_model_predictions(games, season=season, week=week)
    
    # Find opportunities
    opportunities = comparator.find_betting_opportunities(predictions, min_edge=3.0)
    
    # Log predictions to database
    print("\nLogging predictions to database...")
    for pred in predictions:
        try:
            from datetime import datetime
            game_date = datetime.fromisoformat(pred['commence_time'].replace('Z', '+00:00')).date()
            
            recommendation = ""
            if abs(pred['edge']) >= 3.0:
                if pred['edge'] > 0:
                    recommendation = f"Bet {pred['home_team']} to cover"
                else:
                    recommendation = f"Bet {pred['away_team']} to cover"
            
            comparator.roi_tracker.log_prediction({
                'season': season,
                'week': week,
                'home_team_id': pred['home_team_id'],
                'away_team_id': pred['away_team_id'],
                'predicted_spread': pred['predicted_spread'],
                'vegas_spread': pred['vegas_spread'],
                'edge': pred['edge'],
                'confidence_level': pred['confidence'],
                'recommendation': recommendation,
                'game_date': game_date
            })
        except Exception as e:
            print(f"  Error logging prediction: {e}")
    
    print("✓ Predictions logged")
    
    print("\n" + "=" * 70)
    if opportunities:
        print(f"✓ Found {len(opportunities)} strong betting opportunities!")
        print("\nTo track results, run after games complete:")
        print("  python3 src/betting/update_results.py")
    else:
        print("No strong edges this week. The market is efficient.")
    print("=" * 70)

if __name__ == "__main__":
    main()