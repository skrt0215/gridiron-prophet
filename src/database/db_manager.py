import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import os
from dotenv import load_dotenv
load_dotenv('config/.env')
class DatabaseManager:
    """Manages database connections and operations for Gridiron Prophet"""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME')
        self.port = int(os.getenv('DB_PORT', 3306))
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        connection = pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            port=self.port,
            cursorclass=DictCursor
        )
        try:
            yield connection
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
    
    def execute_query(self, query, params=None):
        """Execute a SELECT query and return results"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
    
    def execute_insert(self, query, params=None):
        """Execute an INSERT query and return the last inserted ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.lastrowid
    
    def execute_update(self, query, params=None):
        """Execute an UPDATE or DELETE query and return affected rows"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.rowcount
    
    def add_team(self, name, abbreviation, city=None, conference=None, 
                 division=None, stadium=None, head_coach=None):
        """Add a new team to the database"""
        query = """
            INSERT INTO teams (name, abbreviation, city, conference, division, stadium, head_coach)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (name, abbreviation, city, conference, division, stadium, head_coach))
    
    def get_team_by_abbreviation(self, abbreviation):
        """Get team details by abbreviation"""
        query = "SELECT * FROM teams WHERE abbreviation = %s"
        results = self.execute_query(query, (abbreviation,))
        return results[0] if results else None
    
    def get_all_teams(self):
        """Get all teams"""
        query = "SELECT * FROM teams ORDER BY name"
        return self.execute_query(query)
    
    def add_player(self, name, position=None, height=None, weight=None, 
                   college=None):
        """Add a player to the master players table (NO team info here)"""
        query = """
            INSERT INTO players (name, position, height, weight, college)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE player_id=LAST_INSERT_ID(player_id)
        """
        return self.execute_insert(query, (name, position, height, weight, college))
    
    def get_player_by_name(self, name, position=None):
        """Get player by name (and optionally position)"""
        if position:
            query = "SELECT * FROM players WHERE name = %s AND position = %s LIMIT 1"
            results = self.execute_query(query, (name, position))
        else:
            query = "SELECT * FROM players WHERE name = %s LIMIT 1"
            results = self.execute_query(query, (name,))
        return results[0] if results else None
    
    def get_or_create_player(self, name, position=None, height=None, weight=None, 
                            college=None):
        """Get existing player or create new one, return player_id"""
        player = self.get_player_by_name(name, position)
        if player:
            return player['player_id']
        return self.add_player(name, position, height, weight, college)
    
    def add_player_season(self, player_id, season, team_id, position=None, 
                         jersey_number=None, age=None, years_in_league=None,
                         roster_status='Active', status='Active'):
        """Add or update player-season record"""
        query = """
            INSERT INTO player_seasons 
            (player_id, season, team_id, position, jersey_number, age, 
             years_in_league, roster_status, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                team_id = VALUES(team_id),
                position = VALUES(position),
                jersey_number = VALUES(jersey_number),
                age = VALUES(age),
                years_in_league = VALUES(years_in_league),
                roster_status = VALUES(roster_status),
                status = VALUES(status)
        """
        return self.execute_insert(query, (player_id, season, team_id, position, 
                                          jersey_number, age, years_in_league, 
                                          roster_status, status))
    
    def get_player_season(self, player_id, season):
        """Get player's team/info for a specific season"""
        query = """
            SELECT ps.*, p.name, p.position as player_position, t.abbreviation as team_abbr
            FROM player_seasons ps
            JOIN players p ON ps.player_id = p.player_id
            JOIN teams t ON ps.team_id = t.team_id
            WHERE ps.player_id = %s AND ps.season = %s
        """
        results = self.execute_query(query, (player_id, season))
        return results[0] if results else None
    
    def get_active_players_for_season(self, season, team_id=None, roster_status='Active'):
        """Get all active players for a season (optionally filtered by team)"""
        if team_id:
            query = """
                SELECT ps.*, p.name, p.height, p.weight, p.college, t.abbreviation as team_abbr
                FROM player_seasons ps
                JOIN players p ON ps.player_id = p.player_id
                JOIN teams t ON ps.team_id = t.team_id
                WHERE ps.season = %s AND ps.team_id = %s AND ps.roster_status = %s
                ORDER BY ps.position, p.name
            """
            return self.execute_query(query, (season, team_id, roster_status))
        else:
            query = """
                SELECT ps.*, p.name, p.height, p.weight, p.college, t.abbreviation as team_abbr
                FROM player_seasons ps
                JOIN players p ON ps.player_id = p.player_id
                JOIN teams t ON ps.team_id = t.team_id
                WHERE ps.season = %s AND ps.roster_status = %s
                ORDER BY t.abbreviation, ps.position, p.name
            """
            return self.execute_query(query, (season, roster_status))
    
    def get_players_by_team_season(self, team_id, season):
        """Get all players for a team in a specific season"""
        query = """
            SELECT ps.*, p.name, p.height, p.weight, p.college
            FROM player_seasons ps
            JOIN players p ON ps.player_id = p.player_id
            WHERE ps.team_id = %s AND ps.season = %s
            ORDER BY ps.position, p.name
        """
        return self.execute_query(query, (team_id, season))
    
    def update_roster_status(self, player_id, season, roster_status):
        """Update a player's roster status for a season"""
        query = """
            UPDATE player_seasons 
            SET roster_status = %s 
            WHERE player_id = %s AND season = %s
        """
        return self.execute_update(query, (roster_status, player_id, season))
    
    def get_player_history(self, player_id):
        """Get all seasons a player has played"""
        query = """
            SELECT ps.season, t.abbreviation as team, ps.position, 
                   ps.games_played, ps.games_started, ps.roster_status
            FROM player_seasons ps
            JOIN teams t ON ps.team_id = t.team_id
            WHERE ps.player_id = %s
            ORDER BY ps.season DESC
        """
        return self.execute_query(query, (player_id,))
    
    def game_exists(self, season, week, home_team_id, away_team_id):
        """Check if a game already exists"""
        query = """
            SELECT game_id FROM games 
            WHERE season = %s AND week = %s 
            AND home_team_id = %s AND away_team_id = %s
        """
        result = self.execute_query(query, (season, week, home_team_id, away_team_id))
        return result[0]['game_id'] if result else None
    
    def add_game(self, season, week, game_date, home_team_id, away_team_id,
                 game_time=None, home_score=None, away_score=None, stadium=None,
                 weather_temp=None, weather_wind=None, weather_conditions=None,
                 is_dome=False, game_status='Scheduled'):
        """Add a new game to the database"""
        query = """
            INSERT INTO games (season, week, game_date, game_time, home_team_id, 
                             away_team_id, home_score, away_score, stadium, 
                             weather_temp, weather_wind, weather_conditions, 
                             is_dome, game_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (season, week, game_date, game_time, home_team_id, 
                                          away_team_id, home_score, away_score, stadium, 
                                          weather_temp, weather_wind, weather_conditions, 
                                          is_dome, game_status))
    
    def add_game_safe(self, season, week, game_date, home_team_id, away_team_id,
                     game_time=None, home_score=None, away_score=None, stadium=None,
                     weather_temp=None, weather_wind=None, weather_conditions=None,
                     is_dome=False, game_status='Scheduled'):
        """Add a game only if it doesn't exist, otherwise update it"""
        existing_game_id = self.game_exists(season, week, home_team_id, away_team_id)
        
        if existing_game_id:
            query = """
                UPDATE games SET 
                    game_date = %s, game_time = %s, home_score = %s, away_score = %s,
                    stadium = %s, weather_temp = %s, weather_wind = %s, 
                    weather_conditions = %s, is_dome = %s, game_status = %s
                WHERE game_id = %s
            """
            self.execute_update(query, (game_date, game_time, home_score, away_score,
                                       stadium, weather_temp, weather_wind, 
                                       weather_conditions, is_dome, game_status,
                                       existing_game_id))
            return existing_game_id
        else:
            return self.add_game(season, week, game_date, home_team_id, away_team_id,
                               game_time, home_score, away_score, stadium,
                               weather_temp, weather_wind, weather_conditions,
                               is_dome, game_status)
    
    def get_games_by_week(self, season, week):
        """Get all games for a specific week"""
        query = """
            SELECT g.*, 
                   ht.name as home_team_name, ht.abbreviation as home_team_abbr,
                   at.name as away_team_name, at.abbreviation as away_team_abbr
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE g.season = %s AND g.week = %s
            ORDER BY g.game_date, g.game_time
        """
        return self.execute_query(query, (season, week))
    
    def get_games_by_season(self, season):
        """Get all games for a season"""
        query = """
            SELECT g.*, 
                   ht.abbreviation as home_team_abbr,
                   at.abbreviation as away_team_abbr
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE g.season = %s
            ORDER BY g.week, g.game_date
        """
        return self.execute_query(query, (season,))
    
    def add_player_game_stat(self, player_id, game_id, team_id, season, week, **stats):
        """Add player game statistics (takes all stat fields as kwargs)"""
        base_cols = ['player_id', 'game_id', 'team_id', 'season', 'week']
        base_vals = [player_id, game_id, team_id, season, week]
        
        stat_cols = list(stats.keys())
        stat_vals = list(stats.values())
        
        all_cols = base_cols + stat_cols
        all_vals = base_vals + stat_vals
        
        placeholders = ', '.join(['%s'] * len(all_vals))
        columns = ', '.join(all_cols)
        
        query = f"""
            INSERT INTO player_game_stats ({columns})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE
                {', '.join([f"{col} = VALUES({col})" for col in stat_cols])}
        """
        
        return self.execute_insert(query, tuple(all_vals))
    
    def get_player_stats_by_season(self, player_id, season):
        """Get all game stats for a player in a season"""
        query = """
            SELECT pgs.*, g.week, g.game_date
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id
            WHERE pgs.player_id = %s AND pgs.season = %s
            ORDER BY g.week
        """
        return self.execute_query(query, (player_id, season))
    
    def get_player_career_stats(self, player_id):
        """Get career statistics for a player"""
        query = """
            SELECT 
                pgs.season,
                COUNT(*) as games,
                SUM(pgs.pass_yards) as total_pass_yards,
                SUM(pgs.pass_touchdowns) as total_pass_tds,
                SUM(pgs.rush_yards) as total_rush_yards,
                SUM(pgs.rush_touchdowns) as total_rush_tds,
                SUM(pgs.receiving_yards) as total_rec_yards,
                SUM(pgs.receiving_touchdowns) as total_rec_tds,
                SUM(pgs.tackles) as total_tackles,
                SUM(pgs.sacks) as total_sacks
            FROM player_game_stats pgs
            WHERE pgs.player_id = %s
            GROUP BY pgs.season
            ORDER BY pgs.season DESC
        """
        return self.execute_query(query, (player_id,))
    
    def add_injury(self, player_id, season, injury_status, date_reported, 
                   week=None, game_id=None, body_part=None, expected_return_date=None, 
                   practice_status=None, notes=None):
        """Add an injury report"""
        query = """
            INSERT INTO injuries (player_id, season, week, game_id, injury_status, 
                                body_part, date_reported, expected_return_date, 
                                practice_status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (player_id, season, week, game_id, injury_status,
                                          body_part, date_reported, expected_return_date,
                                          practice_status, notes))
    
    def get_injuries_by_season_week(self, season, week):
        """Get all injuries for a specific week"""
        query = """
            SELECT i.*, p.name as player_name, p.position, 
                   ps.team_id, t.abbreviation as team_abbr
            FROM injuries i
            JOIN players p ON i.player_id = p.player_id
            JOIN player_seasons ps ON i.player_id = ps.player_id AND i.season = ps.season
            JOIN teams t ON ps.team_id = t.team_id
            WHERE i.season = %s AND i.week = %s
            ORDER BY t.abbreviation, p.name
        """
        return self.execute_query(query, (season, week))
    
    def get_active_injuries(self, season):
        """Get all current injuries for a season"""
        query = """
            SELECT i.*, p.name as player_name, p.position,
                   ps.team_id, t.abbreviation as team_abbr
            FROM injuries i
            JOIN players p ON i.player_id = p.player_id
            JOIN player_seasons ps ON i.player_id = ps.player_id AND i.season = ps.season
            JOIN teams t ON ps.team_id = t.team_id
            WHERE i.season = %s 
            AND i.injury_status IN ('Out', 'Doubtful', 'Questionable', 'IR')
            ORDER BY i.date_reported DESC
        """
        return self.execute_query(query, (season,))
    
    def add_betting_line(self, game_id, source=None, spread=None, spread_juice=None,
                        moneyline_home=None, moneyline_away=None, over_under=None,
                        over_juice=None, under_juice=None, is_opening_line=False,
                        is_closing_line=False):
        """Add a betting line for a game"""
        query = """
            INSERT INTO betting_lines (game_id, source, spread, spread_juice,
                                      moneyline_home, moneyline_away, over_under,
                                      over_juice, under_juice, is_opening_line,
                                      is_closing_line)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (game_id, source, spread, spread_juice,
                                          moneyline_home, moneyline_away,
                                          over_under, over_juice, under_juice,
                                          is_opening_line, is_closing_line))
    
    def get_betting_lines_for_game(self, game_id):
        """Get all betting lines for a specific game"""
        query = """
            SELECT * FROM betting_lines
            WHERE game_id = %s
            ORDER BY timestamp
        """
        return self.execute_query(query, (game_id,))
    
    def clear_duplicates(self):
        """Remove duplicate games, keeping the most recent entry"""
        query = """
            DELETE g1 FROM games g1
            INNER JOIN games g2 
            WHERE g1.game_id < g2.game_id
            AND g1.season = g2.season
            AND g1.week = g2.week
            AND g1.home_team_id = g2.home_team_id
            AND g1.away_team_id = g2.away_team_id
        """
        rows_deleted = self.execute_update(query)
        print(f"Removed {rows_deleted} duplicate games")
        return rows_deleted

if __name__ == "__main__":
    db = DatabaseManager()
    
    try:
        teams = db.get_all_teams()
        print(f"✓ Database connected! Found {len(teams)} teams.")
        
        active_2025 = db.get_active_players_for_season(2025)
        print(f"✓ Found {len(active_2025)} active players for 2025 season")
        
    except Exception as e:
        print(f"✗ Database error: {e}")