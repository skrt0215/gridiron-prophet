-- Gridiron Prophet Database Schema - Phase 1
-- Core tables for NFL game prediction and analysis

-- Teams Table
CREATE TABLE IF NOT EXISTS teams (
    team_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(10) NOT NULL UNIQUE,
    city VARCHAR(100),
    conference VARCHAR(10), -- AFC or NFC
    division VARCHAR(20), -- North, South, East, West
    stadium VARCHAR(100),
    head_coach VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Players Table
CREATE TABLE IF NOT EXISTS players (
    player_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    team_id INT,
    position VARCHAR(10), -- QB, RB, WR, TE, OL, DL, LB, DB, K, P
    jersey_number INT,
    height VARCHAR(10), -- Format: 6-2
    weight INT, -- in pounds
    age INT,
    college VARCHAR(100),
    years_in_league INT,
    status VARCHAR(20) DEFAULT 'Active', -- Active, Injured Reserve, Practice Squad, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE SET NULL
);

-- Games Table
CREATE TABLE IF NOT EXISTS games (
    game_id INT PRIMARY KEY AUTO_INCREMENT,
    season INT NOT NULL, -- Year (e.g., 202