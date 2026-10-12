# Data Quality Rules & Great Expectations Design

Workshop-2 · Building a Reliable Batch Data Pipeline. This document covers sections 6.5 and 6.6 of the brief.

---

## 1. Principles

1. **Validation and transformation are separate activities.** Validation detects, measures and records evidence. Transformation applies known rules to clean, standardize and integrate (see [transformation_and_integration.md](transformation_and_integration.md)). Data is never modified just to make a validation pass.
2. **Thresholds are engineering decisions.** Each one comes from profiling evidence (`notebooks/data_profiling.ipynb`), a requirement, the source contract or a post-transformation invariant, not from "what the current batch happens to pass".
3. **Severity policy** (implemented in `src/validation.py:run_gate`):

| Severity | Meaning | Pipeline response |
| :--- | :--- | :--- |
| **Critical** | Continuing would make processing or loading unsafe. | `CriticalDataQualityError` → the task fails, downstream tasks become `upstream_failed`, `load_dw` never runs. |
| **Warning** | The issue needs visibility but does not invalidate the batch. | Logged at `WARNING`, recorded in `summary.warning_failures`; gate decision `CONTINUE_WITH_WARNING`. |
| **Informational** | Monitoring or trend signal. | Recorded in the JSON report; never blocks. |

---

## 2. Quality Rules Matrix (18 rules across 3 gates)

| Rule ID | Dataset / Layer | Attribute(s) | Quality Dimension | Quality Rule | Metric / Threshold | Severity | Related Req. | Justification |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **DQ-RAW-SPT-05** | Spotify / Raw | schema | Conformity (source contract) | All columns required by RQ-01..03 are present. | 14 required columns present (superset allowed). | Critical | RQ-01..03 | Source contract: a missing column breaks every downstream step. |
| **DQ-RAW-SPT-01** | Spotify / Raw | `track_id` | Completeness | Track identifier is non-null. | 0 nulls. | Critical | RQ-01, RQ-02 | Business key of `dim_track`; profiling: 0 nulls. |
| **DQ-RAW-SPT-02** | Spotify / Raw | `duration_ms` | Validity | Duration > 1,000 ms. | ≥ 99.9% of rows. | Critical | RQ-03 | Profiling: 1 corrupted row (0 ms). Tolerance of 0.1% (114 rows) accepts isolated corruption that TR-02 removes, but blocks a systemic unit or format error. |
| **DQ-RAW-SPT-03** | Spotify / Raw | `danceability`, `energy`, `valence`, `acousticness` | Validity (range) | Audio features in [0, 1]. | 100% within range. | Critical | RQ-01 | The source contract defines them as normalized; any violation means a format change. |
| **DQ-RAW-SPT-04** | Spotify / Raw | `popularity` | Validity (range) | Popularity in [0, 100]. | 100% within range. | Critical | RQ-02 | Source contract scale; RQ-02 compares popularity means. |
| **DQ-RAW-SPT-06** | Spotify / Raw | `track_id`, `track_genre` | Uniqueness | Duplicate (track, genre) pairs stay below 1%. | ≥ 99% unique. | Warning | RQ-02 | Profiling: 450 duplicates (0.39%), handled by TR-03. More than 1% would indicate an extraction defect worth investigating, but dedup still makes the batch usable. |
| **DQ-RAW-GRM-03** | Grammys / Raw | schema | Conformity (source contract) | Columns year, title, category, nominee, artist, workers, winner are present. | 7 required columns. | Critical | RQ-01..03 | The extraction query and the integration depend on them. |
| **DQ-RAW-GRM-01** | Grammys / Raw | `year` | Validity (temporal) | Award year within [1958, 2026]. | 100% within range. | Critical | RQ-01, RQ-03 | 1958 = first ceremony, 2026 = current year. Out-of-range years corrupt `dim_time` and the decade KPI. **Used in Test B.** |
| **DQ-RAW-GRM-02** | Grammys / Raw | `nominee` | Completeness | Nominee title populated. | ≥ 99.5% non-null. | Warning | RQ-01, RQ-02 | Profiling: 6 nulls (0.12%) in craft categories. These rows cannot match (TR-06) but do not invalidate the batch. |
| **DQ-RAW-GRM-04** | Grammys / Raw | table | Volume (timeliness / completeness) | Row count between 4,000 and 10,000. | Informational band. | Informational | RQ-03 | Monitors truncated or duplicated extractions (expected 4,810). |
| **DQ-PREP-INT-03** | Prepared | schema | Conformity (load contract) | Prepared columns exactly match the load contract. | Exact set of 21 columns. | Critical | RQ-01..03 | `load_dw` maps columns by name. |
| **DQ-PREP-INT-02** | Prepared | `track_id_spotify`, `track_name`, `artist_name`, `genre_name` | Completeness | Dimension business keys and labels are non-null. | 0 nulls. | Critical | RQ-01..03 | NOT NULL business keys of the dimensions. |
| **DQ-PREP-INT-04** | Prepared | `popularity`, `duration_ms`, audio features | Validity (post-transformation invariant) | Ranges hold after transformation: popularity [0, 100], duration > 1,000 ms (no tolerance), features [0, 1]. | 100% within range. | Critical | RQ-01..03 | After TR-01/02 no exception is acceptable; it also matches the DW `CHECK` constraints. |
| **DQ-PREP-INT-05** | Prepared | `track_id_spotify`, `genre_name`, `award_year`, `grammy_category` | Uniqueness (grain) | One row per declared fact grain. | 0 duplicates. | Critical | RQ-01..03 | Otherwise the `ON CONFLICT` upsert fails or double counts. |
| **DQ-PREP-INT-06** | Prepared | `award_year`, `award_count` (by `is_grammy_winner`) | Consistency (integration integrity) | Matched rows have year in [1958, 2026] and `award_count` ≥ 1; unmatched rows have year = 0. | 100% (row conditions). | Critical | RQ-01, RQ-03 | Verifies that the join and the default-member logic (TR-09) are coherent. |
| **DQ-PREP-INT-07** | Prepared | `is_grammy_winner` | Analytical readiness | Both award tiers exist **and** matched rows are at least 0.1% of the catalog. | Distinct values ⊇ {True, False}; ≥ 0.1% True (about 114 rows; observed 0.42%). | Critical | RQ-01, RQ-02 | Below the floor KPI-02 has no genre with n ≥ 5 and KPI-01 compares against a handful of songs; a > 4× drop means the match key broke. **Proven in Test E.** |
| **DQ-PREP-INT-08** | Prepared | `is_grammy_winner` | Plausibility (match rate) | Matched rows ≤ 5% of the catalog. | ≥ 95% unmatched. | Warning | RQ-01, RQ-02 | Observed 0.42%. A jump above 5% suggests over-matching (key too loose). |
| **DQ-PREP-INT-01** | Prepared | `is_grammy_winner` | Validity (domain) | Award flag is boolean. | Value set {True, False}. | Informational | RQ-01, RQ-02 | Type monitor for the flag used by every KPI. |

---

## 3. Great Expectations Design (Section 6.6)

All three gates (32 expectations: 9 Spotify raw, 4 Grammy raw, 19 prepared) use the same chain, implemented once in `src/validation.py:run_gate`:

```
Data Source (pandas, "<gate>_source")
  └─ Data Asset ("<gate>_asset")
       └─ Batch Definition (whole dataframe, "<gate>_batch")   ← staging Parquet of the current DAG run
Expectation Suite ("<dataset>_suite")                           ← one Expectation per rule, meta.rule_id + meta.severity
Validation Definition ("<gate>_validation_definition") = Batch Definition + Suite
Checkpoint ("<gate>_checkpoint", result_format=SUMMARY)         ← executes the Validation Definition
  └─ result → severity policy → <gate>_validation.json + CONTINUE / CONTINUE_WITH_WARNING / STOP
```

| Design element | Where it lives |
| :--- | :--- |
| Expectations | `spotify_raw_expectations()`, `grammys_raw_expectations()`, `prepared_expectations()` in `src/validation.py` |
| Expectation Suites (exported JSON) | [`gx/expectations/`](../gx/expectations/) |
| Validation Definitions | [`gx/validation_definitions/`](../gx/validation_definitions/) |
| Checkpoints | [`gx/checkpoints/`](../gx/checkpoints/) |
| Validation results (per run, never overwritten) | `docs/evidence/runs/<run_id>/<gate>_validation.json` |

An ephemeral GX context is created per task. This avoids concurrent writes to a shared file context while the two raw gates run in parallel. The declarative configuration is exported to `gx/` on every run, so the repository always shows the suites that actually ran.

Each validation result JSON contains: gate, suite, validation definition, checkpoint, batch context (Airflow `run_id`, source), total records, overall GX success, **gate decision**, a summary of failures by severity, and for every expectation its `rule_id`, severity, target column, success, `element_count`, `unexpected_count`, `unexpected_percent`, `partial_unexpected_list` and `observed_value`.

### 3.1 Expectation → Rule mapping

| Suite | Expectation | Column(s) / kwargs | Rule ID |
| :--- | :--- | :--- | :--- |
| `spotify_raw_suite` | `expect_table_columns_to_match_set` | 14 required columns, `exact_match=False` | DQ-RAW-SPT-05 |
| | `expect_column_values_to_not_be_null` | `track_id` | DQ-RAW-SPT-01 |
| | `expect_column_values_to_be_between` | `duration_ms > 1000`, `mostly=0.999` | DQ-RAW-SPT-02 |
| | `expect_column_values_to_be_between` ×4 | `danceability`, `energy`, `valence`, `acousticness` in [0, 1] | DQ-RAW-SPT-03 |
| | `expect_column_values_to_be_between` | `popularity` in [0, 100] | DQ-RAW-SPT-04 |
| | `expect_compound_columns_to_be_unique` | (`track_id`, `track_genre`), `mostly=0.99` | DQ-RAW-SPT-06 |
| `grammys_raw_suite` | `expect_table_columns_to_match_set` | 7 required columns | DQ-RAW-GRM-03 |
| | `expect_column_values_to_be_between` | `year` in [1958, 2026] | DQ-RAW-GRM-01 |
| | `expect_column_values_to_not_be_null` | `nominee`, `mostly=0.995` | DQ-RAW-GRM-02 |
| | `expect_table_row_count_to_be_between` | 4,000 – 10,000 | DQ-RAW-GRM-04 |
| `prepared_music_suite` | `expect_table_columns_to_match_set` | 21 columns, `exact_match=True` | DQ-PREP-INT-03 |
| | `expect_column_values_to_not_be_null` ×4 | `track_id_spotify`, `track_name`, `artist_name`, `genre_name` | DQ-PREP-INT-02 |
| | `expect_column_values_to_be_between` ×6 | `popularity`, `duration_ms`, 4 audio features | DQ-PREP-INT-04 |
| | `expect_compound_columns_to_be_unique` | fact grain | DQ-PREP-INT-05 |
| | `expect_column_values_to_be_between` ×3 (row conditions) | winners: `award_year` ∈ [1958, 2026], `award_count` ≥ 1; non-winners: `award_year` = 0 | DQ-PREP-INT-06 |
| | `expect_column_distinct_values_to_contain_set` | `is_grammy_winner` ⊇ {True, False} | DQ-PREP-INT-07 |
| | `expect_column_values_to_be_in_set` | `is_grammy_winner` ∈ {True}, `mostly=0.001` (matched-row floor) | DQ-PREP-INT-07 |
| | `expect_column_values_to_be_in_set` | `is_grammy_winner` ∈ {False}, `mostly=0.95` | DQ-PREP-INT-08 |
| | `expect_column_values_to_be_in_set` | `is_grammy_winner` ∈ {True, False} | DQ-PREP-INT-01 |

### 3.2 Recorded results

| Run | Gate | Result | Evidence |
| :--- | :--- | :--- | :--- |
| `test_a_success` | spotify_raw | 9/9 passed → CONTINUE | [`runs/test_a_success/spotify_raw_validation.json`](evidence/runs/test_a_success/spotify_raw_validation.json) |
| `test_a_success` | grammys_raw | 4/4 passed → CONTINUE | [`runs/test_a_success/grammys_raw_validation.json`](evidence/runs/test_a_success/grammys_raw_validation.json) |
| `test_a_success` | prepared | 19/19 passed → CONTINUE | [`runs/test_a_success/prepared_validation.json`](evidence/runs/test_a_success/prepared_validation.json) |
| `test_b_controlled_failure` | grammys_raw | 3/4 → **STOP** (DQ-RAW-GRM-01, `unexpected_count=1`, value 1800) | [`runs/test_b_controlled_failure/grammys_raw_validation.json`](evidence/runs/test_b_controlled_failure/grammys_raw_validation.json) |
| `test_e_prepared_gate` | prepared | 18/19 → **STOP** (DQ-PREP-INT-07: 71 matched rows = 0.063% < 0.1%) | [`runs/test_e_prepared_gate/prepared_validation.json`](evidence/runs/test_e_prepared_gate/prepared_validation.json) |
