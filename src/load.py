"""
Data Warehouse Loading Module: src/load.py
------------------------------------------
Implements the final dimensional and idempotent ETL load into PostgreSQL:
- Schema bootstrap: applies sql/dw_schema.sql (idempotent: CREATE ... IF NOT EXISTS).
- Surrogate key resolution and population for dimensions:
  dim_artist, dim_track, dim_genre, dim_time, dim_grammy_category.
- Fact load as a full snapshot inside ONE transaction:
    1. controlled upsert on the grain constraint uq_fact_grain (ON CONFLICT DO UPDATE),
    2. purge of fact rows that are not part of the current snapshot (stale rows from a
       previous batch, e.g. a track that changed from unmatched to matched).
  A rerun with the same batch therefore leaves row counts and measures unchanged, and a
  failure at any point rolls the whole load back, leaving the previous snapshot intact.
"""

import os
import json
import logging
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ETL_Load")

DW_SCHEMA_PATH = os.getenv(
    "DW_SCHEMA_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sql", "dw_schema.sql"),
)


def _snapshot(conn) -> dict:
    """Row counts and selected measures used for reconciliation and safe-rerun comparison."""
    q = lambda sql: conn.execute(text(sql)).scalar()  # noqa: E731
    return {
        "fact_rows": q("SELECT COUNT(*) FROM fact_music_performance"),
        "fact_winner_rows": q("SELECT COUNT(*) FROM fact_music_performance WHERE is_grammy_winner"),
        "dim_track": q("SELECT COUNT(*) FROM dim_track"),
        "dim_artist": q("SELECT COUNT(*) FROM dim_artist"),
        "dim_genre": q("SELECT COUNT(*) FROM dim_genre"),
        "dim_time": q("SELECT COUNT(*) FROM dim_time"),
        "dim_grammy_category": q("SELECT COUNT(*) FROM dim_grammy_category"),
        "sum_popularity": int(q("SELECT COALESCE(SUM(popularity), 0) FROM fact_music_performance")),
        "avg_danceability": float(round(q("SELECT COALESCE(AVG(danceability), 0) FROM fact_music_performance"), 6)),
        "sum_award_count": int(q("SELECT COALESCE(SUM(award_count), 0) FROM fact_music_performance")),
    }


def ensure_schema(engine) -> None:
    """Applies the idempotent DW DDL so a fresh clone can load without manual steps."""
    with open(DW_SCHEMA_PATH, "r", encoding="utf-8") as f:
        ddl = f.read()
    with engine.begin() as conn:
        conn.exec_driver_sql(ddl)
    logger.info(f"DW schema verified/applied from {DW_SCHEMA_PATH}")


def load_data_warehouse(prepared_path: str, dw_url: str, batch_id: str = "batch_001",
                        report_path: str | None = None) -> dict:
    """
    Loads the prepared dataset into the PostgreSQL dimensional Data Warehouse idempotently.
    Returns compact load metrics (safe for XCom) and optionally writes them to report_path.
    """
    logger.info(f"Initiating Data Warehouse loading ({dw_url.split('@')[-1]}) for batch_id={batch_id}")
    df = pd.read_parquet(prepared_path) if prepared_path.endswith(".parquet") else pd.read_csv(prepared_path)
    total_records = len(df)
    logger.info(f"Total prepared records to process: {total_records:,}")

    engine = create_engine(dw_url)
    ensure_schema(engine)

    with engine.connect() as conn:
        before = _snapshot(conn)
    logger.info(f"DW state BEFORE load: {before}")

    with engine.begin() as conn:
        # 1. dim_artist
        artists_df = df[["artist_name", "artist_type"]].drop_duplicates(subset=["artist_name"])
        artists_df.to_sql("temp_dim_artist", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_artist (artist_name, artist_type)
            SELECT artist_name, artist_type FROM temp_dim_artist
            ON CONFLICT (artist_name) DO UPDATE
            SET artist_type = EXCLUDED.artist_type;
            DROP TABLE temp_dim_artist;
        """))

        # 2. dim_genre
        df[["genre_name"]].drop_duplicates().to_sql("temp_dim_genre", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_genre (genre_name)
            SELECT genre_name FROM temp_dim_genre
            ON CONFLICT (genre_name) DO NOTHING;
            DROP TABLE temp_dim_genre;
        """))

        # 3. dim_track
        tracks_df = df[["track_id_spotify", "track_name", "album_name", "duration_ms", "explicit"]] \
            .drop_duplicates(subset=["track_id_spotify"])
        tracks_df.to_sql("temp_dim_track", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_track (track_id_spotify, track_name, album_name, duration_ms, explicit)
            SELECT track_id_spotify, track_name, album_name, duration_ms, explicit FROM temp_dim_track
            ON CONFLICT (track_id_spotify) DO UPDATE
            SET track_name = EXCLUDED.track_name,
                album_name = EXCLUDED.album_name,
                duration_ms = EXCLUDED.duration_ms,
                explicit = EXCLUDED.explicit;
            DROP TABLE temp_dim_track;
        """))

        # 4. dim_grammy_category (SK 0 = 'No Nomination / Not Applicable' is seeded by the DDL)
        df[["grammy_category"]].drop_duplicates().to_sql("temp_dim_cat", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_grammy_category (category_name)
            SELECT grammy_category FROM temp_dim_cat
            WHERE grammy_category != 'No Nomination / Not Applicable'
            ON CONFLICT (category_name) DO NOTHING;
            DROP TABLE temp_dim_cat;
        """))

        # 5. dim_time (smart key = year; SK 0 = 'Unknown' is seeded by the DDL)
        df[["award_year", "decade"]].drop_duplicates(subset=["award_year"]) \
            .to_sql("temp_dim_time", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_time (time_sk, year, decade)
            SELECT award_year, award_year, decade FROM temp_dim_time
            WHERE award_year > 0
            ON CONFLICT (time_sk) DO NOTHING;
            DROP TABLE temp_dim_time;
        """))

        # 6. Fact upsert on the grain constraint
        df.assign(batch_id=batch_id).to_sql("temp_prepared_staging", con=conn, if_exists="replace", index=False)
        upsert = conn.execute(text("""
            INSERT INTO fact_music_performance (
                track_sk, artist_sk, genre_sk, time_sk, category_sk,
                popularity, danceability, energy, valence, acousticness, loudness, tempo,
                is_grammy_winner, is_grammy_nominee, award_count, batch_id
            )
            SELECT
                dt.track_sk, da.artist_sk, dg.genre_sk,
                COALESCE(dti.time_sk, 0), COALESCE(dc.category_sk, 0),
                s.popularity, s.danceability, s.energy, s.valence, s.acousticness, s.loudness, s.tempo,
                s.is_grammy_winner, s.is_grammy_nominee, s.award_count, s.batch_id
            FROM temp_prepared_staging s
            JOIN dim_track dt ON dt.track_id_spotify = s.track_id_spotify
            JOIN dim_artist da ON da.artist_name = s.artist_name
            JOIN dim_genre dg ON dg.genre_name = s.genre_name
            LEFT JOIN dim_time dti ON dti.time_sk = s.award_year
            LEFT JOIN dim_grammy_category dc ON dc.category_name = s.grammy_category
            ON CONFLICT (track_sk, genre_sk, time_sk, category_sk) DO UPDATE
            SET artist_sk = EXCLUDED.artist_sk,
                popularity = EXCLUDED.popularity,
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
                loaded_at = CURRENT_TIMESTAMP
            RETURNING (xmax = 0) AS inserted;
        """)).fetchall()
        inserted = sum(1 for r in upsert if r.inserted)
        updated = len(upsert) - inserted

        # 7. Snapshot purge: rows not touched by this batch no longer exist in the source snapshot
        purged = conn.execute(
            text("DELETE FROM fact_music_performance WHERE batch_id <> :batch_id"),
            {"batch_id": batch_id},
        ).rowcount
        conn.execute(text("DROP TABLE temp_prepared_staging;"))

        if len(upsert) != total_records:
            # Every prepared row must resolve its dimension keys; otherwise roll back the whole load.
            raise RuntimeError(
                f"Fact reconciliation failed: {total_records:,} prepared rows but {len(upsert):,} fact rows written."
            )

    with engine.connect() as conn:
        after = _snapshot(conn)

    metrics = {
        "batch_id": batch_id,
        "prepared_rows": total_records,
        "fact_rows_inserted": inserted,
        "fact_rows_updated": updated,
        "fact_rows_purged_stale": purged,
        "before": before,
        "after": after,
        "fact_rows_equal_prepared_rows": after["fact_rows"] == total_records,
    }

    logger.info("=" * 60)
    logger.info("DATA WAREHOUSE LOAD RECONCILIATION SUMMARY")
    logger.info(f" batch_id: {batch_id}")
    logger.info(f" prepared rows: {total_records:,} | inserted: {inserted:,} | updated: {updated:,} | purged stale: {purged:,}")
    logger.info(f" fact rows before -> after: {before['fact_rows']:,} -> {after['fact_rows']:,}")
    logger.info(f" sum(popularity) before -> after: {before['sum_popularity']:,} -> {after['sum_popularity']:,}")
    logger.info(f" winner rows: {after['fact_winner_rows']:,} | tracks: {after['dim_track']:,} | artists: {after['dim_artist']:,}")
    logger.info("=" * 60)

    if report_path:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, default=str)
        logger.info(f"Load evidence saved to: {report_path}")

    return metrics


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    db_user = os.environ["POSTGRES_USER"]
    db_pass = os.environ["POSTGRES_PASSWORD"]
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("DW_DB_NAME", "dw_music_analytics")
    dw_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    res = load_data_warehouse("data/staging/prepared_music_data.parquet", dw_url, batch_id="local_cli")
    print("Load metrics:", json.dumps(res, indent=2, default=str))
