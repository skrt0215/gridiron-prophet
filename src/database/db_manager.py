import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import os
from dotenv import load_dotenv

# Load environment variables from config/.env file
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
    
    # Team Operations
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
    
    # Player Operations
    def add_player(self, name, team_id=None, position=None, jersey_number=None,
                   height=None, weight=None, age=None, college=None, 
                   years_in_league=None, status='Active'):
        """Add a new player to the database"""
        query = """
            INSERT INTO players (name, team_id, position, jersey_number, height, 
                               weight, age, college, years_in_league, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (name, team_id, position, jersey_number, height, weight, age, college, 
                                           years_in_league, status))
    
    def get_players_by_team(self, team_id):
        """Get all players for a specific team"""
        query = """
            SELECT p.*, t.name as team_name, t.abbreviation as team_abbr
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.team_id
            WHERE p.team_id = %s
            ORDER BY p.position, p.name
        """
        return self.execute_query(query, (team_id,))
    
    # Game Operations
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
        return self.execute_insert(query, (season, week, game_date, game_time, home_team_id, away_team_id, home_score,
        away_score, stadium, weather_temp, weather_wind, weather_conditions,is_dome, game_status))
    
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
    
    # Injury Operations
    def add_injury(self, player_id, injury_status, date_reported, game_id=None,
                   body_part=None, expected_return_date=None, practice_status=None,
                   notes=None):
        """Add an injury report"""
        query = """
            INSERT INTO injuries (player_id, game_id, injury_status, body_part,
                                date_reported, expected_return_date, practice_status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (player_id, game_id, injury_status,
                                           body_part, date_reported,
                                           expected_return_date, practice_status, notes))
    
    def get_active_injuries(self):
        """Get all current injuries (not resolved)"""
        query = """
            SELECT i.*, p.name as player_name, p.position, t.name as team_name
            FROM injuries i
            JOIN players p ON i.player_id = p.player_id
            LEFT JOIN teams t ON p.team_id = t.team_id
            WHERE i.injury_status IN ('Out', 'Doubtful', 'Questionable', 'IR')
            ORDER BY i.date_reported DESC
        """
        return self.execute_query(query)
    
    # Betting Lines Operations
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

# Example usage
if __name__ == "__main__":
    db = DatabaseManager()
    
    # Test connection
    try:
        teams = db.get_all_teams()
        print(f"Database connected successfully! Found {len(teams)} teams.")
    except Exception as e:
        print(f"Database connection failed: {e}")