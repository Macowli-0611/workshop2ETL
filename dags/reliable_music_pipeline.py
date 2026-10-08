"""
Main Orchestration DAG: dags/reliable_music_pipeline.py
======================================================
Batch Pipeline Orchestration integrating Spotify + Grammy Awards datasets.
Authored for Apache Airflow 3.1.8 using the official TaskFlow API (airflow.sdk).

Solution Architecture:
  extract_spotify ──► validate_spotify_raw ──┐
                                             ├──► transform_and_integrate ──► validate_prepared ──► load_dw
  extract_grammys ──► validate_grammys_raw ──┘

Reliability Engineering Principles:
- XCom Transport: Only compact file path references and audit metadata dictionaries are communicated.
- Selective Retry Policies:
  * Transient operational disruptions (I/O, DB socket): Bounded retries with backoff (retries=2, retry_delay=10s).
  * Deterministic data quality violations (GX): Zero retries (retries=0) to stop pipeline immediately and surface evidence.
"""

import os
import sys
from datetime import datetime, timedelta

# Mandatory import according to Section 1 & Section 5 of the Workshop Brief
from airflow.sdk import dag, task

# Ensure package visibility for src module within Airflow environment
sys.path.append("/opt/airflow")

DEFAULT_ARGS = {
    "owner": "data_engineering_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
}

@dag(
    dag_id="reliable_music_pipeline",
    default_args=DEFAULT_ARGS,
    description="Reliable batch pipeline integrating Spotify + Grammys into dimensional Data Warehouse",
    schedule=None,  # Manual trigger / Event-driven batch
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["etl", "spotify", "grammys", "great_expectations", "dw"],
)
def reliable_music_pipeline():

    # ------------------------------------------------------------------
    # SPOTIFY EXTRACTION & RAW VALIDATION BRANCH
    # ------------------------------------------------------------------
    @task(
        task_id="extract_spotify",
        retries=2,
        retry_delay=timedelta(seconds=10),
    )
    def extract_spotify_task() -> str:
        """Extracts raw Spotify catalog from CSV to persistent staging Parquet."""
        from src.extract import extract_spotify
        csv_path = os.getenv("SPOTIFY_CSV_PATH", "/opt/airflow/data/spotify_dataset.csv")
        output_path = "/opt/airflow/data/staging/spotify_raw.parquet"
        return extract_spotify(csv_path, output_path)

    @task(
        task_id="validate_spotify_raw",
        retries=0,  # Deterministic quality gate: no blind retries
    )
    def validate_spotify_raw_task(raw_path: str) -> dict:
        """Raw Validation Gate: Evaluates DQ-RAW-SPT-01 through DQ-RAW-SPT-04."""
        from src.validation import validate_spotify_raw
        report_path = "/opt/airflow/gx/results/spotify_raw_validation.json"
        res = validate_spotify_raw(raw_path, report_path)
        return {"dataset": "spotify_raw", "success": res["success"], "path": raw_path}

    # ------------------------------------------------------------------
    # GRAMMY AWARDS EXTRACTION & RAW VALIDATION BRANCH (Relational Source)
    # ------------------------------------------------------------------
    @task(
        task_id="extract_grammys",
        retries=2,
        retry_delay=timedelta(seconds=10),
    )
    def extract_grammys_task() -> str:
        """Extracts Grammys from relational PostgreSQL database (Section 4.3)."""
        from src.extract import extract_grammys
        user = os.getenv("POSTGRES_USER", "postgres")
        pwd = os.getenv("POSTGRES_PASSWORD", "postgres_secure_password")
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("SOURCE_DB_NAME", "source_music_db")
        db_url = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
        output_path = "/opt/airflow/data/staging/grammys_raw.parquet"
        return extract_grammys(db_url, output_path)

    @task(
        task_id="validate_grammys_raw",
        retries=0,  # Deterministic quality gate: no blind retries
    )
    def validate_grammys_raw_task(raw_path: str) -> dict:
        """Raw Validation Gate: Evaluates DQ-RAW-GRM-01 and DQ-RAW-GRM-02."""
        from src.validation import validate_grammys_raw
        report_path = "/opt/airflow/gx/results/grammys_raw_validation.json"
        res = validate_grammys_raw(raw_path, report_path)
        return {"dataset": "grammys_raw", "success": res["success"], "path": raw_path}

    # ------------------------------------------------------------------
    # CONVERGENCE: TRANSFORMATION & CROSS-SOURCE INTEGRATION
    # ------------------------------------------------------------------
    @task(
        task_id="transform_and_integrate",
        retries=0,  # Deterministic transformation logic
    )
    def transform_and_integrate_task(spotify_val: dict, grammys_val: dict) -> str:
        """Applies justified cleaning, harmonization, and integration contract."""
        from src.transform import transform_and_integrate
        spotify_path = spotify_val["path"]
        grammys_path = grammys_val["path"]
        output_path = "/opt/airflow/data/staging/prepared_music_data.parquet"
        return transform_and_integrate(spotify_path, grammys_path, output_path)

    # ------------------------------------------------------------------
    # PREPARED DATA VALIDATION GATE
    # ------------------------------------------------------------------
    @task(
        task_id="validate_prepared",
        retries=0,  # Deterministic pre-load quality gate
    )
    def validate_prepared_task(prep_path: str) -> dict:
        """Prepared Gate: Verifies dimensional load readiness (DQ-PREP-INT)."""
        from src.validation import validate_prepared
        report_path = "/opt/airflow/gx/results/prepared_validation.json"
        res = validate_prepared(prep_path, report_path)
        return {"dataset": "prepared_music", "success": res["success"], "path": prep_path}

    # ------------------------------------------------------------------
    # DIMENSIONAL LOAD TO DATA WAREHOUSE (IDEMPOTENT SAFE RERUN)
    # ------------------------------------------------------------------
    @task(
        task_id="load_dw",
        retries=1,
        retry_delay=timedelta(seconds=10),
    )
    def load_dw_task(prep_val: dict) -> dict:
        """Populates dw_music_analytics enforcing Safe Rerun idempotency."""
        from src.load import load_data_warehouse
        prep_path = prep_val["path"]
        user = os.getenv("POSTGRES_USER", "postgres")
        pwd = os.getenv("POSTGRES_PASSWORD", "postgres_secure_password")
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("DW_DB_NAME", "dw_music_analytics")
        dw_url = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
        
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_data_warehouse(prep_path, dw_url, batch_id=batch_id)

    # ------------------------------------------------------------------
    # DEPENDENCY ORCHESTRATION GRAPH
    # ------------------------------------------------------------------
    s_raw_path = extract_spotify_task()
    s_val = validate_spotify_raw_task(s_raw_path)

    g_raw_path = extract_grammys_task()
    g_val = validate_grammys_raw_task(g_raw_path)

    # Both raw branches converge into transformation
    prep_path = transform_and_integrate_task(s_val, g_val)

    # Pre-load validation gate
    prep_val = validate_prepared_task(prep_path)

    # Dimensional warehouse load
    load_dw_task(prep_val)

pipeline = reliable_music_pipeline()
