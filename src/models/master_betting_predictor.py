import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from analysis.injury_impact import InjuryImpactAnalyzer
from models.game_predictor import NFLGamePredictor
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('config/.env')

class MasterBettingPredictor:
    """
    Integrated prediction system combining:
    - Machine Learning (trained on 2022-2024 historical data)
    - Current team performance (2025 season stats)
    - Injury impact analysis (weighted by historical snap counts)
    - DraftKings betting lines
    - Historical player performance trends
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.injury_analyzer = InjuryImpactAnalyzer()
        self.ml_predictor = NFLGamePredictor()
        self.odds_api_key = os.getenv('ODDS_API_KEY')
        self.ml_trained = False
        
    def train_ml_model(self, max_week_2025=None):
        """
        Train ML model on historical data if not already trained
        
        Args:
            max_week_2025: If provided, includes 2025 games up to this week
        """
        if not self.ml_trained:
            if max_week_2025:
                print(f"\n🤖 Training ML Model on 2022-2024 + 2025 (through Week {max_week_2025})...")
                self.ml_predictor.train_model([2022, 2023, 2024, 2025], max_week_2025=max_week_2025)
            else:
                print("\n🤖 Training ML Model on Historical Data (2022-2024)...")
                self.ml_predictor.train_model([2022, 2023, 2024])
            self.ml_trained = True
            print("✓ ML Model Ready\n")
    
    def get_team_current_stats(self, team_abbr, season, through_week):
        """Get current season stats"""
        query = """
            SELECT 
                SUM(CASE 
                    WHEN (home_team_id = t.team_id AND home_score > away_score) 
                      OR (away_team_id = t.team_id AND away_score > home_score) 
                    THEN 1 ELSE 0 
                END) as wins,
                SUM(CASE 
                    WHEN (home_team_id = t.team_id AND home_score < away_score) 
                      OR (away_team_id = t.team_id AND away_score < home_score) 
                    THEN 1 ELSE 0 
                END) as losses,
                AVG(CASE WHEN home_team_id = t.team_id THEN home_score ELSE away_score END) as avg_points_scored,
                AVG(CASE WHEN home_team_id = t.team_id THEN away_score ELSE home_score END) as avg_points_allowed
            FROM teams t
            LEFT JOIN games g ON (g.home_team_id = t.team_id OR g.away_team_id = t.team_id)
                AND g.season = %s 
                AND g.week < %s
                AND g.game_status = 'Final'
            WHERE t.abbreviation = %s
            GROUP BY t.team_id
        """
        
        result = self.db.execute_query(query, (season, through_week, team_abbr))
        
        if result and result[0]['wins'] is not None:
            return result[0]
        
        return {'wins': 0, 'losses': 0, 'avg_points_scored': 0.0, 'avg_points_allowed': 0.0}
    
    def get_historical_performance(self, team_abbr, seasons=[2022, 2023, 2024]):
        """Get team's historical performance trends"""
        query = """
            SELECT 
                g.season,
                SUM(CASE 
                    WHEN (home_team_id = t.team_id AND home_score > away_score) 
                      OR (away_team_id = t.team_id AND away_score > home_score) 
                    THEN 1 ELSE 0 
                END) as wins,
                COUNT(*) as games,
                AVG(CASE WHEN home_team_id = t.team_id THEN home_score ELSE away_score END) as avg_scored,
                AVG(CASE WHEN home_team_id = t.team_id THEN away_score ELSE home_score END) as avg_allowed
            FROM teams t
            JOIN games g ON (g.home_team_id = t.team_id OR g.away_team_id = t.team_id)
            WHERE t.abbreviation = %s
            AND g.season IN ({})
            AND g.game_status = 'Final'
            GROUP BY g.season
            ORDER BY g.season
        """.format(','.join(['%s'] * len(seasons)))
        
        result = self.db.execute_query(query, (team_abbr, *seasons))
        
        if result:
            avg_win_pct = np.mean([r['wins'] / r['games'] for r in result])
            trend = 'improving' if len(result) > 1 and result[-1]['wins']/result[-1]['games'] > avg_win_pct else 'declining'
            return {
                'historical_win_pct': avg_win_pct,
                'trend': trend,
                'seasons_data': result
            }
        
        return {'historical_win_pct': 0.5, 'trend': 'neutral', 'seasons_data': []}
    
    def get_ml_prediction_for_game(self, home_team, away_team, season, week):
        """Get ML model's prediction for this matchup"""
        
        home_stats = self.get_team_current_stats(home_team, season, week)
        away_stats = self.get_team_current_stats(away_team, season, week)
        
        home_games = home_stats['wins'] + home_stats['losses']
        away_games = away_stats['wins'] + away_stats['losses']
        
        features = pd.DataFrame([{
            'home_wins': home_stats['wins'],
            'home_losses': home_stats['losses'],
            'home_win_pct': home_stats['wins'] / max(home_games, 1),
            'home_avg_points_scored': home_stats['avg_points_scored'],
            'home_avg_points_allowed': home_stats['avg_points_allowed'],
            'away_wins': away_stats['wins'],
            'away_losses': away_stats['losses'],
            'away_win_pct': away_stats['wins'] / max(away_games, 1),
            'away_avg_points_scored': away_stats['avg_points_scored'],
            'away_avg_points_allowed': away_stats['avg_points_allowed']
        }])
        
        home_win_prob = self.ml_predictor.model.predict_proba(features)[0][1]
        
        return home_win_prob
    
    def fetch_draftkings_lines(self):
        """Fetch current DraftKings lines"""
        if not self.odds_api_key:
            return None
        
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"
        params = {
            'apiKey': self.odds_api_key,
            'regions': 'us',
            'markets': 'spreads,totals',
            'bookmakers': 'draftkings',
            'oddsFormat': 'american'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except:
            return None
    
    def parse_odds_for_game(self, odds_data, home_team, away_team):
        """Extract DraftKings lines for specific game"""
        team_map = {
            'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens',
            'BUF': 'Buffalo Bills', 'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears',
            'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'DAL': 'Dallas Cowboys',
            'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers',
            'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars',
            'KC': 'Kansas City Chiefs', 'LV': 'Las Vegas Raiders', 'LAC': 'Los Angeles Chargers',
            'LA': 'Los Angeles Rams', 'MIA': 'Miami Dolphins', 'MIN': 'Minnesota Vikings',
            'NE': 'New England Patriots', 'NO': 'New Orleans Saints', 'NYG': 'New York Giants',
            'NYJ': 'New York Jets', 'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers',
            'SF': 'San Francisco 49ers', 'SEA': 'Seattle Seahawks', 'TB': 'Tampa Bay Buccaneers',
            'TEN': 'Tennessee Titans', 'WAS': 'Washington Commanders'
        }
        
        home_full = team_map.get(home_team)
        away_full = team_map.get(away_team)
        
        if not odds_data:
            return None
        
        for game in odds_data:
            if home_full in [game['home_team'], game['away_team']] and away_full in [game['home_team'], game['away_team']]:
                for bookmaker in game['bookmakers']:
                    if bookmaker['key'] == 'draftkings':
                        spread, total = None, None
                        for market in bookmaker['markets']:
                            if market['key'] == 'spreads':
                                for outcome in market['outcomes']:
                                    if outcome['name'] == home_full:
                                        spread = outcome['point']
                            elif market['key'] == 'totals':
                                total = market['outcomes'][0]['point']
                        return {'spread': spread, 'total': total}
        return None
    
    def calculate_comprehensive_prediction(self, home_team, away_team, season, week):
        """
        Master prediction combining all factors:
        1. ML Model (trained on 2022-2024)
        2. Current season performance
        3. Historical trends
        4. Injury impact (weighted by snap counts)
        5. Home field advantage
        
        Returns prediction with BOTH point margin and betting line format
        """
        
        home_current = self.get_team_current_stats(home_team, season, week)
        away_current = self.get_team_current_stats(away_team, season, week)
        
        home_historical = self.get_historical_performance(home_team)
        away_historical = self.get_historical_performance(away_team)
        
        ml_home_win_prob = self.get_ml_prediction_for_game(home_team, away_team, season, week)
        
        home_injury = self.injury_analyzer.get_team_injury_impact(home_team, season, week)
        away_injury = self.injury_analyzer.get_team_injury_impact(away_team, season, week)
        
        prediction_components = {}
        
        ml_spread_contribution = (ml_home_win_prob - 0.5) * 20
        prediction_components['ml_model'] = ml_spread_contribution

        home_games = int(home_current['wins']) + int(home_current['losses'])
        away_games = int(away_current['wins']) + int(away_current['losses'])
        current_record_diff = (int(home_current['wins'])/max(home_games, 1)) - (int(away_current['wins'])/max(away_games, 1))
        prediction_components['current_record'] = current_record_diff * 8

        prediction_components['historical_trend'] = (float(home_historical['historical_win_pct']) - float(away_historical['historical_win_pct'])) * 5

        prediction_components['offensive_power'] = (float(home_current['avg_points_scored']) - float(away_current['avg_points_scored'])) * 0.3

        prediction_components['defensive_strength'] = (float(away_current['avg_points_allowed']) - float(home_current['avg_points_allowed'])) * 0.3
 
        injury_diff = float(away_injury['total_impact']) - float(home_injury['total_impact'])
        prediction_components['injury_impact'] = injury_diff * 0.3
        
        prediction_components['home_field'] = 2.5
        
        predicted_margin = sum(prediction_components.values())
        
        model_betting_line = -predicted_margin
        
        confidence_score = 0
        if abs(ml_spread_contribution) > 5:
            confidence_score += 30
        if abs(prediction_components['current_record']) > 3:
            confidence_score += 25
        if abs(injury_diff) > 15:
            confidence_score += 20
        if abs(prediction_components['offensive_power']) > 3:
            confidence_score += 15
        if abs(prediction_components['defensive_strength']) > 3:
            confidence_score += 10
        
        if confidence_score >= 70:
            confidence = 'HIGH'
        elif confidence_score >= 45:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'home_record': f"{int(home_current['wins'])}-{int(home_current['losses'])}",
            'away_record': f"{int(away_current['wins'])}-{int(away_current['losses'])}",
            'predicted_margin': predicted_margin,
            'model_betting_line': model_betting_line,
            'ml_home_win_probability': ml_home_win_prob,
            'confidence': confidence,
            'confidence_score': confidence_score,
            'components': prediction_components,
            'injury_impact': {
                'home': float(home_injury['total_impact']),
                'away': float(away_injury['total_impact']),
                'critical_home': len(home_injury['critical_injuries']),
                'critical_away': len(away_injury['critical_injuries'])
            },
            'historical': {
                'home_trend': home_historical['trend'],
                'away_trend': away_historical['trend']
            }
        }
    
    def save_weekly_report(self, season, week, recommendations):
        """Save weekly analysis to a text file"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"reports/week{week}_{season}_predictions_{timestamp}.txt"
        
        os.makedirs('reports', exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"GRIDIRON PROPHET - WEEK {week} BETTING REPORT\n")
            f.write(f"Season {season} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("=" * 80 + "\n\n")
            
            if recommendations:
                f.write(f"🎯 TOP BETTING OPPORTUNITIES ({len(recommendations)} picks)\n")
                f.write("=" * 80 + "\n\n")
                
                for i, rec in enumerate(recommendations, 1):
                    f.write(f"{i}. {rec['game']}\n")
                    f.write(f"   BET: {rec['bet']}\n")
                    f.write(f"   Edge: {rec['edge']:+.1f} pts | Confidence: {rec['confidence']}\n")
                    f.write(f"   ML Probability: {rec['ml_prob']:.1%}\n\n")
            else:
                f.write("No strong betting opportunities found this week.\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("After games complete, update results with:\n")
            f.write("  python src/betting/roi_tracker.py\n")
            f.write("=" * 80 + "\n")
        
        print(f"\n💾 Report saved to: {filename}")
        return filename
    
    def analyze_week(self, season, week, store_predictions=True):
        
        print("=" * 80)
        print("🏈 GRIDIRON PROPHET - MASTER BETTING ANALYSIS")
        print(f"   Season {season} | Week {week} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 80)
        
        self.train_ml_model()
        
        if store_predictions:
            from analysis.calculate_weekly_accuracy import WeeklyAccuracyCalculator
            accuracy_calc = WeeklyAccuracyCalculator()
        
        query = """
            SELECT g.game_id, ht.abbreviation as home_team, at.abbreviation as away_team
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE g.season = %s AND g.week = %s
            ORDER BY g.game_date
        """
        
        games = self.db.execute_query(query, (season, week))
        
        if not games:
            print(f"\n⚠️  No games found for Week {week}")
            return
        
        print("\n📊 Fetching DraftKings lines...")
        odds_data = self.fetch_draftkings_lines()
        if odds_data:
            print(f"✓ Found lines for {len(odds_data)} games\n")
        else:
            print("⚠️  Could not fetch odds\n")
        
        recommendations = []
        
        for game in games:
            home = game['home_team']
            away = game['away_team']
            game_id = game['game_id']
            
            prediction = self.calculate_comprehensive_prediction(home, away, season, week)
            dk_lines = self.parse_odds_for_game(odds_data, home, away) if odds_data else None
            
            base_score = 24
            predicted_home_score = base_score + (prediction['predicted_margin'] / 2)
            predicted_away_score = base_score - (prediction['predicted_margin'] / 2)
            
            predicted_winner = 'HOME' if prediction['predicted_margin'] > 0 else 'AWAY'
            
            edge = None
            recommended_bet = None
            
            if dk_lines and dk_lines['spread'] is not None:
                dk_spread = dk_lines['spread']
                edge = prediction['model_betting_line'] - dk_spread
                
                if abs(edge) >= 3.0:
                    if edge < 0:
                        if dk_spread > 0:
                            recommended_bet = f"{home} +{dk_spread}"
                        elif dk_spread < 0:
                            recommended_bet = f"{home} {dk_spread}"
                        else:
                            recommended_bet = f"{home} PK"
                    else:
                        if dk_spread < 0:
                            recommended_bet = f"{away} +{abs(dk_spread)}"
                        elif dk_spread > 0:
                            recommended_bet = f"{away} {-dk_spread}"
                        else:
                            recommended_bet = f"{away} PK"
            
            if store_predictions:
                accuracy_calc.store_prediction(
                    season=season,
                    week=week,
                    game_id=game_id,
                    home_team=home,
                    away_team=away,
                    predicted_home_score=predicted_home_score,
                    predicted_away_score=predicted_away_score,
                    predicted_winner=predicted_winner,
                    model_spread=prediction['model_betting_line'],
                    confidence=prediction['confidence'],
                    recommended_bet=recommended_bet,
                    edge=edge
                )
            
            print("\n" + "=" * 80)
            print(f"📍 {away} @ {home}")
            print("=" * 80)
            print(f"Records: {away} ({prediction['away_record']}) @ {home} ({prediction['home_record']})")
            print(f"Historical Trends: {away} ({prediction['historical']['away_trend']}) | {home} ({prediction['historical']['home_trend']})")
            
            print("\n🎯 PREDICTION:")
            print(f"   Model Spread: {home} {prediction['model_betting_line']:+.1f}")
            print(f"   Predicted Score: {away} {predicted_away_score:.1f} - {home} {predicted_home_score:.1f}")
            print(f"   ML Win Probability: {home} {prediction['ml_home_win_probability']:.1%}")
            print(f"   Confidence: {prediction['confidence']} ({prediction['confidence_score']}/100)")
            
            print("\n📊 Breakdown:")
            for factor, value in prediction['components'].items():
                print(f"   {factor.replace('_', ' ').title():25}: {value:+6.2f}")
            
            print("\n🏥 Injury Impact:")
            print(f"   {home}: {prediction['injury_impact']['home']:.1f} ({prediction['injury_impact']['critical_home']} critical)")
            print(f"   {away}: {prediction['injury_impact']['away']:.1f} ({prediction['injury_impact']['critical_away']} critical)")
            
            if dk_lines and dk_lines['spread'] is not None:
                dk_spread = dk_lines['spread']
                print(f"\n💰 DraftKings Line: {home} {dk_spread:+.1f}")
                print(f"   EDGE: {edge:+.1f} points")
                
                if abs(edge) >= 3.0:
                    strength = "🔥 STRONG" if abs(edge) >= 5 else "⚡ MODERATE"
                    
                    print(f"\n{strength} BET RECOMMENDATION:")
                    print(f"   ► {recommended_bet}")
                    
                    recommendations.append({
                        'game': f"{away} @ {home}",
                        'bet': recommended_bet,
                        'edge': edge,
                        'confidence': prediction['confidence'],
                        'ml_prob': prediction['ml_home_win_probability']
                    })
                else:
                    print("\n   ⚠️  Edge too small - PASS")
            else:
                print("\n   ⚠️  No DraftKings line available")
        
        if recommendations:
            print("\n\n" + "=" * 80)
            print(f"🎯 WEEK {week} TOP BETTING OPPORTUNITIES")
            print("=" * 80 + "\n")
            
            sorted_recs = sorted(recommendations, key=lambda x: abs(x['edge']), reverse=True)
            
            for i, rec in enumerate(sorted_recs, 1):
                print(f"{i}. {rec['game']}")
                print(f"   💵 BET: {rec['bet']}")
                print(f"   📈 Edge: {rec['edge']:+.1f} pts | Confidence: {rec['confidence']}")
                print(f"   🤖 ML Probability: {rec['ml_prob']:.1%}\n")
        else:
            print("\n\n" + "=" * 80)
            print(f"⚠️  No strong betting opportunities found for Week {week}")
            print("=" * 80)
        
        self.save_weekly_report(season, week, recommendations)
        
        if store_predictions:
            print("\n💾 Predictions stored in database for accuracy tracking")
            print(f"   After games complete, run:")
            print(f"   python src/analysis/calculate_weekly_accuracy.py --season {season} --week {week}")

        print("\n💡 Analysis complete! Good luck! 🍀")
        print("=" * 80)

if __name__ == "__main__":
    predictor = MasterBettingPredictor()
    completed_week = 6
    if completed_week:
        print(f"📊 Using 2025 data through Week {completed_week} for training")
        predictor.train_ml_model(max_week_2025=completed_week)
    predictor.analyze_week(season=2025, week=7)