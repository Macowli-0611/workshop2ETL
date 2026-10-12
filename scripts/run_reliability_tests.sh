#!/usr/bin/env bash
# ==============================================================
# Reproduces the reliability tests through Airflow and stores the evidence.
#   Test A  test_a_success              full successful run (DW rebuilt first)
#   Test C  test_c_safe_rerun           same batch again -> no duplicates, same measures
#   Test B  test_b_controlled_failure   invalid year injected in the Grammy source -> raw gate stops
#   Test D  test_d_transient_retry      source DB refuses connections -> extract_grammys retries
#   Test E  test_e_prepared_gate        source artist format changes -> raw gates pass,
#                                       integration breaks, prepared gate blocks load_dw
#
# Usage (from the repository root, stack running):
#   bash scripts/run_reliability_tests.sh          # all tests: A, C, B, D, E
#   bash scripts/run_reliability_tests.sh E        # only the listed tests (A rebuilds the DW)
# Evidence: docs/evidence/runs/<run_id>/ (GX + integration + load JSON)
#           docs/evidence/test_*/      (SQL snapshots, procedures, readable task logs)
# Screenshots afterwards: see README section 16 (scripts/capture_airflow_evidence.py).
# ==============================================================
set -euo pipefail

DAG=reliable_music_pipeline
AF=workshop2_airflow
PG=workshop2_postgres
EV=docs/evidence
TESTS="${*:-A C B D E}"

af()   { docker exec "$AF" "$@"; }
psql() { docker exec "$PG" psql -U "${POSTGRES_USER:-postgres}" "$@"; }
want() { [[ " $TESTS " == *" $1 "* ]]; }

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

# reset <run_id> <evidence folder>: removes a previous run with the same id and its evidence
reset() {
  api_delete_run "$1" >/dev/null
  af rm -rf "/opt/airflow/logs/dag_id=$DAG/run_id=$1"   # Airflow appends to logs of a reused run_id
  rm -rf "$EV/runs/$1" "data/staging/$1"
  mkdir -p "$EV/$2"
  # remove generated artifacts only; the hand-written *_report.md stays
  find "$EV/$2" -mindepth 1 -maxdepth 1 ! -name '*_report.md' -exec rm -rf {} +
}

DW_SNAPSHOT="SELECT COUNT(*) AS fact_rows,
  COUNT(*) - COUNT(DISTINCT (track_sk, genre_sk, time_sk, category_sk)) AS grain_duplicates,
  SUM(popularity) AS sum_popularity, ROUND(AVG(danceability), 6) AS avg_danceability,
  SUM(award_count) AS sum_award_count, COUNT(*) FILTER (WHERE is_grammy_winner) AS winner_rows,
  string_agg(DISTINCT batch_id, ',') AS batch_ids FROM fact_music_performance;"

echo "== Tests selected: $TESTS"
echo "== Waiting for the Airflow API"
until af curl -sf http://localhost:8080/api/v2/version >/dev/null 2>&1; do sleep 3; done

# ---------------- Test A ----------------
if want A; then
  echo "== Test A: successful run (DW rebuilt with sql/dw_reset.sql; load_dw recreates it)"
  reset test_a_success test_a_success
  psql -d dw_music_analytics -q -f /sql/dw_reset.sql
  trigger_and_wait test_a_success
  task_states test_a_success > "$EV/test_a_success/task_states.txt"
  psql -d dw_music_analytics -c "$DW_SNAPSHOT" > "$EV/test_a_success/dw_after_run.txt"
  af python /opt/airflow/scripts/export_task_logs.py test_a_success /opt/airflow/$EV/test_a_success/logs >/dev/null
fi

# ---------------- Test C ----------------
if want C; then
  echo "== Test C: safe rerun with the same input batch"
  reset test_c_safe_rerun test_c_safe_rerun
  psql -d dw_music_analytics -c "$DW_SNAPSHOT" > "$EV/test_c_safe_rerun/dw_before_rerun.txt"
  trigger_and_wait test_c_safe_rerun
  task_states test_c_safe_rerun > "$EV/test_c_safe_rerun/task_states.txt"
  psql -d dw_music_analytics -c "$DW_SNAPSHOT" > "$EV/test_c_safe_rerun/dw_after_rerun.txt"
  af python /opt/airflow/scripts/export_task_logs.py test_c_safe_rerun /opt/airflow/$EV/test_c_safe_rerun/logs load_dw >/dev/null
fi

# ---------------- Test B ----------------
if want B; then
  echo "== Test B: controlled Critical failure at the raw gate (DQ-RAW-GRM-01)"
  reset test_b_controlled_failure test_b_controlled_failure
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
  af python /opt/airflow/scripts/export_task_logs.py test_b_controlled_failure /opt/airflow/$EV/test_b_controlled_failure/logs >/dev/null
fi

# ---------------- Test D ----------------
if want D; then
  echo "== Test D: transient source outage -> selective retry of extract_grammys"
  reset test_d_transient_retry test_d_selective_retry
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
  af python /opt/airflow/scripts/export_task_logs.py test_d_transient_retry /opt/airflow/$EV/test_d_selective_retry/logs extract_grammys >/dev/null
fi

# ---------------- Test E ----------------
if want E; then
  echo "== Test E: source format change -> integration breaks -> prepared gate blocks load_dw (DQ-PREP-INT-07)"
  reset test_e_prepared_gate test_e_prepared_gate
  CHANGE="UPDATE grammy_awards SET artist = artist || ' [credits v2]' WHERE artist IS NOT NULL;"
  { echo "-- $(date -u +%FT%TZ) simulated upstream format change in source_music_db.grammy_awards.artist";
    echo "-- every credit gets a suffix: raw rules (year, nominee, schema, volume) still hold,";
    echo "-- but no (title, primary artist) key can match the Spotify catalog any more.";
    echo "$CHANGE"; psql -d source_music_db -c "$CHANGE";
    psql -d source_music_db -c "SELECT artist FROM grammy_awards WHERE artist IS NOT NULL ORDER BY id LIMIT 3;"; } \
    > "$EV/test_e_prepared_gate/injection.txt"
  psql -d dw_music_analytics -c "$DW_SNAPSHOT" > "$EV/test_e_prepared_gate/dw_before_run.txt"
  trigger_and_wait test_e_prepared_gate
  task_states test_e_prepared_gate > "$EV/test_e_prepared_gate/task_states.txt"
  psql -d dw_music_analytics -c "$DW_SNAPSHOT" > "$EV/test_e_prepared_gate/dw_after_failed_run.txt"
  { echo "-- $(date -u +%FT%TZ) cleanup: remove the suffix so the source mirrors the provided CSV again";
    psql -d source_music_db -c "UPDATE grammy_awards SET artist = left(artist, length(artist) - length(' [credits v2]')) WHERE artist LIKE '% [credits v2]';";
    psql -d source_music_db -c "SELECT COUNT(*) FILTER (WHERE artist LIKE '%[credits v2]') AS suffixed_rows_left, COUNT(*) AS total_rows FROM grammy_awards;"; } \
    > "$EV/test_e_prepared_gate/cleanup.txt"
  af python /opt/airflow/scripts/export_task_logs.py test_e_prepared_gate /opt/airflow/$EV/test_e_prepared_gate/logs \
    validate_grammys_raw transform_and_integrate validate_prepared >/dev/null
fi

echo "== Done. Evidence written under $EV/"
