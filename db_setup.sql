CREATE DATABASE IF NOT EXISTS word_impostor_game;
USE word_impostor_game;

CREATE TABLE IF NOT EXISTS games (
    code VARCHAR(10) PRIMARY KEY,
    host VARCHAR(50),
    status VARCHAR(20), -- waiting, in_progress, voting, ended
    round INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    game_code VARCHAR(10),
    is_impostor BOOLEAN DEFAULT FALSE,
    assigned_word VARCHAR(100),
    FOREIGN KEY (game_code) REFERENCES games(code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_code VARCHAR(10),
    username VARCHAR(50),
    round INT,
    content TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_code) REFERENCES games(code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS votes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_code VARCHAR(10),
    voter VARCHAR(50),
    votee VARCHAR(50),
    round INT,
    FOREIGN KEY (game_code) REFERENCES games(code) ON DELETE CASCADE
);
