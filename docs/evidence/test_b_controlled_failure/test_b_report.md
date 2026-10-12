# Test B — Controlled Critical Quality Failure (Section 7.2)

**Run:** `reliable_music_pipeline` / `test_b_controlled_failure` · 2026-10-12 01:32:53 → 01:33:07 UTC · final state **failed** (as designed).

## Induced condition

**Blocking rule:** **DQ-RAW-GRM-01 [Critical]**: the award year must be within [1958, 2026]. 1958 is the first ceremony; a year outside the range would corrupt `dim_time` and the RQ-03 decade trend.

**Activation:** one award row with `year = 1800` was inserted into the relational source `source_music_db.grammy_awards` (`injection.txt`), not into the CSV. This also demonstrates that the pipeline reads Grammy data from the database. The row was deleted after the test (`cleanup.txt`: 4,810 rows again).

## Observed behaviour (`task_states.txt`, screenshots `b1`, `b2`)

| Stage | Task | Expected | Observed |
| :--- | :--- | :--- | :--- |
| Extract affected source | `extract_grammys` | success | **success**: 4,811 rows (the invalid row is extracted, not hidden) |
| Unaffected branch | `extract_spotify`, `validate_spotify_raw` | success | **success** |
| Affected raw validation | `validate_grammys_raw` | failure | **failed** (`CriticalDataQualityError`, `retries=0`, so no retry) |
| Downstream transformation | `transform_and_integrate` | does not proceed | **upstream_failed** |
| Prepared validation and load | `validate_prepared`, `load_dw` | do not proceed | **upstream_failed** |

## GX evidence ([`grammys_raw_validation.json`](../runs/test_b_controlled_failure/grammys_raw_validation.json))

```json
"gate_decision": "STOP",
"summary": { "expectations_evaluated": 4, "expectations_passed": 3,
             "critical_failures": ["DQ-RAW-GRM-01 (year)"] },
{ "rule_id": "DQ-RAW-GRM-01", "severity": "Critical",
  "expectation_type": "expect_column_values_to_be_between", "target": "year",
  "success": false, "element_count": 4811, "unexpected_count": 1,
  "partial_unexpected_list": [1800] }
```

## Failed task log (`logs/validate_grammys_raw_attempt1.log`, screenshot `b3_failed_task_log.png`)

```
[INFO]  BATCH CONTEXT | dag=reliable_music_pipeline run_id=test_b_controlled_failure task=validate_grammys_raw try=1
[INFO]  [grammys_raw] 3/4 expectations passed on 4,811 records -> gate decision STOP
[ERROR] Critical quality gate failure in grammys_raw: DQ-RAW-GRM-01 (year). Downstream processing is blocked.
        Evidence: /opt/airflow/docs/evidence/runs/test_b_controlled_failure/grammys_raw_validation.json
[ERROR] Task failed with exception
        CriticalDataQualityError: Critical quality gate failure in grammys_raw: DQ-RAW-GRM-01 (year). ...
```

## Interpretation

1. Extraction does not clean the data, so the invalid record reaches the raw gate. This is intentional: the source problem must stay visible.
2. The raw gate evaluates the `grammys_raw_suite` through its Checkpoint. One Critical expectation fails, so the policy raises `CriticalDataQualityError` and the task fails immediately. It is deterministic, so it is not retried.
3. Under the `all_success` trigger rule, Airflow marks `transform_and_integrate`, `validate_prepared` and `load_dw` as `upstream_failed`. Nothing is transformed or loaded.
4. **The DW is protected:** `dw_after_failed_run.txt` still shows 113,549 rows and `batch_id = test_c_safe_rerun`, the previous successful batch.
5. **Recovery:** correct the source (here: delete the row) and trigger a new run. The idempotent load then converges to the correct snapshot.
