# Test A — Successful Run (Section 7.1)

**Run:** `reliable_music_pipeline` / `test_a_success` · manual trigger · 2026-10-12 01:31:09 → 01:31:45 UTC (≈ 36 s) · final state **success**.
The DW was rebuilt (`sql/dw_reset.sql`) right before this run, so `load_dw` starts from an empty warehouse.

## Task states

| Stage | Task | State | Evidence |
| :--- | :--- | :---: | :--- |
| Extract both sources | `extract_spotify` (CSV), `extract_grammys` (PostgreSQL `source_music_db`) | success | `logs/extract_*_attempt1.log`: 114,000 and 4,810 rows. The Grammy log says "extracted from PostgreSQL". |
| Raw validation gates | `validate_spotify_raw`, `validate_grammys_raw` | success | [`spotify_raw_validation.json`](../runs/test_a_success/spotify_raw_validation.json) 9/9 · [`grammys_raw_validation.json`](../runs/test_a_success/grammys_raw_validation.json) 4/4 · decision `CONTINUE` |
| Transform & integrate | `transform_and_integrate` | success | [`integration_report.json`](../runs/test_a_success/integration_report.json): 114,000 → 113,549 rows (−1 null metadata, −450 duplicates); 475 matched rows / 282 tracks; reconciliation `true` |
| Prepared validation | `validate_prepared` | success | [`prepared_validation.json`](../runs/test_a_success/prepared_validation.json) 19/19 · `CONTINUE` |
| Load | `load_dw` | success | [`load_report.json`](../runs/test_a_success/load_report.json): inserted 113,549 · updated 0 · purged 0 · fact rows 0 → 113,549 = prepared rows |
| Analytics | Metabase dashboard and KPI views | — | [`../kpi/metabase_dashboard.png`](../kpi/metabase_dashboard.png) reads the DW views |

## Screenshots

- `a1_grid_task_states.png`: Grid view, all 7 task instances in `success`.
- `a2_graph_success.png`: Graph view showing both branches converging into transformation, then the prepared gate and the load.
- `a3_load_dw_log.png`: `load_dw` log with batch context, DW state before the load and the reconciliation summary.

## DW after the run (`dw_after_run.txt`)

113,549 fact rows · 0 grain duplicates · `SUM(popularity)` = 3,783,956 · `AVG(danceability)` = 0.567031 · 475 winner rows · `batch_id` = `test_a_success`.
Dimensions: 89,740 tracks · 17,645 artists · 114 genres · 53 time members · 68 categories.

**Conclusion.** With a batch that satisfies the Critical policy, every stage succeeds and leaves reconciliation evidence. Source rows → clean rows → prepared rows → fact rows are accounted for at every step.
