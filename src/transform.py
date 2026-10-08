"""
Data Transformation & Integration Module: src/transform.py
---------------------------------------------------------
Implements the unified engineering phase:
- Evidence-based cleaning and deduplication derived from profiling.
- Textual normalization and harmonization.
- Execution of the cross-source integration contract (Spotify catalog + Grammy Awards).
- Derivation of analytical measures and dimensions for the star schema.

Integration Contract:
- Matching Keys: (clean_track_name, clean_primary_artist)
- Cardinality: N-to-1 (multiple catalog occurrences of a track across genres mapped to single award event).
- Unmatched Records: Preserved with is_grammy_winner = False and mapped to default dimension keys (SK = 0).
"""

import os
import re
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ETL_Transform")

def _normalize_string(text_val: str) -> str:
    """Normalizes string fields for deterministic cross-source matching."""
    if pd.isna(text_val):
        return ""
    text_clean = str(text_val).lower().strip()
    # Remove peripheral punctuation, brackets and quotes
    text_clean = re.sub(r'["\'\(\)\[\],.;:!?\-]', ' ', text_clean)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    return text_clean

def _extract_primary_artist(artist_str: str) -> str:
    """Extracts primary artist from delimited collaboration strings."""
    if pd.isna(artist_str):
        return "Unknown Artist"
    # Spotify uses semicolon delimiters
    first_part = str(artist_str).split(";")[0]
    # Grammys use collaboration tokens (featuring, feat., &, with)
    first_part = re.split(r'\b(featuring|feat\.|&|with)\b', first_part, flags=re.IGNORECASE)[0]
    return first_part.strip()

def transform_and_integrate(spotify_raw_path: str, grammys_raw_path: str, output_path: str) -> str:
    """
    Executes cleaning, harmonization, cross-matching and metric derivation.
    Persists ready-to-load dataset to output_path (Parquet) and returns reference.
    """
    logger.info("Executing transformation and integration phase...")

    # 1. Load raw staging artifacts
    df_spotify = pd.read_parquet(spotify_raw_path) if spotify_raw_path.endswith(".parquet") else pd.read_csv(spotify_raw_path)
    df_grammys = pd.read_parquet(grammys_raw_path) if grammys_raw_path.endswith(".parquet") else pd.read_csv(grammys_raw_path)

    initial_spotify_rows = len(df_spotify)
    initial_grammy_rows = len(df_grammys)
    logger.info(f"Incoming records: Spotify={initial_spotify_rows:,}, Grammys={initial_grammy_rows:,}")

    # 2. Evidence-based cleaning on Spotify catalog
    # Drop rows with corrupted / missing essential metadata
    df_spotify = df_spotify.dropna(subset=["track_name", "artists", "track_id"])
    # Filter physical impossibilities (duration <= 1000 ms)
    df_spotify = df_spotify[df_spotify["duration_ms"] > 1000]
    # Deduplicate exact tuples on (track_id, track_genre)
    df_spotify = df_spotify.drop_duplicates(subset=["track_id", "track_genre"])

    logger.info(f"Spotify post-cleaning: {len(df_spotify):,} rows (removed {initial_spotify_rows - len(df_spotify):,} corrupted/duplicate rows).")

    # 3. Grammy source cleaning and aggregation
    df_grammys = df_grammys.dropna(subset=["nominee"])
    df_grammys["clean_nominee"] = df_grammys["nominee"].apply(_normalize_string)
    df_grammys["clean_grammy_artist"] = df_grammys["artist"].apply(_extract_primary_artist).apply(_normalize_string)

    # Consolidate multiple award categories for the same track/artist
    grammy_agg = df_grammys.groupby(["clean_nominee", "clean_grammy_artist"]).agg({
        "year": "max",
        "category": "first",
        "winner": "any",
        "title": "count"
    }).reset_index().rename(columns={"title": "award_count", "winner": "is_grammy_winner"})

    # 4. Textual normalization for the Integration Contract
    df_spotify["clean_track_name"] = df_spotify["track_name"].apply(_normalize_string)
    df_spotify["primary_artist"] = df_spotify["artists"].apply(_extract_primary_artist)
    df_spotify["clean_spotify_artist"] = df_spotify["primary_artist"].apply(_normalize_string)

    # Derive artist classification
    df_spotify["artist_type"] = np.where(df_spotify["artists"].str.contains(";", na=False), "Collaboration", "Solo")

    # 5. Execute Integration Contract (Left Join preserving entire catalog)
    df_integrated = df_spotify.merge(
        grammy_agg,
        left_on=["clean_track_name", "clean_spotify_artist"],
        right_on=["clean_nominee", "clean_grammy_artist"],
        how="left"
    )

    # 6. Treatment of Unmatched Catalog Records
    df_integrated["is_grammy_winner"] = df_integrated["is_grammy_winner"].fillna(False).astype(bool)
    df_integrated["is_grammy_nominee"] = df_integrated["is_grammy_winner"]
    df_integrated["award_count"] = df_integrated["award_count"].fillna(0).astype(int)
    df_integrated["grammy_category"] = df_integrated["category"].fillna("No Nomination / Not Applicable")
    
    # Temporal dimension derivation
    df_integrated["award_year"] = df_integrated["year"].fillna(0).astype(int)
    df_integrated["decade"] = np.where(
        df_integrated["award_year"] > 0,
        ((df_integrated["award_year"] // 10) * 10).astype(str) + "s",
        "Unknown"
    )

    # 7. Structure prepared dimensional schema
    prepared_df = pd.DataFrame({
        "track_id_spotify": df_integrated["track_id"],
        "track_name": df_integrated["track_name"],
        "album_name": df_integrated["album_name"].fillna("Single / Unknown Album"),
        "artist_name": df_integrated["primary_artist"],
        "artist_type": df_integrated["artist_type"],
        "genre_name": df_integrated["track_genre"],
        "duration_ms": df_integrated["duration_ms"].astype(int),
        "explicit": df_integrated["explicit"].astype(bool),
        "popularity": df_integrated["popularity"].astype(int),
        "danceability": df_integrated["danceability"].round(4),
        "energy": df_integrated["energy"].round(4),
        "valence": df_integrated["valence"].round(4),
        "acousticness": df_integrated["acousticness"].round(4),
        "loudness": df_integrated["loudness"].round(3),
        "tempo": df_integrated["tempo"].round(3),
        "grammy_category": df_integrated["grammy_category"],
        "award_year": df_integrated["award_year"],
        "decade": df_integrated["decade"],
        "is_grammy_winner": df_integrated["is_grammy_winner"],
        "is_grammy_nominee": df_integrated["is_grammy_nominee"],
        "award_count": df_integrated["award_count"]
    })

    # Enforce unique business grain
    prepared_df = prepared_df.drop_duplicates(subset=["track_id_spotify", "genre_name", "award_year", "grammy_category"])

    total_prepared = len(prepared_df)
    total_winners = prepared_df["is_grammy_winner"].sum()
    logger.info(f"Integration finalized: {total_prepared:,} prepared load-ready rows.")
    logger.info(f"Tracks with confirmed Grammy recognition: {total_winners:,} ({total_winners / total_prepared * 100:.2f}% of catalog).")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    prepared_df.to_parquet(output_path, index=False)
    logger.info(f"Prepared dimensional dataset saved to: {output_path}")

    return output_path

if __name__ == "__main__":
    out = transform_and_integrate(
        "data/staging/spotify_raw.parquet",
        "data/staging/grammys_raw.parquet",
        "data/staging/prepared_music_data.parquet"
    )
    print("Prepared artifact persisted to:", out)
