#!/usr/bin/env python3
"""
Exports Airflow task logs of one DAG run as readable text evidence.

Usage (inside the Airflow container):
    python /opt/airflow/scripts/export_task_logs.py <run_id> <output_dir> [task_id ...]

Reads /opt/airflow/logs/dag_id=<dag>/run_id=<run_id>/task_id=<task>/attempt=<n>.log
(structured JSON lines) and writes <task>_attempt<n>.log with timestamp, level, message
and exception, dropping library noise (progress bars, plugin registration).
"""

import os
import sys
import json
import glob

DAG_ID = "reliable_music_pipeline"
LOG_ROOT = os.getenv("AIRFLOW_LOG_ROOT", "/opt/airflow/logs")
NOISE = ("Calculating Metrics", "Stats instance", "Skipping registering", "DAG bundles loaded",
         "Filling up the DagBag", "Created temporary directory", "Loading '")


def render(path: str) -> str:
    lines = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            event = str(rec.get("event", ""))
            if any(n in event for n in NOISE):
                continue
            line = f"{rec.get('timestamp', '')[:23]} [{str(rec.get('level', '')).upper()}] {event}"
            detail = rec.get("error_detail")
            if detail:
                first = detail[0] if isinstance(detail, list) else detail
                line += f"\n    {first.get('exc_type')}: {first.get('exc_value')}"
            lines.append(line)
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    run_id, out_dir, tasks = sys.argv[1], sys.argv[2], sys.argv[3:]
    run_dir = os.path.join(LOG_ROOT, f"dag_id={DAG_ID}", f"run_id={run_id}")
    os.makedirs(out_dir, exist_ok=True)
    for attempt_log in sorted(glob.glob(os.path.join(run_dir, "task_id=*", "attempt=*.log"))):
        task = attempt_log.split("task_id=")[1].split(os.sep)[0]
        if tasks and task not in tasks:
            continue
        attempt = os.path.basename(attempt_log).replace("attempt=", "").replace(".log", "")
        target = os.path.join(out_dir, f"{task}_attempt{attempt}.log")
        with open(target, "w", encoding="utf-8") as f:
            f.write(render(attempt_log))
        print(f"[+] {target}")


if __name__ == "__main__":
    main()
