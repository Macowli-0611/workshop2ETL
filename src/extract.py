"""
Data Extraction Module: src/extract.py
--------------------------------------
Handles decoupled extraction from two heterogeneous sources:
1. Spotify Dataset (from local CSV file).
2. Grammy Awards (from relational PostgreSQL database).

Engineering Principle (Section 4.2 & 6.7):
Extraction does not perform premature cleaning to avoid masking raw source anomalies
from the automated raw validation gate.
"""

import os
import logging
import pandas as pd
from sqlalchemy import create_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ETL_Extract")

def extract_spotify(csv_path: str, output_path: str) -> str:
    """
    Extracts raw Spotify catalog data from local CSV source.
    Persists raw output as staging Parquet and returns file path reference.
    """
    logger.info(f"Initiating Spotify extraction from: {csv_path}")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Spotify CSV file not found at: {csv_path}")

    # Read raw data directly without premature cleaning
    df_spotify = pd.read_csv(csv_path)
    total_rows = len(df_spotify)
    logger.info(f"Spotify successfully extracted: {total_rows:,} records, {df_spotify.shape[1]} columns.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_spotify.to_parquet(output_path, index=False)
    logger.info(f"Raw Spotify dataset persisted to staging: {output_path}")

    return output_path

def extract_grammys(db_url: str, output_path: str) -> str:
    """
    Extracts raw Grammy Awards records from relational PostgreSQL database.
    Complies strictly with Section 4.3 requirement (relational source extraction).
    """
    logger.info("Initiating Grammy Awards extraction from operational relational database.")
    engine = create_engine(db_url)

    query = """
        SELECT 
            year,
            title,
            published_at,
            updated_at,
            category,
            nominee,
            artist,
            workers,
            img,
            winner
        FROM grammy_awards
        ORDER BY year ASC, category ASC;
    """

    with engine.connect() as conn:
        df_grammys = pd.read_sql(query, conn)

    total_rows = len(df_grammys)
    logger.info(f"Grammy Awards successfully extracted from PostgreSQL: {total_rows:,} records.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_grammys.to_parquet(output_path, index=False)
    logger.info(f"Raw Grammy dataset persisted to staging: {output_path}")

    return output_path

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    db_user = os.environ["POSTGRES_USER"]
    db_pass = os.environ["POSTGRES_PASSWORD"]
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("SOURCE_DB_NAME", "source_music_db")
    db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    out_s = extract_spotify("data/spotify_dataset.csv", "data/staging/spotify_raw.parquet")
    out_g = extract_grammys(db_url, "data/staging/grammys_raw.parquet")
    print(f"Staging artifacts generated:\n- {out_s}\n- {out_g}")
