import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
import pandas as pd

class DefensiveRankings:
    """Calculate and track defensive performance rankings"""

    def __init__(self):
        self.db = DatabaseManager()
    
    def calculate_pass_defense_rankings(self, season, through_week=None):
        """
        Calculate pass defense rankings (yards allowed per game)
        
        Returns rankings for each team
        """
        week_clause = f"AND g.week <= {through_week}" if through_week else ""
        
        query = f"""
            SELECT 
                t.team_id,
                t.name,
                t.abbreviation,
                COUNT(DISTINCT g.game_id) as games_played,
                SUM(pgs.pass_yards) as total_pass_yards_allowed,
                AVG(pgs.pass_yards) as avg_pass_yards_per_game,
                SUM(pgs.pass_touchdowns) as pass_tds_allowed,
                SUM(pgs.interceptions) as interceptions
            FROM teams t
            JOIN games g ON (t.team_id = g.home_team_id OR t.team_id = g.away_team_id)
            JOIN player_game_stats pgs ON pgs.game_id = g.game_id
            WHERE g.season = %s
            AND g.game_status = 'Final'
            AND pgs.team_id != t.team_id  -- Opponent stats
            AND pgs.pass_yards > 0
            {week_clause}
            GROUP BY t.team_id, t.name, t.abbreviation
            ORDER BY avg_pass_yards_per_game ASC
        """
        
        results = self.db.execute_query(query, (season,))
        df = pd.DataFrame(results)
        
        df['pass_defense_rank'] = range(1, len(df) + 1)
        
        return df
    
    def calculate_run_defense_rankings(self, season, through_week=None):
        """Calculate run defense rankings (yards allowed per game)"""
        week_clause = f"AND g.week <= {through_week}" if through_week else ""
        
        query = f"""
            SELECT 
                t.team_id,
                t.name,
                t.abbreviation,
                COUNT(DISTINCT g.game_id) as games_played,
                SUM(pgs.rush_yards) as total_rush_yards_allowed,
                AVG(pgs.rush_yards) as avg_rush_yards_per_game,
                SUM(pgs.rush_touchdowns) as rush_tds_allowed
            FROM teams t
            JOIN games g ON (t.team_id = g.home_team_id OR t.team_id = g.away_team_id)
            JOIN player_game_stats pgs ON pgs.game_id = g.game_id
            WHERE g.season = %s
            AND g.game_status = 'Final'
            AND pgs.team_id != t.team_id  -- Opponent stats
            AND pgs.rush_yards > 0
            {week_clause}
            GROUP BY t.team_id, t.name, t.abbreviation
            ORDER BY avg_rush_yards_per_game ASC
        """
        
        results = self.db.execute_query(query, (season,))
        df = pd.DataFrame(results)
        
        df['run_defense_rank'] = range(1, len(df) + 1)
        
        return df
    
    def calculate_points_allowed_rankings(self, season, through_week=None):
        """Calculate points allowed rankings"""
        week_clause = f"AND week <= {through_week}" if through_week else ""
        
        query = f"""
            SELECT 
                t.team_id,
                t.name,
                t.abbreviation,
                COUNT(*) as games,
                SUM(CASE 
                    WHEN g.home_team_id = t.team_id THEN g.away_score
                    ELSE g.home_score
                END) as total_points_allowed,
                AVG(CASE 
                    WHEN g.home_team_id = t.team_id THEN g.away_score
                    ELSE g.home_score
                END) as avg_points_allowed
            FROM teams t
            JOIN games g ON (t.team_id = g.home_team_id OR t.team_id = g.away_team_id)
            WHERE g.season = %s
            AND g.game_status = 'Final'
            {week_clause}
            GROUP BY t.team_id, t.name, t.abbreviation
            ORDER BY avg_points_allowed ASC
        """
        
        results = self.db.execute_query(query, (season,))
        df = pd.DataFrame(results)
        
        df['points_defense_rank'] = range(1, len(df) + 1)
        
        return df
    
    def get_all_defensive_rankings(self, season, through_week=None):
        """Get comprehensive defensive rankings"""
        
        pass_def = self.calculate_pass_defense_rankings(season, through_week)
        run_def = self.calculate_run_defense_rankings(season, through_week)
        points_def = self.calculate_points_allowed_rankings(season, through_week)
        
        rankings = pass_def[['team_id', 'abbreviation', 'pass_defense_rank', 'avg_pass_yards_per_game']].merge(
            run_def[['team_id', 'run_defense_rank', 'avg_rush_yards_per_game']],
            on='team_id'
        ).merge(
            points_def[['team_id', 'points_defense_rank', 'avg_points_allowed']],
            on='team_id'
        )
        
        rankings['overall_defense_rank'] = (
            rankings['pass_defense_rank'] + 
            rankings['run_defense_rank'] + 
            rankings['points_defense_rank']
        ) / 3
        
        rankings = rankings.sort_values('overall_defense_rank')
        
        return rankings

def main():
    ranker = DefensiveRankings()
    
    print("=" * 70)
    print("DEFENSIVE RANKINGS - 2024 SEASON")
    print("=" * 70)
    
    rankings = ranker.get_all_defensive_rankings(2024)
    
    print("\nTop 10 Defenses (Overall):")
    print(f"{'Rank':<6} {'Team':<6} {'Pass Def':<10} {'Run Def':<10} {'Pts Def':<10} {'Overall':<10}")
    print("-" * 70)
    
    for idx, row in rankings.head(10).iterrows():
        print(f"{idx+1:<6} {row['abbreviation']:<6} "
              f"#{row['pass_defense_rank']:<9.0f} "
              f"#{row['run_defense_rank']:<9.0f} "
              f"#{row['points_defense_rank']:<9.0f} "
              f"{row['overall_defense_rank']:<10.1f}")
    
    print("\nBottom 5 Defenses (Overall):")
    print(f"{'Rank':<6} {'Team':<6} {'Pass Def':<10} {'Run Def':<10} {'Pts Def':<10} {'Overall':<10}")
    print("-" * 70)
    
    for idx, row in rankings.tail(5).iterrows():
        rank = len(rankings) - len(rankings.tail(5)) + list(rankings.tail(5).index).index(idx) + 1
        print(f"{rank:<6} {row['abbreviation']:<6} "
              f"#{row['pass_defense_rank']:<9.0f} "
              f"#{row['run_defense_rank']:<9.0f} "
              f"#{row['points_defense_rank']:<9.0f} "
              f"{row['overall_defense_rank']:<10.1f}")

if __name__ == "__main__":
    main()