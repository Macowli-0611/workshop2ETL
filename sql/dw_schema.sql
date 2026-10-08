-- ==============================================================
-- Analytical Data Warehouse DDL: dw_music_analytics
-- Dimensional Star Schema for Workshop-2 ETL
-- ==============================================================

-- Drop existing tables to ensure clean rebuild when executing migration
DROP TABLE IF EXISTS fact_music_performance CASCADE;
DROP TABLE IF EXISTS dim_track CASCADE;
DROP TABLE IF EXISTS dim_artist CASCADE;
DROP TABLE IF EXISTS dim_genre CASCADE;
DROP TABLE IF EXISTS dim_grammy_category CASCADE;
DROP TABLE IF EXISTS dim_time CASCADE;

-- --------------------------------------------------------------
-- 1. DIMENSION: dim_artist
-- --------------------------------------------------------------
CREATE TABLE dim_artist (
    artist_sk SERIAL PRIMARY KEY,
    artist_name VARCHAR(500) NOT NULL,
    artist_type VARCHAR(50) DEFAULT 'Solo', -- 'Solo', 'Collaboration', 'Band'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dim_artist_name UNIQUE (artist_name)
);

-- --------------------------------------------------------------
-- 2. DIMENSION: dim_track
-- --------------------------------------------------------------
CREATE TABLE dim_track (
    track_sk SERIAL PRIMARY KEY,
    track_id_spotify VARCHAR(100) NOT NULL,
    track_name TEXT NOT NULL,
    album_name TEXT,
    duration_ms INTEGER NOT NULL,
    explicit BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dim_track_spotify UNIQUE (track_id_spotify)
);

-- --------------------------------------------------------------
-- 3. DIMENSION: dim_genre
-- --------------------------------------------------------------
CREATE TABLE dim_genre (
    genre_sk SERIAL PRIMARY KEY,
    genre_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dim_genre_name UNIQUE (genre_name)
);

-- --------------------------------------------------------------
-- 4. DIMENSION: dim_time
-- --------------------------------------------------------------
CREATE TABLE dim_time (
    time_sk INTEGER PRIMARY KEY, -- Numeric YYYY format
    year INTEGER NOT NULL,
    decade VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------
-- 5. DIMENSION: dim_grammy_category
-- --------------------------------------------------------------
CREATE TABLE dim_grammy_category (
    category_sk SERIAL PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL,
    category_field VARCHAR(100) DEFAULT 'General',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dim_category_name UNIQUE (category_name)
);

-- Seed default records (SK = 0) for non-awarded tracks and unmapped years
INSERT INTO dim_grammy_category (category_sk, category_name, category_field)
VALUES (0, 'No Nomination / Not Applicable', 'N/A')
ON CONFLICT (category_sk) DO NOTHING;

INSERT INTO dim_time (time_sk, year, decade)
VALUES (0, 0, 'Unknown')
ON CONFLICT (time_sk) DO NOTHING;

-- --------------------------------------------------------------
-- 6. FACT TABLE: fact_music_performance
-- Grain: One row per audio track, catalog genre, and award event edition.
-- --------------------------------------------------------------
CREATE TABLE fact_music_performance (
    fact_id BIGSERIAL PRIMARY KEY,
    
    -- Foreign Keys to Dimension Tables
    track_sk INTEGER NOT NULL REFERENCES dim_track(track_sk) ON DELETE CASCADE,
    artist_sk INTEGER NOT NULL REFERENCES dim_artist(artist_sk) ON DELETE CASCADE,
    genre_sk INTEGER NOT NULL REFERENCES dim_genre(genre_sk) ON DELETE CASCADE,
    time_sk INTEGER NOT NULL REFERENCES dim_time(time_sk) ON DELETE CASCADE,
    category_sk INTEGER NOT NULL REFERENCES dim_grammy_category(category_sk) ON DELETE CASCADE,

    -- Numerical Audio Signals & Consumptions Measures
    popularity INTEGER NOT NULL,
    danceability NUMERIC(6,4) NOT NULL,
    energy NUMERIC(6,4) NOT NULL,
    valence NUMERIC(6,4) NOT NULL,
    acousticness NUMERIC(6,4) NOT NULL,
    loudness NUMERIC(7,3) NOT NULL,
    tempo NUMERIC(7,3) NOT NULL,
    
    -- Award & Recognition Measures
    is_grammy_winner BOOLEAN NOT NULL DEFAULT FALSE,
    is_grammy_nominee BOOLEAN NOT NULL DEFAULT FALSE,
    award_count INTEGER NOT NULL DEFAULT 0,

    -- Audit Metadata & Safe Rerun Management
    batch_id VARCHAR(100) NOT NULL,
    loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Composite unique grain constraint enforcing Safe Rerun Idempotency
    CONSTRAINT uq_fact_grain UNIQUE (track_sk, genre_sk, time_sk, category_sk)
);

-- High-performance analytical indexes for BI reporting
CREATE INDEX idx_fact_track ON fact_music_performance(track_sk);
CREATE INDEX idx_fact_artist ON fact_music_performance(artist_sk);
CREATE INDEX idx_fact_genre ON fact_music_performance(genre_sk);
CREATE INDEX idx_fact_time ON fact_music_performance(time_sk);
CREATE INDEX idx_fact_category ON fact_music_performance(category_sk);
CREATE INDEX idx_fact_winner ON fact_music_performance(is_grammy_winner);
CREATE INDEX idx_fact_popularity ON fact_music_performance(popularity);

-- Engineering comments
COMMENT ON TABLE fact_music_performance IS 'Central fact table evaluating Spotify digital consumption & audio features against historical Grammy Awards acclaim.';
COMMENT ON CONSTRAINT uq_fact_grain ON fact_music_performance IS 'Composite natural grain constraint preventing duplicate rows during pipeline reruns (Safe Rerun pattern).';
