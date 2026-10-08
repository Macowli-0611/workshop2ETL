# System Architecture & Reliability Policies
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Course: ETL (G01) — Faculty of Engineering and Basic Sciences (UAO)*

---

## 1. System Architecture Overview

The solution implements an end-to-end reliable batch pipeline orchestrating the integration of Spotify streaming catalog data and historical Grammy Awards records into a dimensional Data Warehouse hosted in PostgreSQL, orchestrated by Apache Airflow 3.1.8.

```
+─────────────────────────────────────────────────────────────────────────────────────────────+
|                                        DATA SOURCES                                         |
|  [ Spotify Dataset (Local CSV file) ]             [ Grammy Awards (Operational PostgreSQL) ]|
+──────────────────────────┬───────────────────────────────────────────────────┬──────────────+
                           │                                                   │
+──────────────────────────▼───────────────────────────────────────────────────▼──────────────+
|                                PHASE 1: EXTRACTION (PARALLEL BRANCHES)                      |
|  extract_spotify (staging Parquet)                extract_grammys (staging Parquet)         |
+──────────────────────────┬───────────────────────────────────────────────────┬──────────────+
                           │                                                   │
+──────────────────────────▼───────────────────────────────────────────────────▼──────────────+
|                                PHASE 2: RAW VALIDATION GATES (GREAT EXPECTATIONS)           |
|  validate_spotify_raw (DQ-RAW-SPT-01..04)         validate_grammys_raw (DQ-RAW-GRM-01..02)  |
+──────────────────────────┬───────────────────────────────────────────────────┬──────────────+
                           └─────────────────────────┬─────────────────────────┘
                                                     │ (Conditional Convergence)
+────────────────────────────────────────────────────▼────────────────────────────────────────+
|                            PHASE 3: TRANSFORMATION & INTEGRATION                            |
|  transform_and_integrate:                                                                   |
|   - Evidence-based cleaning & deduplication (450 duplicate pairs, duration <= 1,000 ms)     |
|   - Textual normalization & primary artist extraction                                       |
|   - Integration Contract: Left Join (track, artist) + treatment of unmatched catalog items  |
+────────────────────────────────────────────────────┬────────────────────────────────────────+
                                                     │
+────────────────────────────────────────────────────▼────────────────────────────────────────+
|                            PHASE 4: PREPARED VALIDATION GATE (GX)                           |
|  validate_prepared (DQ-PREP-INT-01..02):                                                    |
|   - Natural business keys non-null verification                                             |
|   - Normalized audio invariant boundaries in [0.0, 1.0]                                     |
+────────────────────────────────────────────────────┬────────────────────────────────────────+
                                                     │ (Pre-load Quality Gate)
+────────────────────────────────────────────────────▼────────────────────────────────────────+
|                            PHASE 5: DATA WAREHOUSE LOAD (POSTGRESQL)                        |
|  load_dw:                                                                                   |
|   - Dimensions: dim_artist, dim_track, dim_genre, dim_time, dim_grammy_category            |
|   - Fact Table: fact_music_performance (Enforced idempotency via ON CONFLICT DO UPDATE)     |
+────────────────────────────────────────────────────┬────────────────────────────────────────+
                                                     │
+────────────────────────────────────────────────────▼────────────────────────────────────────+
|                            PHASE 6: ANALYTICAL CONSUMPTION (BI DASHBOARD)                   |
|  Direct SQL Queries to DW / Power BI / Tableau / Looker Studio:                             |
|   - KPI 1: Comparative audio & perceptual fingerprint (Winners vs. Catalog)                 |
|   - KPI 2: Popularity multiplier & uplift delta by genre                                    |
|   - KPI 3: Historical decade trends in collaborations and explicit content                  |
+─────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Task Interfaces & Bulk Transport Policy
* **Prohibition of Bulk Transport via XCom:** In accordance with Section 6.11, transferring heavy DataFrames through Airflow's metadata store is strictly prohibited.
* **Reference-Passing Architecture:** Tasks communicate exclusively through lightweight string references (file paths to persistent staging Parquet files: `data/staging/*.parquet`) or compact JSON-serializable audit summary dictionaries.

---

## 3. Failure & Selective Retry Policy Matrix

In compliance with Sections 6.11 and 6.12: *"A blanket policy such as retries=3 everywhere is not evidence of reliability. Justify retry count, delay, and scope for each task class where retries are used."*

| DAG Task (`task_id`) | Potential Failure Condition | Failure Class | Pipeline Response | Retries (`retries`) | Retry Delay (`retry_delay`) | Engineering Justification |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `extract_spotify` | Temporary volume I/O latency or read lock. | Transient operational | Bounded automated retry. | **2** | 10 seconds | Mount delays and ephemeral file system I/O latency can resolve on a second attempt without code changes. |
| `extract_grammys` | Temporary PostgreSQL socket disconnect or pool saturation. | Transient operational | Bounded retry with exponential backoff. | **2** | 10 seconds | Transient database connection spikes recover once socket handshakes re-establish. |
| `validate_spotify_raw` | Critical data rule violation (missing IDs, extreme corruption). | Deterministic data / contract | Immediate failure halting downstream path. | **0** | N/A | Deterministic check. Re-evaluating the identical corrupt batch will replicate identical failure; retries waste resources and mask issues. |
| `validate_grammys_raw` | Critical award rule violation (corrupted year outside $[1958, 2026]$). | Deterministic data / contract | Immediate failure halting downstream path. | **0** | N/A | Requires upstream source correction; blind repetition is anti-pattern. |
| `transform_and_integrate`| Schema mismatch or unhandled data type exception. | Deterministic code / contract | Immediate stop with actionable traceback. | **0** | N/A | Transformation errors are invariant across repeated executions. |
| `validate_prepared` | Missing dimensional keys or broken invariants post-transform. | Deterministic quality gate | Pre-load block protecting the Data Warehouse. | **0** | N/A | Prevents corrupted rows from reaching target dimensional tables. |
| `load_dw` | Ephemeral transactional deadlock or concurrent lock timeout in PostgreSQL. | Transient operational | Single bounded retry. | **1** | 10 seconds | Temporary lock contention clears upon transaction completion by concurrent readers. |

---

## 4. Idempotency & Safe Rerun Strategy
To satisfy Section 7.3:
1. **Composite Unique Grain Constraint:**
   ```sql
   CONSTRAINT uq_fact_grain UNIQUE (track_sk, genre_sk, time_sk, category_sk)
   ```
2. **Atomic Controlled Upsert (`ON CONFLICT DO UPDATE`):**
   * Pre-existing rows have their metrics and audit fields updated cleanly.
   * New rows are inserted without collision.
3. **Repeatability Invariant:** Re-executing the batch 1, 2, or $N$ times guarantees **0 duplicate records** and leaves aggregated measure sums identical.
