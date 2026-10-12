"""
Main Orchestration DAG: dags/reliable_music_pipeline.py
======================================================
Batch Pipeline Orchestration integrating Spotify + Grammy Awards datasets.
Authored for Apache Airflow 3.1.8 using the TaskFlow API (airflow.sdk).

Solution Architecture:
  extract_spotify ──► validate_spotify_raw ──┐
                                             ├──► transform_and_integrate ──► validate_prepared ──► load_dw
  extract_grammys ──► validate_grammys_raw ──┘

Reliability Engineering Principles:
- Task interfaces: only file paths and compact metadata dictionaries travel through XCom.
- Batch context: the Airflow run_id is the batch identifier. Every run writes its staging
  files to data/staging/<run>/ and its evidence (GX results, integration and load reports)
  to docs/evidence/runs/<run>/, so earlier runs are never overwritten.
- Selective retry policy (docs/architecture.md, section 3):
  * Transient operational failures (file I/O, DB connection): bounded retries.
  * Deterministic data-quality / contract failures: retries=0, fail fast and surface evidence.
- max_active_runs=1: two runs never write the same DW snapshot concurrently.
"""

import os
import re
import sys
import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task, get_current_context

# Ensure package visibility for src module within Airflow environment
AIRFLOW_HOME = "/opt/airflow"
if AIRFLOW_HOME not in sys.path:
    sys.path.append(AIRFLOW_HOME)

logger = logging.getLogger("reliable_music_pipeline")

STAGING_ROOT = os.getenv("STAGING_DIR", f"{AIRFLOW_HOME}/data/staging")
EVIDENCE_ROOT = os.getenv("EVIDENCE_DIR", f"{AIRFLOW_HOME}/docs/evidence/runs")

DEFAULT_ARGS = {
    "owner": "data_engineering_team",
    "depends_on_past": False,
    "retries": 0,  # default: no retry unless the task class justifies it
}

# Transient operational class: a new attempt can succeed without changing input or code.
TRANSIENT_RETRY = {"retries": 2, "retry_delay": timedelta(seconds=15), "retry_exponential_backoff": True,
                   "max_retry_delay": timedelta(minutes=2)}


def _batch_context() -> dict:
    """Run identifiers used for folders, logs, evidence and the DW batch_id."""
    ctx = get_current_context()
    run_id = ctx["run_id"]
    safe_run = re.sub(r"[^A-Za-z0-9_.-]", "_", run_id)
    return {
        "dag_id": ctx["dag"].dag_id,
        "run_id": run_id,
        "safe_run_id": safe_run,
        "logical_date": str(ctx.get("logical_date")),
        "task_id": ctx["ti"].task_id,
        "try_number": ctx["ti"].try_number,
        "staging_dir": os.path.join(STAGING_ROOT, safe_run),
        "evidence_dir": os.path.join(EVIDENCE_ROOT, safe_run),
    }


def _log_context(bc: dict) -> None:
    logger.info(f"BATCH CONTEXT | dag={bc['dag_id']} run_id={bc['run_id']} task={bc['task_id']} "
                f"try={bc['try_number']} logical_date={bc['logical_date']}")


def _db_url(db_env: str, default_db: str) -> str:
    user = os.environ["POSTGRES_USER"]
    pwd = os.environ["POSTGRES_PASSWORD"]
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv(db_env, default_db)
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


@dag(
    dag_id="reliable_music_pipeline",
    default_args=DEFAULT_ARGS,
    description="Reliable batch pipeline integrating Spotify + Grammys into a dimensional Data Warehouse",
    schedule=None,  # manually triggered batch
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["etl", "spotify", "grammys", "great_expectations", "dw"],
)
def reliable_music_pipeline():

    # ------------------------------------------------------------------
    # SPOTIFY BRANCH (CSV file source)
    # ------------------------------------------------------------------
    @task(task_id="extract_spotify", **TRANSIENT_RETRY)
    def extract_spotify_task() -> str:
        """Extracts the raw Spotify CSV to a run-scoped staging Parquet (no cleaning)."""
        from src.extract import extract_spotify
        bc = _batch_context()
        _log_context(bc)
        csv_path = os.getenv("SPOTIFY_CSV_PATH", f"{AIRFLOW_HOME}/data/spotify_dataset.csv")
        return extract_spotify(csv_path, os.path.join(bc["staging_dir"], "spotify_raw.parquet"))

    @task(task_id="validate_spotify_raw", retries=0)
    def validate_spotify_raw_task(raw_path: str) -> dict:
        """Raw gate (deterministic, no retry): DQ-RAW-SPT-01..06."""
        from src.validation import validate_spotify_raw
        bc = _batch_context()
        _log_context(bc)
        res = validate_spotify_raw(raw_path, os.path.join(bc["evidence_dir"], "spotify_raw_validation.json"),
                                   batch_context={"run_id": bc["run_id"], "source": "spotify_dataset.csv"})
        return {"dataset": "spotify_raw", "decision": res["gate_decision"], "path": raw_path}

    # ------------------------------------------------------------------
    # GRAMMY BRANCH (relational PostgreSQL source)
    # ------------------------------------------------------------------
    @task(task_id="extract_grammys", **TRANSIENT_RETRY)
    def extract_grammys_task() -> str:
        """Extracts Grammy records from the source database source_music_db.grammy_awards."""
        from src.extract import extract_grammys
        bc = _batch_context()
        _log_context(bc)
        return extract_grammys(_db_url("SOURCE_DB_NAME", "source_music_db"),
                               os.path.join(bc["staging_dir"], "grammys_raw.parquet"))

    @task(task_id="validate_grammys_raw", retries=0)
    def validate_grammys_raw_task(raw_path: str) -> dict:
        """Raw gate (deterministic, no retry): DQ-RAW-GRM-01..04."""
        from src.validation import validate_grammys_raw
        bc = _batch_context()
        _log_context(bc)
        res = validate_grammys_raw(raw_path, os.path.join(bc["evidence_dir"], "grammys_raw_validation.json"),
                                   batch_context={"run_id": bc["run_id"], "source": "source_music_db.grammy_awards"})
        return {"dataset": "grammys_raw", "decision": res["gate_decision"], "path": raw_path}

    # ------------------------------------------------------------------
    # CONVERGENCE: TRANSFORMATION & INTEGRATION (runs only if both raw gates succeed)
    # ------------------------------------------------------------------
    @task(task_id="transform_and_integrate", retries=0)
    def transform_and_integrate_task(spotify_val: dict, grammys_val: dict) -> str:
        """Cleaning, harmonization and integration contract (deterministic, no retry)."""
        from src.transform import transform_and_integrate
        bc = _batch_context()
        _log_context(bc)
        return transform_and_integrate(
            spotify_val["path"], grammys_val["path"],
            os.path.join(bc["staging_dir"], "prepared_music_data.parquet"),
            report_path=os.path.join(bc["evidence_dir"], "integration_report.json"),
        )

    # ------------------------------------------------------------------
    # PREPARED DATA VALIDATION GATE
    # ------------------------------------------------------------------
    @task(task_id="validate_prepared", retries=0)
    def validate_prepared_task(prep_path: str) -> dict:
        """Prepared gate (deterministic, no retry): DQ-PREP-INT-01..08. Gates load_dw."""
        from src.validation import validate_prepared
        bc = _batch_context()
        _log_context(bc)
        res = validate_prepared(prep_path, os.path.join(bc["evidence_dir"], "prepared_validation.json"),
                                batch_context={"run_id": bc["run_id"]})
        return {"dataset": "prepared_music", "decision": res["gate_decision"], "path": prep_path}

    # ------------------------------------------------------------------
    # DIMENSIONAL LOAD (single transaction, idempotent)
    # ------------------------------------------------------------------
    @task(task_id="load_dw", retries=1, retry_delay=timedelta(seconds=30))
    def load_dw_task(prep_val: dict) -> dict:
        """Loads the star schema; batch_id = Airflow run_id. One retry for transient DB errors."""
        from src.load import load_data_warehouse
        bc = _batch_context()
        _log_context(bc)
        return load_data_warehouse(
            prep_val["path"], _db_url("DW_DB_NAME", "dw_music_analytics"),
            batch_id=bc["run_id"][:100],
            report_path=os.path.join(bc["evidence_dir"], "load_report.json"),
        )

    # ------------------------------------------------------------------
    # DEPENDENCIES
    # ------------------------------------------------------------------
    s_val = validate_spotify_raw_task(extract_spotify_task())
    g_val = validate_grammys_raw_task(extract_grammys_task())
    prep_val = validate_prepared_task(transform_and_integrate_task(s_val, g_val))
    load_dw_task(prep_val)


pipeline = reliable_music_pipeline()
