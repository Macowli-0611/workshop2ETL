"""
Módulo de Carga al Data Warehouse: src/load.py
---------------------------------------------
Implementa la carga dimensional e idempotente (Safe Rerun) en PostgreSQL:
- Carga y resolución de claves subrogadas para dimensiones:
  dim_artist, dim_track, dim_genre, dim_time, dim_grammy_category.
- Carga de la tabla de hechos fact_music_performance mediante ON CONFLICT DO UPDATE
  asegurando que ejecuciones repetidas no dupliquen filas ni corrompan métricas.
"""

import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ETL_Load")

def load_data_warehouse(prepared_path: str, dw_url: str, batch_id: str = "batch_001") -> dict:
    """
    Carga el dataset preparado en el Data Warehouse dimensional de manera idempotente.
    Retorna métricas de filas cargadas para auditoría y evidencia de confiabilidad.
    """
    logger.info(f"Iniciando carga al Data Warehouse ({dw_url.split('@')[-1]})...")
    df = pd.read_parquet(prepared_path) if prepared_path.endswith(".parquet") else pd.read_csv(prepared_path)
    total_records = len(df)
    logger.info(f"Total registros preparados a procesar: {total_records:,}")

    engine = create_engine(dw_url)

    with engine.begin() as conn:
        # ----------------------------------------------------------
        # 1. Cargar Dimensión: dim_artist
        # ----------------------------------------------------------
        logger.info("Cargando dimensión dim_artist...")
        artists_df = df[["artist_name", "artist_type"]].drop_duplicates(subset=["artist_name"])
        artists_df.to_sql("temp_dim_artist", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_artist (artist_name, artist_type)
            SELECT artist_name, artist_type FROM temp_dim_artist
            ON CONFLICT (artist_name) DO UPDATE 
            SET artist_type = EXCLUDED.artist_type;
            DROP TABLE temp_dim_artist;
        """))

        # ----------------------------------------------------------
        # 2. Cargar Dimensión: dim_genre
        # ----------------------------------------------------------
        logger.info("Cargando dimensión dim_genre...")
        genres_df = df[["genre_name"]].drop_duplicates(subset=["genre_name"])
        genres_df.to_sql("temp_dim_genre", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_genre (genre_name)
            SELECT genre_name FROM temp_dim_genre
            ON CONFLICT (genre_name) DO NOTHING;
            DROP TABLE temp_dim_genre;
        """))

        # ----------------------------------------------------------
        # 3. Cargar Dimensión: dim_track
        # ----------------------------------------------------------
        logger.info("Cargando dimensión dim_track...")
        tracks_df = df[["track_id_spotify", "track_name", "album_name", "duration_ms", "explicit"]].drop_duplicates(subset=["track_id_spotify"])
        tracks_df.to_sql("temp_dim_track", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_track (track_id_spotify, track_name, album_name, duration_ms, explicit)
            SELECT track_id_spotify, track_name, album_name, duration_ms, explicit FROM temp_dim_track
            ON CONFLICT (track_id_spotify) DO UPDATE 
            SET track_name = EXCLUDED.track_name,
                album_name = EXCLUDED.album_name;
            DROP TABLE temp_dim_track;
        """))

        # ----------------------------------------------------------
        # 4. Cargar Dimensión: dim_grammy_category
        # ----------------------------------------------------------
        logger.info("Cargando dimensión dim_grammy_category...")
        categories_df = df[["grammy_category"]].drop_duplicates(subset=["grammy_category"])
        categories_df.to_sql("temp_dim_cat", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_grammy_category (category_name)
            SELECT grammy_category FROM temp_dim_cat
            WHERE grammy_category != 'Sin Nominación / No Aplica'
            ON CONFLICT (category_name) DO NOTHING;
            DROP TABLE temp_dim_cat;
        """))

        # ----------------------------------------------------------
        # 5. Cargar Dimensión: dim_time
        # ----------------------------------------------------------
        logger.info("Cargando dimensión dim_time...")
        time_df = df[["award_year", "decade"]].drop_duplicates(subset=["award_year"])
        time_df.to_sql("temp_dim_time", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_time (time_sk, year, decade)
            SELECT award_year, award_year, decade FROM temp_dim_time
            WHERE award_year > 0
            ON CONFLICT (time_sk) DO NOTHING;
            DROP TABLE temp_dim_time;
        """))

        # ----------------------------------------------------------
        # 6. Mapear Claves Subrogadas y Cargar Tabla de Hechos
        # ----------------------------------------------------------
        logger.info("Mapeando claves subrogadas y cargando fact_music_performance...")
        
        # Subir dataset preparado a tabla temporal para join directo en PostgreSQL
        df["batch_id"] = batch_id
        df.to_sql("temp_prepared_staging", con=conn, if_exists="replace", index=False)

        upsert_fact_query = text("""
            INSERT INTO fact_music_performance (
                track_sk,
                artist_sk,
                genre_sk,
                time_sk,
                category_sk,
                popularity,
                danceability,
                energy,
                valence,
                acousticness,
                loudness,
                tempo,
                is_grammy_winner,
                is_grammy_nominee,
                award_count,
                batch_id
            )
            SELECT 
                dt.track_sk,
                da.artist_sk,
                dg.genre_sk,
                COALESCE(dti.time_sk, 0) AS time_sk,
                COALESCE(dc.category_sk, 0) AS category_sk,
                s.popularity,
                s.danceability,
                s.energy,
                s.valence,
                s.acousticness,
                s.loudness,
                s.tempo,
                s.is_grammy_winner,
                s.is_grammy_nominee,
                s.award_count,
                s.batch_id
            FROM temp_prepared_staging s
            JOIN dim_track dt ON dt.track_id_spotify = s.track_id_spotify
            JOIN dim_artist da ON da.artist_name = s.artist_name
            JOIN dim_genre dg ON dg.genre_name = s.genre_name
            LEFT JOIN dim_time dti ON dti.time_sk = s.award_year
            LEFT JOIN dim_grammy_category dc ON dc.category_name = s.grammy_category
            ON CONFLICT (track_sk, genre_sk, time_sk, category_sk) DO UPDATE
            SET popularity = EXCLUDED.popularity,
                danceability = EXCLUDED.danceability,
                energy = EXCLUDED.energy,
                valence = EXCLUDED.valence,
                acousticness = EXCLUDED.acousticness,
                loudness = EXCLUDED.loudness,
                tempo = EXCLUDED.tempo,
                is_grammy_winner = EXCLUDED.is_grammy_winner,
                is_grammy_nominee = EXCLUDED.is_grammy_nominee,
                award_count = EXCLUDED.award_count,
                batch_id = EXCLUDED.batch_id,
                loaded_at = CURRENT_TIMESTAMP;

            DROP TABLE temp_prepared_staging;
        """)

        conn.execute(upsert_fact_query)

    # --------------------------------------------------------------
    # 7. Resumen de Carga y Reconciliación
    # --------------------------------------------------------------
    with engine.connect() as conn:
        fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_music_performance;")).scalar()
        winners_count = conn.execute(text("SELECT COUNT(*) FROM fact_music_performance WHERE is_grammy_winner = TRUE;")).scalar()
        artist_count = conn.execute(text("SELECT COUNT(*) FROM dim_artist;")).scalar()
        track_count = conn.execute(text("SELECT COUNT(*) FROM dim_track;")).scalar()

    metrics = {
        "batch_id": batch_id,
        "total_fact_rows": fact_count,
        "total_grammy_winners_in_dw": winners_count,
        "total_dim_artists": artist_count,
        "total_dim_tracks": track_count
    }

    logger.info("="*50)
    logger.info("RESUMEN DE CARGA AL DATA WAREHOUSE:")
    logger.info(f" - Filas en fact_music_performance: {fact_count:,}")
    logger.info(f" - Pistas galardonadas en DW: {winners_count:,}")
    logger.info(f" - Artistas en dimensión: {artist_count:,}")
    logger.info(f" - Canciones en dimensión: {track_count:,}")
    logger.info("="*50)

    return metrics

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_pass = os.getenv("POSTGRES_PASSWORD", "postgres_secure_password")
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("DW_DB_NAME", "dw_music_analytics")
    dw_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    res = load_data_warehouse("data/staging/prepared_music_data.parquet", dw_url)
    print("Métricas de carga:", res)
