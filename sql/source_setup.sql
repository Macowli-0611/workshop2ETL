-- ==============================================================
-- Operational Source DDL: Grammy Awards
-- Target Database: source_music_db (or designated operational source)
-- ==============================================================

-- Drop existing table if present for idempotent source initialization
DROP TABLE IF EXISTS grammy_awards CASCADE;

-- Create operational source table hosting historical Grammy Awards records
CREATE TABLE grammy_awards (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    category VARCHAR(255) NOT NULL,
    nominee TEXT,
    artist TEXT,
    workers TEXT,
    img TEXT,
    winner BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Strategic indexes optimizing operational extraction queries
CREATE INDEX idx_grammy_year ON grammy_awards(year);
CREATE INDEX idx_grammy_category ON grammy_awards(category);
CREATE INDEX idx_grammy_artist ON grammy_awards(artist);
CREATE INDEX idx_grammy_winner ON grammy_awards(winner);

-- Engineering comments
COMMENT ON TABLE grammy_awards IS 'Operational source table for Grammy Awards, populated initially from the_grammy_awards.csv to establish a real relational extraction origin.';
COMMENT ON COLUMN grammy_awards.winner IS 'Boolean flag indicating whether the nominee was declared winner in the respective category.';
