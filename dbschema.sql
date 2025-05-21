-- HARD RESET, Removes all tables and data. disable in production.
DROP TABLE IF EXISTS portfolio;
DROP TABLE IF EXISTS history;
DROP TABLE IF EXISTS users;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL,
    hash TEXT NOT NULL,
    cash NUMERIC NOT NULL DEFAULT 10000.00
);

-- This table (sqlite_sequence) is automatically created and managed by SQLite
-- when you use AUTOINCREMENT. You should *not* manually create or modify it.
-- Remove: CREATE TABLE IF NOT EXISTS sqlite_sequence(name,seq);

CREATE UNIQUE INDEX IF NOT EXISTS username_idx ON users (username);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    shares INTEGER NOT NULL,
    price NUMERIC NOT NULL,
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
); 

CREATE TABLE IF NOT EXISTS portfolio (
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    shares INTEGER NOT NULL,
    price NUMERIC NOT NULL,
    total NUMERIC GENERATED ALWAYS AS (shares * price) STORED,
    FOREIGN KEY (user_id) REFERENCES users(id)
);