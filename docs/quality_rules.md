# Data Quality Rules & Validation Matrix (Phase 2)
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Course: ETL (G01) — Faculty of Engineering and Basic Sciences (UAO)*

---

## 1. Engineering Principles for Quality Design
1. **Separation of Concerns:** Validation *detects violations, measures quality, and generates auditable evidence*; transformation *applies known engineering rules to clean, standardize, and integrate*. **Data is never modified solely to make a validation pass.**
2. **Justified Threshold Engineering:** Thresholds represent calculated engineering decisions reflecting observed data patterns and the protected analytical requirement, rather than arbitrary numbers chosen simply because the current batch passes.
3. **Operational Severity Policy:**
   * **Critical:** Violation invalidates data integrity. **Halts downstream execution immediately** (Test B demonstrates this controlled failure).
   * **Warning:** Inconsistency requires operational visibility but does not invalidate batch processing; logged and monitored under policy.
   * **Informational:** Trend signal or context measurement; does not block processing.

---

## 2. Quality Rules Matrix (Section 6.5 of the Brief)

Eight formal quality rules are implemented across Raw and Prepared validation gates:

| Rule ID | Dataset / Layer | Attribute(s) | Quality Dimension | Quality Rule | Metric / Threshold | Severity | Related Requirement | Engineering Justification |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **DQ-RAW-SPT-01** | Spotify / Raw | `track_id` | **Uniqueness & Completeness** | Technical track identifier must be non-null. | Null count = 0 (100% non-null). | **Critical** | RQ-01, RQ-02 | Natural technical catalog key; nulls break dimension reference integrity. |
| **DQ-RAW-SPT-02** | Spotify / Raw | `duration_ms` | **Validity & Physical Plausibility** | Physical track duration must exceed 1,000 ms. | $\ge 99.9\%$ of raw batch exceeds 1,000 ms. | **Critical** | RQ-03 | Profiling detected corrupted rows with duration = 0 ms that distort averages. |
| **DQ-RAW-SPT-03** | Spotify / Raw | `danceability`, `energy`, `valence`, `acousticness` | **Validity & Range** | Perceptual audio metrics must fall within normalized scale $[0.0, 1.0]$. | 100% within range $[0.0, 1.0]$. | **Critical** | RQ-01 | Out-of-bounds metrics corrupt statistical clustering and audio radar charts. |
| **DQ-RAW-SPT-04** | Spotify / Raw | `popularity` | **Validity & Range** | Digital streaming popularity must fall within integer scale $[0, 100]$. | 100% within range $[0, 100]$. | **Critical** | RQ-02 | Out-of-range metrics distort percentile calculations and popularity KPIs. |
| **DQ-RAW-GRM-01** | Grammys / Raw | `year` | **Validity & Temporal Coverage** | Award edition year must fall within historical Academy bounds $[1958, 2026]$. | 100% within range $[1958, 2026]$. | **Critical** | RQ-01, RQ-03 | Corrupted or out-of-range years destroy time dimension hierarchies and trends. |
| **DQ-RAW-GRM-02** | Grammys / Raw | `nominee` | **Completeness** | Nominated work title must be non-null. | Non-null count $\ge 99.5\%$. | **Warning** | RQ-01, RQ-02 | Profiling revealed 6 historical nulls (0.12%) in special craft categories. |
| **DQ-PREP-INT-01** | Prepared / Gate | `is_grammy_winner` | **Consistency & Domain** | Award indicator must be a valid boolean in $\{True, False\}$. | 100% compliance with domain set. | **Informational** | RQ-01, RQ-02 | Monitors stability and cross-matching rates across periodic ingestion batches. |
| **DQ-PREP-INT-02** | Prepared / Gate | `track_id_spotify`, `track_name`, `artist_name` | **Integrity & Dimensional Readiness** | Natural dimension business keys and names must be 100% non-null post-transformation. | 0% nulls permitted. | **Critical** | RQ-01, RQ-02, RQ-03 | Guarantees referential integrity before triggering final Data Warehouse load. |

---

## 3. Great Expectations Implementation Mapping

### 3.1 Raw Spotify Suite: `spotify_raw_suite`
* `expect_column_values_to_not_be_null(column="track_id")` ➔ **DQ-RAW-SPT-01**
* `expect_column_values_to_be_between(column="duration_ms", min_value=1000, mostly=0.999)` ➔ **DQ-RAW-SPT-02**
* `expect_column_values_to_be_between(column="danceability", min_value=0.0, max_value=1.0)` ➔ **DQ-RAW-SPT-03**
* `expect_column_values_to_be_between(column="energy", min_value=0.0, max_value=1.0)` ➔ **DQ-RAW-SPT-03**
* `expect_column_values_to_be_between(column="popularity", min_value=0, max_value=100)` ➔ **DQ-RAW-SPT-04**

### 3.2 Raw Grammys Suite: `grammys_raw_suite`
* `expect_column_values_to_be_between(column="year", min_value=1958, max_value=2026)` ➔ **DQ-RAW-GRM-01**
* `expect_column_values_to_not_be_null(column="nominee", mostly=0.995)` ➔ **DQ-RAW-GRM-02**

### 3.3 Prepared Data Suite: `prepared_music_suite`
* `expect_column_values_to_not_be_null(column="track_id_spotify")` ➔ **DQ-PREP-INT-02**
* `expect_column_values_to_not_be_null(column="track_name")` ➔ **DQ-PREP-INT-02**
* `expect_column_values_to_not_be_null(column="artist_name")` ➔ **DQ-PREP-INT-02**
* `expect_column_values_to_be_in_set(column="is_grammy_winner", value_set=[True, False])` ➔ **DQ-PREP-INT-01**
