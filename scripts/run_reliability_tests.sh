#!/usr/bin/env bash
# ==============================================================
# Reproduces the mandatory reliability tests through Airflow and stores the evidence.
#   Test A  test_a_success            full successful run (DW rebuilt first)
#   Test C  test_c_safe_rerun         same batch again -> no duplicates, same measures
#   Test B  test_b_controlled_failure invalid year injected in the Grammy source -> Critical stop
#   Test D  test_d_transient_retry    source DB refuses connections -> extract_grammys retries
#
# Usage (from the repository root, stack running):  bash scripts/run_reliability_tests.sh
# Evidence: docs/evidence/runs/<run_id>/ (GX + integration + load JSON)
#           docs/evidence/test_*/      (SQL snapshots, procedures, readable task logs)
# Screenshots afterwards: see README section 16 (scripts/capture_airflow_evidence.py).
# ==============================================================
set -euo pipefail

DAG=reliable_music_pipeline
AF=workshop2_airflow
PG=workshop2_postgres
EV=docs/evidence

af()   { docker exec "$AF" "$@"; }
psql() { docker exec "$PG" psql -U "${POSTGRES_USER:-postgres}" "$@"; }

api_delete_run() {
  af bash -c "T=\$(curl -s http://localhost:8080/auth/token | python -c 'import sys,json;print(json.load(sys.stdin)[\"access_token\"])'); \
    curl -s -o /dev/null -w '%{http_code}' -X DELETE -H \"Authorization: Bearer \$T\" \
    http://localhost:8080/api/v2/dags/$DAG/dagRuns/$1" || true
}

run_state() { af airflow dags state "$DAG" "$1" 2>/dev/null | tail -1; }

trigger_and_wait() {
  local run=$1
  af airflow dags trigger "$DAG" --run-id "$run" >/dev/null 2>&1
  until run_state "$run" | grep -qE '^(success|failed)'; do sleep 5; done
  echo "    $run -> $(run_state "$run")"
}

task_states() { af airflow tasks states-for-dag-run "$DAG" "$1" 2>/dev/null | grep -E 'task_id|reliable'; }

DW_SNAPSHOT="SELECT COUNT(*) AS fact_rows,
  COUNT(*) - COUNT(DISTINCT (track_sk, genre_sk, time_sk, category_sk)) AS grain_duplicates,
  SUM(popularity) AS sum_popularity, ROUND(AVG(danceability), 6) AS avg_danceability,
  SUM(award_count) AS sum_award_count, COUNT(*) FILTER (WHERE is_grammy_winner) AS winner_rows,
  string_agg(DISTINCT batch_id, ',') AS batch_ids FROM fact_music_performance;"

echo "== Waiting for the Airflow API"
until af curl -sf http://localhost:8080/api/v2/version >/dev/null 2>&1; do sleep 3; done

echo "== Cleaning previous test runs and evidence"
for r in test_a_success test_c_safe_rerun test_b_controlled_failure test_d_transient_retry; do
  api_delete_run "$r" >/dev/null
  rm -rf "$EV/runs/$r" "data/staging/$r"
done
rm -rf "$EV/test_a_success" "$EV/test_b_controlled_failure" "$EV/test_c_safe_rerun" "$EV/test_d_selective_retry"
mkdir -p "$EV/test_a_success" "$EV/test_b_controlled_failure" "$EV/test_c_safe_rerun" "$EV/test_d_selective_retry"

echo "== Rebuilding the Data Warehouse (sql/dw_reset.sql; load_dw recreates it)"
psql -d dw_music_analytics -q -f /sql/dw_reset.sql

# ---------------- Test A ----------------
echo "== Test A: successful run"
trigger_and_wait test_a_success
task_states test_a_success > "$EV/test_a_success/task_states.txt"
psql -d dw_music_analytics -c "$DW_SNAPSHOT" > "$EV/test_a_success/dw_after_run.txt"

# ---------------- Test C ----------------
echo "== Test C: safe rerun with the same input batch"
psql -d dw_music_analytics -c "$DW_SNAPSHOT" > "$EV/test_c_safe_rerun/dw_before_rerun.txt"
trigger_and_wait test_c_safe_rerun
task_states test_c_safe_rerun > "$EV/test_c_safe_rerun/task_states.txt"
psql -d dw_music_analytics -c "$DW_SNAPSHOT" > "$EV/test_c_safe_rerun/dw_after_rerun.txt"

# ---------------- Test B ----------------
echo "== Test B: controlled Critical failure (DQ-RAW-GRM-01)"
INJECT="INSERT INTO grammy_awards (year, title, category, nominee, artist, winner)
        VALUES (1800, 'Test B injected record', 'Record Of The Year', 'Test B Invalid Year', 'Test B', TRUE)
        RETURNING id, year, nominee;"
{ echo "-- $(date -u +%FT%TZ) injected into source_music_db.grammy_awards to violate DQ-RAW-GRM-01 [Critical]";
  echo "$INJECT"; psql -d source_music_db -c "$INJECT"; } > "$EV/test_b_controlled_failure/injection.txt"
trigger_and_wait test_b_controlled_failure
task_states test_b_controlled_failure > "$EV/test_b_controlled_failure/task_states.txt"
psql -d dw_music_analytics -c "$DW_SNAPSHOT" > "$EV/test_b_controlled_failure/dw_after_failed_run.txt"
{ echo "-- $(date -u +%FT%TZ) cleanup: the source again mirrors the provided CSV";
  psql -d source_music_db -c "DELETE FROM grammy_awards WHERE year = 1800 RETURNING id, year;";
  psql -d source_music_db -c "SELECT COUNT(*) AS rows_after_cleanup FROM grammy_awards;"; } > "$EV/test_b_controlled_failure/cleanup.txt"

# ---------------- Test D ----------------
echo "== Test D: transient source outage -> selective retry of extract_grammys"
LOG="$EV/test_d_selective_retry/procedure.txt"
{ echo "== $(date -u +%FT%TZ) source_music_db stops accepting new connections (simulated outage)";
  psql -d postgres -c "ALTER DATABASE source_music_db ALLOW_CONNECTIONS false;"; } > "$LOG"
af airflow dags trigger "$DAG" --run-id test_d_transient_retry >/dev/null 2>&1
for _ in $(seq 1 60); do
  task_states test_d_transient_retry | grep extract_grammys | grep -q up_for_retry && break
  sleep 2
done
{ echo "== $(date -u +%FT%TZ) extract_grammys attempt 1 failed -> up_for_retry; connections restored";
  psql -d postgres -c "ALTER DATABASE source_music_db ALLOW_CONNECTIONS true;"; } >> "$LOG"
until run_state test_d_transient_retry | grep -qE '^(success|failed)'; do sleep 5; done
echo "== $(date -u +%FT%TZ) DAG run state: $(run_state test_d_transient_retry)" >> "$LOG"
echo "    test_d_transient_retry -> $(run_state test_d_transient_retry)"
task_states test_d_transient_retry > "$EV/test_d_selective_retry/task_states.txt"
psql -d airflow_db -c "SELECT task_id, try_number, state, start_date, end_date FROM task_instance_history
  WHERE run_id='test_d_transient_retry' AND task_id='extract_grammys'
  UNION ALL SELECT task_id, try_number, state, start_date, end_date FROM task_instance
  WHERE run_id='test_d_transient_retry' AND task_id='extract_grammys' ORDER BY 2;" \
  > "$EV/test_d_selective_retry/try_history.txt"

echo "== Exporting readable task logs"
af python /opt/airflow/scripts/export_task_logs.py test_a_success /opt/airflow/$EV/test_a_success/logs >/dev/null
af python /opt/airflow/scripts/export_task_logs.py test_b_controlled_failure /opt/airflow/$EV/test_b_controlled_failure/logs >/dev/null
af python /opt/airflow/scripts/export_task_logs.py test_c_safe_rerun /opt/airflow/$EV/test_c_safe_rerun/logs load_dw >/dev/null
af python /opt/airflow/scripts/export_task_logs.py test_d_transient_retry /opt/airflow/$EV/test_d_selective_retry/logs extract_grammys >/dev/null

echo "== Done. Evidence written under $EV/"
