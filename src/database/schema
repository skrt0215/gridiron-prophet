-- Gridiron Prophet Database Schema V2.1 - CORRECTED

CREATE TABLE IF NOT EXISTS teams (
    team_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(10) NOT NULL UNIQUE,
    city VARCHAR(100),
    conference VARCHAR(10),
    division VARCHAR(20),
    stadium VARCHAR(100),
    head_coach VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS players (
    player_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    position VARCHAR(10),
    height VARCHAR(10),
    weight INT,
    college VARCHAR(100),
    birth_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_player_name_position (name, position)
);

CREATE TABLE IF NOT EXISTS player_seasons (
    player_season_id INT PRIMARY KEY AUTO_INCREMENT,
    player_id INT NOT NULL,
    season INT NOT NULL,
    team_id INT NOT NULL,
    position VARCHAR(10),
    jersey_number INT,
    age INT,
    years_in_league INT,
    games_played INT DEFAULT 0,
    games_started INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Active',
    roster_status VARCHAR(30) DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
    UNIQUE KEY unique_player_season (player_id, season),
    INDEX idx_season_team (season, team_id),
    INDEX idx_player_season (player_id, season),
    INDEX idx_roster_status (roster_status)
);

CREATE TABLE IF NOT EXISTS games (
    game_id INT PRIMARY KEY AUTO_INCREMENT,
    season INT NOT NULL,
    week INT NOT NULL,
    game_date DATE NOT NULL,
    game_time TIME,
    home_team_id INT NOT NULL,
    away_team_id INT NOT NULL,
    home_score INT,
    away_score INT,
    stadium VARCHAR(100),
    weather_temp INT,
    weather_wind INT,
    weather_conditions VARCHAR(100),
    is_dome BOOLEAN DEFAULT FALSE,
    game_status VARCHAR(20) DEFAULT 'Scheduled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id),
    UNIQUE KEY unique_game (season, week, home_team_id, away_team_id),
    INDEX idx_season_week (season, week)
);

CREATE TABLE IF NOT EXISTS injuries (
    injury_id INT PRIMARY KEY AUTO_INCREMENT,
    player_id INT NOT NULL,
    season INT NOT NULL,
    week INT,
    game_id INT,
    injury_status VARCHAR(20) NOT NULL,
    body_part VARCHAR(50),
    date_reported DATE NOT NULL,
    expected_return_date DATE,
    practice_status VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE SET NULL,
    INDEX idx_player_season (player_id, season),
    INDEX idx_season_week (season, week),
    INDEX idx_status (injury_status),
    INDEX idx_date_reported (date_reported)
);

CREATE TABLE IF NOT EXISTS depth_charts (
    depth_chart_id INT PRIMARY KEY AUTO_INCREMENT,
    team_id INT NOT NULL,
    player_id INT NOT NULL,
    season INT NOT NULL,
    week INT NOT NULL,
    position VARCHAR(10) NOT NULL,
    depth_order INT DEFAULT 99,
    snap_percentage DECIMAL(5,2) DEFAULT 0.00,
    offense_snaps INT DEFAULT 0,
    defense_snaps INT DEFAULT 0,
    special_teams_snaps INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    UNIQUE KEY unique_player_week (player_id, season, week),
    INDEX idx_team_season_week (team_id, season, week),
    INDEX idx_player_season (player_id, season)
);

CREATE TABLE IF NOT EXISTS betting_lines (
    betting_line_id INT PRIMARY KEY AUTO_INCREMENT,
    game_id INT NOT NULL,
    source VARCHAR(50),
    spread DECIMAL(4,1),
    spread_juice INT,
    moneyline_home INT,
    moneyline_away INT,
    over_under DECIMAL(4,1),
    over_juice INT,
    under_juice INT,
    is_opening_line BOOLEAN DEFAULT FALSE,
    is_closing_line BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
    INDEX idx_game_timestamp (game_id, timestamp)
);

CREATE TABLE IF NOT EXISTS player_game_stats (
    stat_id INT PRIMARY KEY AUTO_INCREMENT,
    player_id INT NOT NULL,
    game_id INT NOT NULL,
    team_id INT NOT NULL,
    season INT NOT NULL,
    week INT NOT NULL,
    
    pass_attempts INT DEFAULT 0,
    pass_completions INT DEFAULT 0,
    pass_yards INT DEFAULT 0,
    pass_touchdowns INT DEFAULT 0,
    interceptions INT DEFAULT 0,
    sacks_taken INT DEFAULT 0,
    
    rush_attempts INT DEFAULT 0,
    rush_yards INT DEFAULT 0,
    rush_touchdowns INT DEFAULT 0,
    
    targets INT DEFAULT 0,
    receptions INT DEFAULT 0,
    receiving_yards INT DEFAULT 0,
    receiving_touchdowns INT DEFAULT 0,
    
    tackles INT DEFAULT 0,
    tackles_for_loss INT DEFAULT 0,
    sacks DECIMAL(3,1) DEFAULT 0.0,
    forced_fumbles INT DEFAULT 0,
    fumble_recoveries INT DEFAULT 0,
    interceptions_defense INT DEFAULT 0,
    passes_defended INT DEFAULT 0,
    
    fumbles INT DEFAULT 0,
    fumbles_lost INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
    UNIQUE KEY unique_player_game (player_id, game_id),
    INDEX idx_player_season (player_id, season),
    INDEX idx_game_id (game_id)
);