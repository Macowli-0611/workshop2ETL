# Reliability Evidence Register (Section 4.4 / 8.3)

All runs were executed through Airflow 3.1.8 with `bash scripts/run_reliability_tests.sh`. Screenshots come from `scripts/capture_airflow_evidence.py`. Paths are relative to `docs/evidence/`.

| Evidence ID | Run / Task | Artifact or path | What it proves | Related policy / rule |
| :--- | :--- | :--- | :--- | :--- |
| EV-01 | source-seed service | `source_preparation/seed_report.json` | Grammy CSV loaded into `source_music_db.grammy_awards`: 4,810 = 4,810 rows; winners, year range and null nominees reconcile. | Source preparation (§6.2); not the ETL load |
| EV-02 | `test_a_success` / `extract_grammys` | `test_a_success/logs/extract_grammys_attempt1.log` | The operational pipeline extracts Grammy data **from PostgreSQL** (4,810 rows), not from the CSV. | §4.3 required evidence |
| EV-03 | `test_a_success` / all | `test_a_success/a1_grid_task_states.png`, `a2_graph_success.png`, `task_states.txt` | Successful DAG run: both branches, both raw gates, transformation, prepared gate and load all succeed. | Test A (§7.1) |
| EV-04 | `test_a_success` / raw gates | `runs/test_a_success/spotify_raw_validation.json`, `grammys_raw_validation.json` | Successful raw validation for both sources (9/9 and 4/4), per-rule results. | DQ-RAW-SPT-01..06, DQ-RAW-GRM-01..04 |
| EV-05 | `test_a_success` / `transform_and_integrate` | `runs/test_a_success/integration_report.json` | Cleaning counts per TR rule, match metrics, cardinality, unmatched keys, reconciliation 113,549 = 113,549. | Integration contract, TR-01..TR-11 |
| EV-06 | `test_a_success` / `validate_prepared` | `runs/test_a_success/prepared_validation.json` | Prepared gate (separate suite) passes 18/18 before the load. | DQ-PREP-INT-01..08 |
| EV-07 | `test_a_success` / `load_dw` | `runs/test_a_success/load_report.json`, `a3_load_dw_log.png`, `dw_after_run.txt` | Load summary: 113,549 inserted; fact rows = prepared rows; DW counts. | Load reconciliation |
| EV-08 | `test_b_controlled_failure` / all | `test_b_controlled_failure/b1_grid_failed_run.png`, `b2_graph_failed_run.png`, `task_states.txt` | Controlled failure: `validate_grammys_raw` failed; transform, prepared gate and load `upstream_failed`. | Test B (§7.2), Critical policy |
| EV-09 | `test_b_controlled_failure` / `validate_grammys_raw` | `runs/test_b_controlled_failure/grammys_raw_validation.json` | Machine-readable failure linked to its Rule ID: DQ-RAW-GRM-01, `unexpected_count=1`, value `1800`, decision `STOP`. | DQ-RAW-GRM-01 (Critical) |
| EV-10 | `test_b_controlled_failure` / `validate_grammys_raw` | `test_b_controlled_failure/logs/validate_grammys_raw_attempt1.log`, `b3_failed_task_log.png` | Failed task log with an actionable cause and a pointer to the evidence file. | Logging & observability (§6.11) |
| EV-11 | `test_b_controlled_failure` / DW | `test_b_controlled_failure/dw_after_failed_run.txt`, `injection.txt`, `cleanup.txt` | The DW is untouched by the failed run; the injected row and its cleanup are documented. | Load gated by validation |
| EV-12 | `test_c_safe_rerun` / `load_dw` | `test_c_safe_rerun/dw_before_rerun.txt`, `dw_after_rerun.txt`, `runs/test_c_safe_rerun/load_report.json`, `c2_load_dw_log.png` | Rerun of the same batch: 0 inserted, 113,549 updated, 0 duplicates; identical row counts and measures. | Safe rerun (§7.3), `uq_fact_grain` |
| EV-13 | `test_d_transient_retry` / `extract_grammys` | `test_d_selective_retry/try_history.txt`, `logs/extract_grammys_attempt1.log`, `attempt2.log`, `d2_*.png`, `d3_*.png` | Selective retry: a transient DB refusal fails try 1 and try 2 succeeds; the run completes. | Retry policy (transient class) |
| EV-14 | DAG | `dag_overview_all_runs.png` | All test runs side by side in the Grid view. | Observability |
| EV-15 | GX configuration | `../../gx/expectations/`, `../../gx/validation_definitions/`, `../../gx/checkpoints/` | Suites, Validation Definitions and Checkpoints actually executed by the gates. | GX design (§6.6) |
| EV-16 | DW → BI | `kpi/metabase_dashboard.png`, `kpi/*.csv`, `kpi/*.png` | Dashboard and KPI figures computed from the DW views (not CSV). | §8.1 analytics |
| EV-17 | Profiling | `../../notebooks/data_profiling.ipynb` (executed, outputs saved) | Reproducible evidence behind every risk and threshold. | §6.3 |
