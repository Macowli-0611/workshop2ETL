-- ==============================================================
-- Analytical Data Warehouse DDL: dw_music_analytics
-- Dimensional Star Schema for Workshop-2 ETL
--
-- Idempotent: safe to execute on every load (src/load.py:ensure_schema).
-- It never drops data. To rebuild from scratch use sql/dw_reset.sql.
-- ==============================================================

-- --------------------------------------------------------------
-- 1. DIMENSION: dim_artist  (business key: artist_name)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_artist (
    artist_sk SERIAL PRIMARY KEY,
    artist_name VARCHAR(500) NOT NULL,
    artist_type VARCHAR(50) DEFAULT 'Solo', -- 'Solo' | 'Collaboration'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dim_artist_name UNIQUE (artist_name)
);

-- --------------------------------------------------------------
-- 2. DIMENSION: dim_track  (business key: track_id_spotify)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_track (
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
-- 3. DIMENSION: dim_genre  (business key: genre_name)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_genre (
    genre_sk SERIAL PRIMARY KEY,
    genre_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dim_genre_name UNIQUE (genre_name)
);

-- --------------------------------------------------------------
-- 4. DIMENSION: dim_time  (smart key = award year, 0 = Unknown)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_time (
    time_sk INTEGER PRIMARY KEY,
    year INTEGER NOT NULL,
    decade VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------
-- 5. DIMENSION: dim_grammy_category  (business key: category_name)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_grammy_category (
    category_sk SERIAL PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL,
    category_field VARCHAR(100) DEFAULT 'General',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dim_category_name UNIQUE (category_name)
);

-- Default members (SK = 0) for non-awarded tracks and unknown years
INSERT INTO dim_grammy_category (category_sk, category_name, category_field)
VALUES (0, 'No Nomination / Not Applicable', 'N/A')
ON CONFLICT DO NOTHING;

INSERT INTO dim_time (time_sk, year, decade)
VALUES (0, 0, 'Unknown')
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------
-- 6. FACT TABLE: fact_music_performance
-- Business process: catalog performance of a track in a genre, enriched with its Grammy recognition.
-- Grain: one row per Spotify track x catalog genre x award edition (year) x award category.
--        Unmatched tracks use time_sk = 0 and category_sk = 0.
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_music_performance (
    fact_id BIGSERIAL PRIMARY KEY,

    track_sk INTEGER NOT NULL REFERENCES dim_track(track_sk),
    artist_sk INTEGER NOT NULL REFERENCES dim_artist(artist_sk),
    genre_sk INTEGER NOT NULL REFERENCES dim_genre(genre_sk),
    time_sk INTEGER NOT NULL REFERENCES dim_time(time_sk),
    category_sk INTEGER NOT NULL REFERENCES dim_grammy_category(category_sk),

    -- Consumption and audio measures
    popularity INTEGER NOT NULL CHECK (popularity BETWEEN 0 AND 100),
    danceability NUMERIC(6,4) NOT NULL CHECK (danceability BETWEEN 0 AND 1),
    energy NUMERIC(6,4) NOT NULL CHECK (energy BETWEEN 0 AND 1),
    valence NUMERIC(6,4) NOT NULL CHECK (valence BETWEEN 0 AND 1),
    acousticness NUMERIC(6,4) NOT NULL CHECK (acousticness BETWEEN 0 AND 1),
    loudness NUMERIC(7,3) NOT NULL,
    tempo NUMERIC(7,3) NOT NULL,

    -- Award measures
    is_grammy_winner BOOLEAN NOT NULL DEFAULT FALSE,
    is_grammy_nominee BOOLEAN NOT NULL DEFAULT FALSE,
    award_count INTEGER NOT NULL DEFAULT 0 CHECK (award_count >= 0),

    -- Audit metadata (batch_id = Airflow run_id of the load)
    batch_id VARCHAR(100) NOT NULL,
    loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_fact_grain UNIQUE (track_sk, genre_sk, time_sk, category_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_track ON fact_music_performance(track_sk);
CREATE INDEX IF NOT EXISTS idx_fact_artist ON fact_music_performance(artist_sk);
CREATE INDEX IF NOT EXISTS idx_fact_genre ON fact_music_performance(genre_sk);
CREATE INDEX IF NOT EXISTS idx_fact_time ON fact_music_performance(time_sk);
CREATE INDEX IF NOT EXISTS idx_fact_category ON fact_music_performance(category_sk);
CREATE INDEX IF NOT EXISTS idx_fact_winner ON fact_music_performance(is_grammy_winner);
CREATE INDEX IF NOT EXISTS idx_fact_batch ON fact_music_performance(batch_id);

COMMENT ON TABLE fact_music_performance IS 'Spotify catalog performance and audio features per track and genre, enriched with Grammy Awards recognition.';
COMMENT ON CONSTRAINT uq_fact_grain ON fact_music_performance IS 'Declared grain; target of the ON CONFLICT upsert that makes reruns idempotent.';

-- ==============================================================
-- 7. ANALYTICAL VIEWS (consumed by the BI dashboard and scripts/generate_kpi_charts.py)
-- A track can appear in several genres, so track-level KPIs aggregate DISTINCT tracks
-- first to avoid counting the same song more than once.
-- ==============================================================

-- One row per track: audio profile, popularity and award status
CREATE OR REPLACE VIEW vw_track_profile AS
SELECT
    f.track_sk,
    MAX(dt.track_name)                 AS track_name,
    MAX(da.artist_name)                AS artist_name,
    MAX(da.artist_type)                AS artist_type,
    BOOL_OR(dt.explicit)               AS explicit,
    MAX(f.popularity)                  AS popularity,
    AVG(f.danceability)                AS danceability,
    AVG(f.energy)                      AS energy,
    AVG(f.valence)                     AS valence,
    AVG(f.acousticness)                AS acousticness,
    BOOL_OR(f.is_grammy_winner)        AS is_grammy_winner,
    MAX(f.time_sk)                     AS award_year
FROM fact_music_performance f
JOIN dim_track dt  ON dt.track_sk = f.track_sk
JOIN dim_artist da ON da.artist_sk = f.artist_sk
GROUP BY f.track_sk;

-- RQ-01 / KPI-01: audio profile of Grammy winners vs. catalog
CREATE OR REPLACE VIEW vw_kpi1_audio_profile AS
SELECT
    CASE WHEN is_grammy_winner THEN 'Grammy Winner' ELSE 'General Catalog' END AS award_status,
    COUNT(*)                         AS n_tracks,
    ROUND(AVG(danceability), 4)      AS avg_danceability,
    ROUND(AVG(energy), 4)            AS avg_energy,
    ROUND(AVG(valence), 4)           AS avg_valence,
    ROUND(AVG(acousticness), 4)      AS avg_acousticness,
    ROUND(AVG(popularity), 2)        AS avg_popularity
FROM vw_track_profile
GROUP BY is_grammy_winner;

-- RQ-02 / KPI-02: popularity uplift of Grammy winners per genre (grain = track x genre)
CREATE OR REPLACE VIEW vw_kpi2_genre_uplift AS
SELECT
    dg.genre_name,
    COUNT(DISTINCT f.track_sk) FILTER (WHERE f.is_grammy_winner)      AS n_winner_tracks,
    COUNT(DISTINCT f.track_sk) FILTER (WHERE NOT f.is_grammy_winner)  AS n_catalog_tracks,
    ROUND(AVG(f.popularity) FILTER (WHERE f.is_grammy_winner), 2)     AS avg_pop_winners,
    ROUND(AVG(f.popularity) FILTER (WHERE NOT f.is_grammy_winner), 2) AS avg_pop_catalog,
    ROUND(AVG(f.popularity) FILTER (WHERE f.is_grammy_winner)
        - AVG(f.popularity) FILTER (WHERE NOT f.is_grammy_winner), 2) AS popularity_uplift
FROM fact_music_performance f
JOIN dim_genre dg ON dg.genre_sk = f.genre_sk
GROUP BY dg.genre_name;

-- RQ-03 / KPI-03: explicit and collaboration share of awarded tracks per decade
CREATE OR REPLACE VIEW vw_kpi3_decade_trends AS
SELECT
    t.decade,
    COUNT(*)                                                            AS n_winner_tracks,
    ROUND(100.0 * COUNT(*) FILTER (WHERE p.explicit) / COUNT(*), 2)     AS pct_explicit,
    ROUND(100.0 * COUNT(*) FILTER (WHERE p.artist_type = 'Collaboration') / COUNT(*), 2) AS pct_collaboration
FROM vw_track_profile p
JOIN dim_time t ON t.time_sk = p.award_year
WHERE p.is_grammy_winner AND p.award_year > 0
GROUP BY t.decade;

-- ==============================================================
-- 8. BI-READY VIEWS (Looker Studio cannot compute across rows, so these
--    expose each chart in the exact shape it needs; same logic as above)
-- ==============================================================

-- One row with the headline KPIs (scorecards)
CREATE OR REPLACE VIEW vw_kpi_scorecards AS
SELECT
    (SELECT ROUND(MAX(avg_popularity) FILTER (WHERE award_status = 'Grammy Winner')
                - MAX(avg_popularity) FILTER (WHERE award_status = 'General Catalog'), 2)
       FROM vw_kpi1_audio_profile)                                              AS kpi1_popularity_uplift,
    (SELECT n_tracks FROM vw_kpi1_audio_profile WHERE award_status = 'Grammy Winner') AS awarded_tracks,
    (SELECT COUNT(*) FROM dim_track)                                             AS catalog_tracks,
    (SELECT pct_explicit FROM vw_kpi3_decade_trends ORDER BY decade DESC LIMIT 1) AS kpi3_explicit_latest_decade,
    (SELECT pct_collaboration FROM vw_kpi3_decade_trends ORDER BY decade DESC LIMIT 1) AS kpi3_collab_latest_decade;

-- RQ-01 audio profile in long format (one bar per feature x award status)
CREATE OR REPLACE VIEW vw_kpi1_audio_profile_long AS
SELECT award_status, n_tracks, f.feature, f.mean_value
FROM vw_kpi1_audio_profile,
     LATERAL (VALUES ('Danceability', avg_danceability), ('Energy', avg_energy),
                     ('Valence', avg_valence), ('Acousticness', avg_acousticness)) AS f(feature, mean_value);

-- RQ-02 genres with enough awarded tracks to be compared (n >= 5)
CREATE OR REPLACE VIEW vw_kpi2_genre_uplift_comparable AS
SELECT * FROM vw_kpi2_genre_uplift WHERE n_winner_tracks >= 5;
