-- ==============================================================
-- DESTRUCTIVE: drops the whole Data Warehouse so it can be rebuilt.
-- Never executed by the pipeline. Manual use only:
--   docker compose exec postgres psql -U postgres -d dw_music_analytics -f /sql/dw_reset.sql
-- The next load_dw run recreates the schema from sql/dw_schema.sql.
-- ==============================================================
DROP VIEW IF EXISTS vw_kpi_scorecards, vw_kpi1_audio_profile_long, vw_kpi2_genre_uplift_comparable;
DROP VIEW IF EXISTS vw_kpi3_decade_trends, vw_kpi2_genre_uplift, vw_kpi1_audio_profile, vw_track_profile;
DROP TABLE IF EXISTS fact_music_performance CASCADE;
DROP TABLE IF EXISTS dim_track CASCADE;
DROP TABLE IF EXISTS dim_artist CASCADE;
DROP TABLE IF EXISTS dim_genre CASCADE;
DROP TABLE IF EXISTS dim_grammy_category CASCADE;
DROP TABLE IF EXISTS dim_time CASCADE;
