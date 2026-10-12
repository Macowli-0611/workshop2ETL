# Test C — Repeatability & Safe Rerun (Section 7.3)

**Run:** `reliable_music_pipeline` / `test_c_safe_rerun` · 2026-10-12 01:32:00 → 01:32:35 UTC · **success**. Same input batch as `test_a_success` (same CSV, same source table).

## Strategy

**Snapshot load = controlled upsert on business keys and the fact grain + purge of stale rows, in one transaction** (`src/load.py`).

- Dimensions: `INSERT … ON CONFLICT (<business key>) DO NOTHING / DO UPDATE` on `uq_dim_track_spotify`, `uq_dim_artist_name`, `uq_dim_genre_name`, `uq_dim_category_name`; `dim_time` keyed by year.
- Facts:
  ```sql
  CONSTRAINT uq_fact_grain UNIQUE (track_sk, genre_sk, time_sk, category_sk)

  INSERT INTO fact_music_performance (...) SELECT ... FROM temp_prepared_staging ...
  ON CONFLICT (track_sk, genre_sk, time_sk, category_sk) DO UPDATE
     SET popularity = EXCLUDED.popularity, ..., batch_id = EXCLUDED.batch_id, loaded_at = CURRENT_TIMESTAMP
  RETURNING (xmax = 0) AS inserted;            -- counts inserted vs updated

  DELETE FROM fact_music_performance WHERE batch_id <> :run_id;   -- rows not in the current snapshot
  ```
- Reconciliation guard: rows written ≠ prepared rows → `RuntimeError` → rollback.

## Before / after (`dw_before_rerun.txt`, `dw_after_rerun.txt`)

| Metric | Before (after Test A) | After rerun | Δ |
| :--- | ---: | ---: | ---: |
| `fact_music_performance` rows | 113,549 | 113,549 | 0 |
| Grain duplicates | 0 | 0 | 0 |
| `SUM(popularity)` | 3,783,956 | 3,783,956 | 0 |
| `AVG(danceability)` | 0.567031 | 0.567031 | 0 |
| `SUM(award_count)` | 538 | 538 | 0 |
| Winner rows | 475 | 475 | 0 |
| `batch_id` | `test_a_success` | `test_c_safe_rerun` | every row re-stamped |

`load_report.json` / `load_dw` log (screenshot `c2_load_dw_log.png`): **inserted 0 · updated 113,549 · purged 0**. Dimension counts are unchanged (89,740 tracks, 17,645 artists, 114 genres). The same result appears again in `test_d_transient_retry`.

## Partially completed or failed runs

- **Failure inside `load_dw`** (lock timeout, crash, reconciliation mismatch): all statements run in a single `engine.begin()` transaction, so PostgreSQL rolls back dimensions and facts together. The previous snapshot stays intact, and the retry (`retries=1`) or the next run reloads it idempotently.
- **Failure before `load_dw`** (Test B): the DW is not touched at all (`test_b_controlled_failure/dw_after_failed_run.txt`).
- **Changed source between runs:** rows that disappear from the snapshot (e.g. a track that moves from "unmatched" to "matched", which changes its grain key) are removed by the purge step, so the DW never keeps stale and current versions side by side.

**Conclusion.** Rerunning the same batch creates no duplicate rows and leaves every measure unchanged. Only the audit columns (`batch_id`, `loaded_at`) change, which records which run produced the current snapshot.
