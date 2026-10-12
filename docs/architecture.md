# System Architecture & Reliability Policies

Workshop-2 · Building a Reliable Batch Data Pipeline. This document covers sections 4.2, 5, 6.2, 6.11 and 7 of the brief.

---

## 1. Conceptual architecture

```
 SOURCES                    EXTRACT              RAW VALIDATION (GX)          TRANSFORM               PREPARED VALIDATION (GX)   LOAD            TARGET
 ───────                    ───────              ───────────────────          ─────────               ────────────────────────   ────            ──────
 data/spotify_dataset.csv ─► extract_spotify ──► validate_spotify_raw ──┐
   (CSV file source)          (retries: 2)        DQ-RAW-SPT-01..06      │
                                                  (retries: 0)           ├─► transform_and_integrate ─► validate_prepared ─► load_dw ─► dw_music_analytics ─► publish_dw ─► Looker Studio
 source_music_db          ─► extract_grammys ──► validate_grammys_raw ──┘    TR-01..TR-12            DQ-PREP-INT-01..08    (retries: 1)   star schema +        dashboard
   .grammy_awards             (retries: 2)        DQ-RAW-GRM-01..04           integration contract    (retries: 0)          single tx,     KPI views            (3 KPIs)
   (PostgreSQL source)                            (retries: 0)                (retries: 0)                                  upsert+purge

 Source preparation (not the ETL load): service source-seed → scripts/seed_source_db.py loads data/the_grammy_awards.csv
 into source_music_db.grammy_awards and writes docs/evidence/source_preparation/seed_report.json (row-count reconciliation).
```

Quality design around the flow: profiling (`notebooks/data_profiling.ipynb`) → risks → rules ([quality_rules.md](quality_rules.md)) → GX suites → gates.
Reliability controls: dependencies, selective retries, structured logs with batch context, per-run evidence, controlled failure, idempotent reruns.

### Infrastructure (`docker-compose.yaml`)

| Service | Role |
| :--- | :--- |
| `postgres` (16) | `source_music_db` (Grammy source), `dw_music_analytics` (DW), `airflow_db` (Airflow metadata), `metabase_db` (BI metadata). Bound to 127.0.0.1. |
| `airflow-init` | `airflow db migrate`. |
| `source-seed` | Source preparation and reconciliation (runs once per `up`, before Airflow starts). |
| `airflow` (3.1.8) | `airflow standalone`: api-server, scheduler, dag-processor, triggerer. Logs persisted in `./logs`. |
| `metabase` | Local BI alternative on the DW views (`scripts/setup_metabase.py`). |
| *cloud* Neon PostgreSQL | Published read-only copy of the DW for **Looker Studio** (`scripts/publish_dw.py`; role `bi_reader` can only select the views). |

---

## 2. DAG design (`dags/reliable_music_pipeline.py`)

- Authored with `from airflow.sdk import dag, task` (TaskFlow API); `schedule=None` (manual batch), `catchup=False`, `max_active_runs=1`.
- **Two independently observable source branches** converge in `transform_and_integrate`. With the default `all_success` trigger rule, transformation cannot start unless *both* raw gates succeed, and `load_dw` cannot start unless `validate_prepared` succeeds.
- **Separation of concerns:** the DAG only wires tasks. Logic lives in `src/extract.py`, `src/validation.py`, `src/transform.py` and `src/load.py`, which can also be run outside Airflow.
- **Batch context:** the Airflow `run_id` identifies the batch. Each task logs `BATCH CONTEXT | dag run_id task try logical_date`, writes staging files to `data/staging/<run_id>/` and evidence to `docs/evidence/runs/<run_id>/`. The DW rows carry `batch_id = run_id`.

### Task interfaces (no bulk data in XCom)

| Task | Input (XCom) | Output (XCom) | Persistent artifact |
| :--- | :--- | :--- | :--- |
| `extract_spotify` | — | path `str` | `data/staging/<run>/spotify_raw.parquet` |
| `extract_grammys` | — | path `str` | `data/staging/<run>/grammys_raw.parquet` |
| `validate_spotify_raw` | path | `{dataset, decision, path}` | `runs/<run>/spotify_raw_validation.json` |
| `validate_grammys_raw` | path | `{dataset, decision, path}` | `runs/<run>/grammys_raw_validation.json` |
| `transform_and_integrate` | 2 gate dicts | path `str` | `prepared_music_data.parquet`, `runs/<run>/integration_report.json` |
| `validate_prepared` | path | `{dataset, decision, path}` | `runs/<run>/prepared_validation.json` (19 expectations) |
| `load_dw` | gate dict | load metrics dict (~20 numbers) | `runs/<run>/load_report.json` + DW tables |

---

## 3. Failure & selective retry policy

| Condition | Severity / Type | Pipeline response | Retry? | Justification |
| :--- | :--- | :--- | :--- | :--- |
| Source DB temporarily unavailable / refuses connections (`extract_grammys`) | Transient operational | Task goes to `up_for_retry`; downstream waits. | **Yes:** 2 retries, 15 s initial delay, exponential backoff, max 2 min | A new attempt can succeed without changing input or code. **Demonstrated in Test D.** |
| CSV temporarily unreadable (mount / I/O latency) (`extract_spotify`) | Transient operational | Same as above. | **Yes:** 2 retries, same backoff | Bind mounts can be briefly unavailable after a container restart. |
| CSV missing at the documented path | Deterministic (configuration) | `FileNotFoundError` after the retries are exhausted; downstream blocked. | Retries apply (same class as I/O); they cannot fix it and the error message names the path | The task can't tell "missing" from "not mounted yet" on the first attempt; the cost is under a minute. |
| Missing required column (DQ-RAW-SPT-05 / GRM-03 / PREP-INT-03) | Deterministic data contract, Critical | Gate raises `CriticalDataQualityError`; downstream `upstream_failed`. | **No** (`retries=0`) | Re-validating the same batch reproduces the failure; it must be surfaced. |
| Critical GX rule violated (e.g. year 1800, DQ-RAW-GRM-01) | Deterministic data quality, Critical | Same as above; evidence JSON names the rule and the unexpected values. | **No** | **Demonstrated in Test B.** Requires source correction. |
| Integration collapse: raw data valid but matched rows < 0.1% (DQ-PREP-INT-07) | Deterministic data quality, Critical (prepared gate) | `validate_prepared` fails, `load_dw` is `upstream_failed`, DW keeps the previous snapshot. | **No** | **Demonstrated in Test E.** A source format change must be fixed upstream or in the match rules. |
| Warning GX rule violated (DQ-RAW-SPT-06, DQ-RAW-GRM-02, DQ-PREP-INT-08) | Data quality, Warning | Logged at WARNING, decision `CONTINUE_WITH_WARNING`, batch continues. | n/a | Documented policy: visible but not invalidating. |
| Informational rule signal (DQ-RAW-GRM-04, DQ-PREP-INT-01) | Monitoring | Recorded only. | n/a | Trend signal. |
| Transformation exception (unexpected type, join cardinality violated) | Deterministic code / contract | Task fails with traceback; downstream blocked. | **No** | Same input + same code = same error. |
| DW lock timeout / connection drop during `load_dw` | Transient operational | Whole load transaction rolls back; one retry. | **Yes:** 1 retry, 30 s | Lock contention clears; a single retry limits repeated heavy loads. Atomic transaction makes the retry safe. |
| Fact reconciliation mismatch (prepared rows ≠ written fact rows) | Deterministic contract | `RuntimeError` inside the transaction → rollback; previous DW snapshot intact. | Retried once with `load_dw` (harmless, same result) | Prevents a silent partial load. |

`DEFAULT_ARGS` sets `retries=0`, so a task only retries when its class justifies it. There is no blanket `retries=3`.

---

## 4. Logging & observability

| Question | Where to look |
| :--- | :--- |
| What ran? | Airflow Grid/Graph view: DAG `reliable_music_pipeline`, run IDs `test_a_success`, `test_b_controlled_failure`, `test_c_safe_rerun`, `test_d_transient_retry`, `test_e_prepared_gate`. Every task log starts with `BATCH CONTEXT | dag=… run_id=… task=… try=…`. |
| When? | Run and task start/end timestamps in the UI and in `docs/evidence/test_*/task_states.txt`. |
| Did it succeed? | DAG run / task instance states plus material counts: rows extracted, rows removed per rule, matched rows, fact rows inserted/updated/purged, before/after snapshots (`load_dw` log, `load_report.json`). |
| Where did it fail? | The failed task (red) and `upstream_failed` downstream tasks (screenshots `b1`, `b2`, `e1`). |
| Why? | Actionable error: `Critical quality gate failure in grammys_raw: DQ-RAW-GRM-01 (year)… Evidence: …/grammys_raw_validation.json` and the JSON with `partial_unexpected_list: [1800]`. |
| What happened next? | Retry history (`test_d_selective_retry/try_history.txt`: try 1 failed → try 2 success), stop on Critical, `CONTINUE_WITH_WARNING` for warnings. |

---

## 5. Idempotency & safe rerun (Section 7.3)

**Strategy: snapshot load = controlled upsert on the declared grain + purge of stale rows, in one transaction.**

1. `uq_fact_grain UNIQUE (track_sk, genre_sk, time_sk, category_sk)` declares the fact grain.
2. Dimensions use business-key constraints (`uq_dim_track_spotify`, `uq_dim_artist_name`, `uq_dim_genre_name`, `uq_dim_category_name`; `dim_time` uses the year as smart key) with `ON CONFLICT DO NOTHING/UPDATE`, so reruns never duplicate members.
3. Facts: `INSERT … ON CONFLICT (grain) DO UPDATE SET <measures>, batch_id = :run_id`. `RETURNING (xmax = 0)` counts inserted vs updated rows.
4. `DELETE FROM fact_music_performance WHERE batch_id <> :run_id` removes rows that are no longer part of the current snapshot (e.g. a track whose Grammy match changed). Without this step an upsert-only load would leave orphan rows.
5. Reconciliation: if the rows written differ from the prepared rows, a `RuntimeError` rolls back everything.

**Partially completed or failed runs.** Everything in `load_dw` runs inside `engine.begin()`, so a crash, lock timeout or reconciliation error rolls back dimensions *and* facts together, and the previous snapshot stays intact. A failure before `load_dw` (Test B) never touches the DW: Test B's DW snapshot shows the same 113,549 rows and `batch_id` of the previous successful run. The next successful run (or the retry) converges to the correct snapshot because the load is idempotent.

Evidence: Test C (`docs/evidence/test_c_safe_rerun/`): 0 inserted, 113,549 updated, 0 purged; identical row counts, popularity sum, mean danceability and award count; 0 grain duplicates.
