# Test D — Selective Retry of a Transient Failure (Sections 6.11 and 8.3)

**Run:** `reliable_music_pipeline` / `test_d_transient_retry` · final state **success** after one automatic retry.

## Procedure (`procedure.txt`)

1. `01:33:24Z` simulate a transient outage: `ALTER DATABASE source_music_db ALLOW_CONNECTIONS false;`. The database is up, but it refuses new connections, the same symptom as a restart or a full connection pool.
2. Trigger the run. `extract_grammys` attempt 1 fails with `psycopg2.OperationalError: database "source_music_db" is not currently accepting connections` and goes to **`up_for_retry`**.
3. `01:33:34Z` restore connections (`ALLOW_CONNECTIONS true`).
4. After the retry delay (15 s, exponential backoff), attempt 2 extracts 4,810 rows; the rest of the DAG completes.

## Evidence

| Artifact | What it proves |
| :--- | :--- |
| `try_history.txt` | `extract_grammys` try 1 = **failed** (01:33:28), try 2 = **success** (01:33:57). |
| `logs/extract_grammys_attempt1.log`, `d2_attempt1_failed_log.png` | Actionable cause of the transient error, with the batch context `try=1`. |
| `logs/extract_grammys_attempt2.log`, `d3_attempt2_success_log.png` | `try=2` recovers: "Grammy Awards successfully extracted from PostgreSQL: 4,810 records". |
| `d1_grid_retry_run.png`, `task_states.txt` | All 7 tasks end in success; the downstream tasks waited for the retry instead of failing. |
| [`../runs/test_d_transient_retry/load_report.json`](../runs/test_d_transient_retry/load_report.json) | The run reloaded the same snapshot: inserted 0 / updated 113,549, which is also idempotent. |

## Why this task retries and the gates do not

| Task class | Retries | Reason |
| :--- | :--- | :--- |
| Extraction (`extract_spotify`, `extract_grammys`) | 2, 15 s + exponential backoff (max 2 min) | Transient I/O or connection problems can disappear without any change to input or code, as this test shows. |
| Validation gates and transformation | 0 | Deterministic: the same batch reproduces the same failure (Test B). Retrying would only delay the evidence. |
| `load_dw` | 1, 30 s | Lock contention or a connection drop is transient; the load is one atomic transaction, so a retry is safe. One attempt limits repeated heavy loads. |
