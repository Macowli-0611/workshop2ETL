# Test E — Prepared Gate Blocks the Load (Section 6.9)

**Run:** `reliable_music_pipeline` / `test_e_prepared_gate` · 2026-10-12 01:34:54 → 01:35:22 UTC · final state **failed** (as designed).

Section 6.9 requires *proof that `load_dw` is gated by the Critical outcome of the prepared gate*. Test B stops at a raw gate; Test E covers the case where the raw data looks valid, but the transformation output is not fit to load.

## Induced condition (`injection.txt`)

A simulated upstream format change in the source database: every non-null Grammy `artist` credit gets the suffix `" [credits v2]"`.

```sql
UPDATE grammy_awards SET artist = artist || ' [credits v2]' WHERE artist IS NOT NULL;   -- 2,970 rows
```

Year, nominee, schema and volume are untouched, so the source still satisfies every raw rule. The integration key (title, primary artist) no longer matches the Spotify catalog, except for 13 keys where the suffix falls after a `feat.` / `&` / `with` separator and TR-05 discards it.

## Observed behaviour (`task_states.txt`, screenshots `e1`, `e2`)

| Stage | Task | State | Evidence |
| :--- | :--- | :---: | :--- |
| Extract | `extract_spotify`, `extract_grammys` | success | 114,000 / 4,810 rows |
| Raw gates | `validate_spotify_raw`, `validate_grammys_raw` | **success** | 9/9 and 4/4 → `CONTINUE`: nothing is wrong at source level |
| Transform | `transform_and_integrate` | success | [`integration_report.json`](../runs/test_e_prepared_gate/integration_report.json): **71 matched rows** (33 tracks, 13 keys) instead of 475 (282 tracks, 181 keys); match rate 0.063% vs 0.418% |
| Prepared gate | `validate_prepared` | **failed** | [`prepared_validation.json`](../runs/test_e_prepared_gate/prepared_validation.json): 18/19, decision `STOP`, Critical failure `DQ-PREP-INT-07 (is_grammy_winner)` |
| Load | `load_dw` | **upstream_failed** | never started |

Failed task log (`logs/validate_prepared_attempt1.log`):

```
[INFO]  BATCH CONTEXT | dag=reliable_music_pipeline run_id=test_e_prepared_gate task=validate_prepared try=1
[INFO]  [prepared] 18/19 expectations passed on 113,549 records -> gate decision STOP
[ERROR] Critical quality gate failure in prepared: DQ-PREP-INT-07 (is_grammy_winner). Downstream processing is blocked.
[ERROR] Task failed with exception
        CriticalDataQualityError: Critical quality gate failure in prepared: DQ-PREP-INT-07 (is_grammy_winner). ...
```

## The rule that stopped it

**DQ-PREP-INT-07 [Critical]** (analytical readiness): both award tiers must exist, **and matched rows must be at least 0.1% of the catalog (about 114 rows)**. It is implemented as `expect_column_values_to_be_in_set(column="is_grammy_winner", value_set=[True], mostly=0.001)`.

Why 0.1%:
- KPI-02 only compares genres with at least 5 awarded tracks. Below about 114 matched rows practically no genre qualifies, and KPI-01 would compare the catalog against a handful of songs.
- The match rate is stable at 0.42% for this source; a drop of more than 4× means the match key broke, not that the music changed.

## What the test changed in the system

The first execution of this test (before the rule had a minimum) **passed the prepared gate**: the gate only required "at least one match", and the degraded batch was loaded. The test therefore exposed a real gap in the validation design. We added the minimum match rate and reran Tests A–E so that all evidence uses the same 19-expectation prepared suite. The good batch passes it in every run (A, C, D: 19/19).

## DW protected and recovery

`dw_before_run.txt` and `dw_after_failed_run.txt` are identical: 113,549 rows, 475 winner rows, `batch_id = test_d_transient_retry` (the previous good batch). Cleanup (`cleanup.txt`) removed the suffix from the 2,970 rows, so the source again mirrors the provided CSV (0 suffixed rows left, 4,810 rows).
