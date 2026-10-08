# Reliability Evidence Report: Test B — Controlled Critical Quality Failure
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Course: ETL (G01) — Section 7.2 of the Brief*

---

## 1. Specification of the Induced Failure Condition
* **Evaluated Critical Rule:** `DQ-RAW-GRM-01` [Critical] — *"Award edition year must fall within historical Academy range [1958, 2026]"*.
* **Activated Anomaly:** Intentionally injected an invalid historical record in the relational source database (`source_music_db.grammy_awards`) with `year = 1800` (pre-dating the Recording Academy's establishment in 1958).
* **DAG Run ID:** `manual__2026-10-07T22:33:55.085717+00:00`

---

## 2. Observed Airflow 3.1.8 Task Execution States

```text
dag_id                  | task_id                 | state           | start_date                       | end_date
========================+=========================+=================+==================================+=================================
reliable_music_pipeline | extract_grammys         | success         | 2026-10-07T22:33:55.601128+00:00 | 2026-10-07T22:33:56.276505+00:00
reliable_music_pipeline | extract_spotify         | success         | 2026-10-07T22:33:55.600749+00:00 | 2026-10-07T22:33:56.640342+00:00
reliable_music_pipeline | validate_spotify_raw    | success         | 2026-10-07T22:33:57.688741+00:00 | 2026-10-07T22:34:01.745844+00:00
reliable_music_pipeline | validate_grammys_raw    | failed          | 2026-10-07T22:33:56.635248+00:00 | 2026-10-07T22:34:05.811114+00:00
reliable_music_pipeline | transform_and_integrate | upstream_failed | 2026-10-07T22:34:06.541336+00:00 | 2026-10-07T22:34:06.541336+00:00
reliable_music_pipeline | validate_prepared       | upstream_failed | 2026-10-07T22:34:07.575243+00:00 | 2026-10-07T22:34:07.575243+00:00
reliable_music_pipeline | load_dw                 | upstream_failed | 2026-10-07T22:34:08.606695+00:00 | 2026-10-07T22:34:08.606695+00:00
```

---

## 3. Great Expectations Machine-Readable Evidence (`grammys_raw_validation.json`)
```json
{
  "dataset": "grammys_raw",
  "total_records": 4810,
  "success": false,
  "rules_evaluated": [
    {
      "expectation_type": "expect_column_values_to_be_between",
      "rule_description": "DQ-RAW-GRM-01 [Critical]: Award year must fall within historical Academy range [1958, 2026].",
      "success": false,
      "observed_value": {
        "element_count": 4810,
        "unexpected_count": 1,
        "unexpected_percent": 0.02079,
        "partial_unexpected_list": [ 1800 ]
      }
    }
  ]
}
```

---

## 4. Engineering Interpretation & System Analysis
1. **Deterministic Quality Gate Trigger:** The extraction task succeeded; the raw validation gate `validate_grammys_raw` correctly detected the anomalous row `1800` outside the legitimate range $[1958, 2026]$.
2. **Immediate Failure Isolation (`retries=0`):** Because the rule was designated `Critical`, the gate immediately raised `CriticalDataQualityError` without blind reattempts, transitioning the task instance to `failed`.
3. **Downstream Block (`upstream_failed`):** Airflow's scheduler resolved dependencies and **immediately blocked** `transform_and_integrate`, `validate_prepared`, and `load_dw`.
4. **Data Warehouse Protection:** No corrupt records were merged into the target analytical store, preserving data trust.
