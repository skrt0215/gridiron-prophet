import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from datetime import datetime
from typing import Dict
import pickle

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager

POSITION_WEIGHTS = {
    'QB': 1.0,
    'RB': 0.7,
    'WR': 0.6,
    'TE': 0.5,
    'OL': 0.6,
    'DL': 0.6,
    'LB': 0.5,
    'DB': 0.4,
    'K': 0.2,
    'P': 0.1,
    'LS': 0.1
}

INJURY_STATUS_MULTIPLIERS = {
    'Out': 1.0,
    'IR': 1.0,
    'PUP': 0.9,
    'Questionable': 0.4
}


def calculate_injury_impact(db: DatabaseManager, team: str, week: int, season: int = 2025) -> Dict[str, float]:
    injuries = db.execute_query("""
        SELECT 
            ps.position,
            i.injury_status
        FROM injuries i
        JOIN players p ON i.player_id = p.player_id
        JOIN player_seasons ps ON i.player_id = ps.player_id AND i.season = ps.season
        JOIN teams t ON ps.team_id = t.team_id
        WHERE t.abbreviation = ?
        AND i.season = ?
        AND i.week = ?
    """, (team, season, week))
    
    if not injuries:
        return {
            'total_impact': 0.0,
            'qb_impact': 0.0,
            'skill_impact': 0.0,
            'defense_impact': 0.0,
            'injury_count': 0
        }
    
    total_impact = 0.0
    qb_impact = 0.0
    skill_impact = 0.0
    defense_impact = 0.0
    
    for injury in injuries:
        position = injury['position'] if isinstance(injury, dict) else injury[0]
        status = injury['injury_status'] if isinstance(injury, dict) else injury[1]
        
        pos_weight = POSITION_WEIGHTS.get(position, 0.3)
        status_mult = INJURY_STATUS_MULTIPLIERS.get(status, 0.5)
        snap_factor = 0.65
        
        impact = pos_weight * status_mult * snap_factor
        total_impact += impact
        
        if position == 'QB':
            qb_impact += impact
        elif position in ['RB', 'WR', 'TE']:
            skill_impact += impact
        elif position in ['DL', 'LB', 'DB']:
            defense_impact += impact
    
    return {
        'total_impact': total_impact,
        'qb_impact': qb_impact,
        'skill_impact': skill_impact,
        'defense_impact': defense_impact,
        'injury_count': len(injuries)
    }
    
    if not injuries:
        return {
            'total_impact': 0.0,
            'qb_impact': 0.0,
            'skill_impact': 0.0,
            'defense_impact': 0.0,
            'injury_count': 0
        }
    
    total_impact = 0.0
    qb_impact = 0.0
    skill_impact = 0.0
    defense_impact = 0.0
    
    for position, status, snap_pct in injuries:
        pos_weight = POSITION_WEIGHTS.get(position, 0.3)
        status_mult = INJURY_STATUS_MULTIPLIERS.get(status, 0.5)
        snap_factor = snap_pct / 100.0
        
        impact = pos_weight * status_mult * snap_factor
        total_impact += impact
        
        if position == 'QB':
            qb_impact += impact
        elif position in ['RB', 'WR', 'TE']:
            skill_impact += impact
        elif position in ['DL', 'LB', 'DB']:
            defense_impact += impact
    
    return {
        'total_impact': total_impact,
        'qb_impact': qb_impact,
        'skill_impact': skill_impact,
        'defense_impact': defense_impact,
        'injury_count': len(injuries)
    }


def build_training_features(db: DatabaseManager):
    print("🔨 Building training dataset with injury features...")
    
    games = db.execute_query("""
        SELECT 
            g.game_id,
            g.season,
            g.week,
            ht.abbreviation as home_team,
            at.abbreviation as away_team,
            g.home_score,
            g.away_score,
            g.game_date
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.team_id
        JOIN teams at ON g.away_team_id = at.team_id
        WHERE g.home_score IS NOT NULL
        AND g.away_score IS NOT NULL
        AND g.season >= 2022
        ORDER BY g.season, g.week
    """)
    
    features_list = []
    labels_list = []
    
    for game in games:
        if isinstance(game, dict):
            game_id = game['game_id']
            season = game['season']
            week = game['week']
            home_team = game['home_team']
            away_team = game['away_team']
            home_score = game['home_score']
            away_score = game['away_score']
        else:
            game_id, season, week, home_team, away_team, home_score, away_score, game_date = game
        
        if week <= 1:
            continue
        
        home_stats = get_team_recent_performance(db, home_team, season, week, venue='home')
        away_stats = get_team_recent_performance(db, away_team, season, week, venue='away')
        
        home_injuries = calculate_injury_impact(db, home_team, week, season)
        away_injuries = calculate_injury_impact(db, away_team, week, season)
        
        feature_vector = [
            home_stats['win_pct'],
            away_stats['win_pct'],
            home_stats['ppg'],
            away_stats['ppg'],
            home_stats['pa_pg'],
            away_stats['pa_pg'],
            home_stats['point_diff'],
            away_stats['point_diff'],
            home_stats['recent_form'],
            away_stats['recent_form'],
            home_injuries['total_impact'],
            away_injuries['total_impact'],
            home_injuries['qb_impact'],
            away_injuries['qb_impact'],
            home_injuries['skill_impact'],
            away_injuries['skill_impact'],
            home_injuries['defense_impact'],
            away_injuries['defense_impact'],
            home_injuries['injury_count'],
            away_injuries['injury_count'],
            2.5
        ]
        
        point_diff = home_score - away_score
        
        features_list.append(feature_vector)
        labels_list.append(point_diff)
    
    X = np.array(features_list)
    y = np.array(labels_list)
    
    print(f"✅ Built {len(X)} training samples with {X.shape[1]} features")
    print(f"   Including {10} injury-related features")
    
    return X, y


def get_team_recent_performance(db: DatabaseManager, team: str, season: int, week: int, venue: str = 'all') -> Dict:
    query = """
        SELECT 
            CASE 
                WHEN ht.abbreviation = ? THEN g.home_score
                ELSE g.away_score
            END as team_score,
            CASE 
                WHEN ht.abbreviation = ? THEN g.away_score
                ELSE g.home_score
            END as opp_score,
            CASE 
                WHEN ht.abbreviation = ? THEN 1
                ELSE 0
            END as is_home
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.team_id
        JOIN teams at ON g.away_team_id = at.team_id
        WHERE (ht.abbreviation = ? OR at.abbreviation = ?)
        AND g.season = ?
        AND g.week < ?
        AND g.home_score IS NOT NULL
        ORDER BY g.week DESC
        LIMIT 5
    """
    
    games = db.execute_query(query, (team, team, team, team, team, season, week))
    
    if not games:
        return {
            'win_pct': 0.5,
            'ppg': 20.0,
            'pa_pg': 20.0,
            'point_diff': 0.0,
            'recent_form': 0.0
        }
    
    game_list = []
    for g in games:
        if isinstance(g, dict):
            game_list.append((g['team_score'], g['opp_score'], g['is_home']))
        else:
            game_list.append((g[0], g[1], g[2]))
    
    wins = sum(1 for g in game_list if g[0] > g[1])
    total_games = len(game_list)
    win_pct = wins / total_games if total_games > 0 else 0.5
    
    points_scored = [g[0] for g in game_list]
    points_allowed = [g[1] for g in game_list]
    
    ppg = np.mean(points_scored)
    pa_pg = np.mean(points_allowed)
    point_diff = ppg - pa_pg
    
    recent_form = sum((g[0] > g[1]) for g in game_list[:3]) / min(3, len(game_list))
    
    return {
        'win_pct': win_pct,
        'ppg': ppg,
        'pa_pg': pa_pg,
        'point_diff': point_diff,
        'recent_form': recent_form
    }


def train_enhanced_model(db: DatabaseManager):
    print("\n" + "="*60)
    print("🎯 TRAINING ENHANCED MODEL WITH INJURIES")
    print("="*60)
    
    X, y = build_training_features(db)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print("\n🌲 Training Random Forest...")
    rf_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train_scaled, y_train)
    
    print("🚀 Training Gradient Boosting...")
    gb_model = GradientBoostingRegressor(
        n_estimators=150,
        learning_rate=0.1,
        max_depth=7,
        min_samples_split=10,
        random_state=42
    )
    gb_model.fit(X_train_scaled, y_train)
    
    rf_score = rf_model.score(X_test_scaled, y_test)
    gb_score = gb_model.score(X_test_scaled, y_test)
    
    rf_predictions = rf_model.predict(X_test_scaled)
    gb_predictions = gb_model.predict(X_test_scaled)
    
    rf_mae = np.mean(np.abs(rf_predictions - y_test))
    gb_mae = np.mean(np.abs(gb_predictions - y_test))
    
    print("\n" + "-"*60)
    print("📊 MODEL PERFORMANCE:")
    print(f"  Random Forest R²: {rf_score:.4f} | MAE: {rf_mae:.2f} points")
    print(f"  Gradient Boost R²: {gb_score:.4f} | MAE: {gb_mae:.2f} points")
    
    feature_importance = rf_model.feature_importances_
    feature_names = [
        'Home Win%', 'Away Win%', 'Home PPG', 'Away PPG',
        'Home PA/G', 'Away PA/G', 'Home Diff', 'Away Diff',
        'Home Form', 'Away Form', 'Home Injury Total', 'Away Injury Total',
        'Home QB Injury', 'Away QB Injury', 'Home Skill Injury', 'Away Skill Injury',
        'Home Def Injury', 'Away Def Injury', 'Home Injury Count', 'Away Injury Count',
        'Home Field'
    ]
    
    importance_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': feature_importance
    }).sort_values('Importance', ascending=False)
    
    print("\n🎯 TOP 10 FEATURE IMPORTANCE:")
    for idx, row in importance_df.head(10).iterrows():
        bar = "█" * int(row['Importance'] * 100)
        print(f"  {row['Feature']:20s}: {row['Importance']:.4f} {bar}")
    
    models_dir = project_root / 'models' / 'trained'
    models_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with open(models_dir / f'rf_model_enhanced_{timestamp}.pkl', 'wb') as f:
        pickle.dump(rf_model, f)
    
    with open(models_dir / f'gb_model_enhanced_{timestamp}.pkl', 'wb') as f:
        pickle.dump(gb_model, f)
    
    with open(models_dir / f'scaler_enhanced_{timestamp}.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    
    with open(models_dir / 'rf_model_enhanced_latest.pkl', 'wb') as f:
        pickle.dump(rf_model, f)
    
    with open(models_dir / 'gb_model_enhanced_latest.pkl', 'wb') as f:
        pickle.dump(gb_model, f)
    
    with open(models_dir / 'scaler_enhanced_latest.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    
    print(f"\n💾 Models saved to: {models_dir}")
    print("="*60)


def main():
    db = DatabaseManager()
    
    try:
        train_enhanced_model(db)
        print("\n✅ TRAINING COMPLETE!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()