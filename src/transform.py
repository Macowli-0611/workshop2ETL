"""
Data Transformation & Integration Module: src/transform.py
---------------------------------------------------------
Implements the unified engineering phase:
- Evidence-based cleaning and deduplication derived from profiling.
- Textual normalization and harmonization.
- Execution of the cross-source integration contract (Spotify catalog + Grammy Awards).
- Derivation of analytical measures and dimensions for the star schema.

Integration Contract (docs/integration_contract.md):
- Matching key: (clean_track_name, clean_primary_artist) on both sides.
- Grammy side is aggregated to one row per key before the join, so each Spotify row
  matches at most one award record (many-to-one; duplicate matches are impossible by design).
- Unmatched Spotify rows are preserved with is_grammy_winner = False and default keys (SK = 0).
- Unmatched Grammy keys, multi-award keys and keys matching several catalog tracks are
  measured and written to integration_report.json for every run.

Every transformation decision is listed in docs/transformation_decisions.md (TR-xx IDs).
"""

import os
import re
import json
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ETL_Transform")


def _normalize_string(text_val: str) -> str:
    """TR-04: normalizes text for deterministic cross-source matching."""
    if pd.isna(text_val):
        return ""
    text_clean = str(text_val).lower().strip()
    # Remove peripheral punctuation, brackets and quotes
    text_clean = re.sub(r'["\'\(\)\[\],.;:!?\-]', ' ', text_clean)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    return text_clean


def _extract_primary_artist(artist_str: str) -> str:
    """TR-05: extracts the primary artist from delimited collaboration strings."""
    if pd.isna(artist_str):
        return "Unknown Artist"
    # Spotify uses semicolon delimiters
    first_part = str(artist_str).split(";")[0]
    # Grammys use collaboration tokens (featuring, feat., &, with)
    first_part = re.split(r'\b(featuring|feat\.|&|with)\b', first_part, flags=re.IGNORECASE)[0]
    return first_part.strip()


def transform_and_integrate(spotify_raw_path: str, grammys_raw_path: str, output_path: str,
                            report_path: str | None = None) -> str:
    """
    Executes cleaning, harmonization, cross-matching and metric derivation.
    Persists the ready-to-load dataset to output_path (Parquet) and returns its path.
    When report_path is given, writes the integration/reconciliation evidence there.
    """
    logger.info("Executing transformation and integration phase...")

    # 1. Load raw staging artifacts
    df_spotify = pd.read_parquet(spotify_raw_path) if spotify_raw_path.endswith(".parquet") else pd.read_csv(spotify_raw_path)
    df_grammys = pd.read_parquet(grammys_raw_path) if grammys_raw_path.endswith(".parquet") else pd.read_csv(grammys_raw_path)

    initial_spotify_rows = len(df_spotify)
    initial_grammy_rows = len(df_grammys)
    logger.info(f"Incoming records: Spotify={initial_spotify_rows:,}, Grammys={initial_grammy_rows:,}")

    # 2. Evidence-based cleaning on Spotify catalog
    # TR-01: drop rows with missing essential metadata (profiling: 1 corrupted row)
    df_spotify = df_spotify.dropna(subset=["track_name", "artists", "track_id"])
    removed_null_metadata = initial_spotify_rows - len(df_spotify)
    # TR-02: filter physically impossible durations (<= 1,000 ms)
    rows_before = len(df_spotify)
    df_spotify = df_spotify[df_spotify["duration_ms"] > 1000]
    removed_duration = rows_before - len(df_spotify)
    # TR-03: deduplicate exact (track_id, track_genre) tuples (profiling: 450 rows)
    rows_before = len(df_spotify)
    df_spotify = df_spotify.drop_duplicates(subset=["track_id", "track_genre"])
    removed_duplicates = rows_before - len(df_spotify)

    logger.info(f"Spotify post-cleaning: {len(df_spotify):,} rows (removed {removed_null_metadata} null-metadata, "
                f"{removed_duration} invalid-duration, {removed_duplicates} duplicate rows).")

    # 3. Grammy source cleaning and aggregation
    # TR-06: award rows without a nominee title cannot be matched (Warning rule DQ-RAW-GRM-02)
    df_grammys = df_grammys.dropna(subset=["nominee"]).copy()
    removed_null_nominee = initial_grammy_rows - len(df_grammys)
    df_grammys["clean_nominee"] = df_grammys["nominee"].apply(_normalize_string)
    df_grammys["clean_grammy_artist"] = df_grammys["artist"].apply(_extract_primary_artist).apply(_normalize_string)

    # TR-07: consolidate several awards of the same (work, artist) into one record
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

    # TR-08: derive artist classification (RQ-03 collaborations)
    df_spotify["artist_type"] = np.where(df_spotify["artists"].str.contains(";", na=False), "Collaboration", "Solo")

    # 5. Execute Integration Contract (Left Join preserving entire catalog)
    df_integrated = df_spotify.merge(
        grammy_agg,
        left_on=["clean_track_name", "clean_spotify_artist"],
        right_on=["clean_nominee", "clean_grammy_artist"],
        how="left",
        indicator=True,
        validate="many_to_one",  # guarantees no Spotify row is duplicated by the join
    )

    matched_mask = df_integrated["_merge"] == "both"
    matched_keys = df_integrated.loc[matched_mask, ["clean_nominee", "clean_grammy_artist"]].drop_duplicates()
    tracks_per_key = (df_integrated.loc[matched_mask]
                      .groupby(["clean_nominee", "clean_grammy_artist"])["track_id"].nunique())

    # 6. TR-09: treatment of unmatched catalog records
    df_integrated["is_grammy_winner"] = df_integrated["is_grammy_winner"].astype("boolean").fillna(False).astype(bool)
    # The provided Grammy extract only contains winners (profiling), so nominee == winner.
    df_integrated["is_grammy_nominee"] = df_integrated["is_grammy_winner"]
    df_integrated["award_count"] = df_integrated["award_count"].fillna(0).astype(int)
    df_integrated["grammy_category"] = df_integrated["category"].fillna("No Nomination / Not Applicable")

    # TR-10: temporal dimension derivation
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

    # TR-11: enforce unique fact grain
    rows_before = len(prepared_df)
    prepared_df = prepared_df.drop_duplicates(subset=["track_id_spotify", "genre_name", "award_year", "grammy_category"])
    removed_grain_duplicates = rows_before - len(prepared_df)

    total_prepared = len(prepared_df)
    winner_rows = int(prepared_df["is_grammy_winner"].sum())
    winner_tracks = int(prepared_df.loc[prepared_df["is_grammy_winner"], "track_id_spotify"].nunique())
    grammy_keys = len(grammy_agg)
    unmatched_keys = grammy_keys - len(matched_keys)

    logger.info(f"Integration finalized: {total_prepared:,} prepared load-ready rows.")
    logger.info(f"Matched rows: {winner_rows:,} ({winner_rows / total_prepared * 100:.2f}%) | "
                f"distinct matched tracks: {winner_tracks:,} | matched Grammy keys: {len(matched_keys):,}/{grammy_keys:,} "
                f"| unmatched Grammy keys: {unmatched_keys:,} ({unmatched_keys / grammy_keys * 100:.1f}%)")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    prepared_df.to_parquet(output_path, index=False)
    logger.info(f"Prepared dimensional dataset saved to: {output_path}")

    if report_path:
        report = {
            "spotify": {
                "raw_rows": initial_spotify_rows,
                "removed_null_metadata_TR01": int(removed_null_metadata),
                "removed_invalid_duration_TR02": int(removed_duration),
                "removed_duplicate_track_genre_TR03": int(removed_duplicates),
                "clean_rows": int(len(df_spotify)),
                "distinct_tracks": int(df_spotify["track_id"].nunique()),
            },
            "grammys": {
                "raw_rows": initial_grammy_rows,
                "removed_null_nominee_TR06": int(removed_null_nominee),
                "rows_used_for_matching": int(len(df_grammys)),
                "distinct_match_keys_TR07": int(grammy_keys),
                "keys_with_multiple_awards": int((grammy_agg["award_count"] > 1).sum()),
            },
            "integration": {
                "join": "LEFT JOIN spotify -> grammy_agg ON (clean_track_name, clean_primary_artist)",
                "declared_cardinality": "many-to-one (validated by pandas merge validate='many_to_one')",
                "matched_spotify_rows": winner_rows,
                "match_rate_rows_pct": round(winner_rows / total_prepared * 100, 3),
                "distinct_matched_tracks": winner_tracks,
                "matched_grammy_keys": int(len(matched_keys)),
                "unmatched_grammy_keys": int(unmatched_keys),
                "unmatched_grammy_keys_pct": round(unmatched_keys / grammy_keys * 100, 2),
                "keys_matching_more_than_one_track_id": int((tracks_per_key > 1).sum()),
                "max_track_ids_per_key": int(tracks_per_key.max()) if len(tracks_per_key) else 0,
                "duplicate_matches_per_spotify_row": 0,
            },
            "prepared": {
                "rows": int(total_prepared),
                "removed_grain_duplicates_TR11": int(removed_grain_duplicates),
            },
            "reconciliation": {
                "spotify_clean_rows_equal_prepared_rows": int(len(df_spotify)) == int(total_prepared),
            },
        }
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Integration contract evidence saved to: {report_path}")

    return output_path


if __name__ == "__main__":
    out = transform_and_integrate(
        "data/staging/spotify_raw.parquet",
        "data/staging/grammys_raw.parquet",
        "data/staging/prepared_music_data.parquet",
        "data/staging/integration_report.json",
    )
    print("Prepared artifact persisted to:", out)
