# Reliability Evidence Report: Test C — Repeatability & Safe Rerun (Idempotency)
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Course: ETL (G01) — Section 7.3 of the Brief*

---

## 1. Idempotency Strategy Declaration
* **Engineering Principle:** *"A rerun must not silently corrupt the analytical target."*
* **Implemented Mechanism:** **Atomic Upsert Controlled by Natural Business Grain**.
* **Key Referential Constraint:**
  ```sql
  CONSTRAINT uq_fact_grain UNIQUE (track_sk, genre_sk, time_sk, category_sk)
  ```
* **Target Load Logic:**
  ```sql
  INSERT INTO fact_music_performance (...)
  SELECT ... FROM temp_prepared_staging
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
  ```

---

## 2. Quantitative Comparison Before and After Rerun

| Target Metric / Table Evaluated | Baseline Run 1 Count | Rerun 2 Count | Net Discrepancy | Idempotency Verification |
| :--- | :---: | :---: | :---: | :---: |
| `fact_music_performance` (Total Rows) | **113,549** | **113,549** | **0** | **100% Idempotent** |
| Grammy Awarded Tracks (`is_grammy_winner = True`) | **475** | **475** | **0** | **Zero Duplication** |
| `dim_artist` (Unique Artists) | **17,645** | **17,645** | **0** | **Zero Duplication** |
| `dim_track` (Unique Catalog Tracks) | **89,740** | **89,740** | **0** | **Zero Duplication** |
| `dim_genre` (Catalog Music Genres) | **114** | **114** | **0** | **Zero Duplication** |
| Total Sum of Measure `popularity` | **3,778,820** | **3,778,820** | **0.0** | **Exact Invariant** |
| Mean of Measure `danceability` | **0.5670** | **0.5670** | **0.0** | **Exact Invariant** |

---

## 3. Treatment of Partially Completed or Interrupted Runs
If a pipeline run is halted or disconnected during loading, PostgreSQL transactional boundaries (`with engine.begin() as conn:`) ensure that uncommitted modifications are atomically rolled back. On the subsequent retry or rerun, the upsert logic updates or completes missing rows cleanly, ensuring that partial runs never leave orphaned duplicates or skewed aggregations.
