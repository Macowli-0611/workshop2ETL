"""
DAG Principal: dags/reliable_music_pipeline.py
==============================================
Orquestación del Batch Pipeline de Integración Spotify + Grammys.
Implementado para Apache Airflow 3.1.8 utilizando la TaskFlow API oficial (airflow.sdk).

Arquitectura del Flujo:
  extract_spotify ──► validate_spotify_raw ──┐
                                             ├──► transform_and_integrate ──► validate_prepared ──► load_dw
  extract_grammys ──► validate_grammys_raw ──┘

Políticas de Confiabilidad:
- XCom Transport: Solo se transmiten rutas de almacenamiento o metadatos compactos.
- Reintentos Selectivos:
  * Fallas operacionales transitorias (I/O, DB): reintentos acotados (retries=2, retry_delay=10s).
  * Fallas de calidad de datos determinísticas (GX): sin reintentos (retries=0) para detener el pipeline de inmediato.
"""

import os
import sys
from datetime import datetime, timedelta

# Importación obligatoria según Sección 1 y 5 del Brief del Taller
from airflow.sdk import dag, task

# Asegurar visibilidad del paquete src en PYTHONPATH
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
    description="Pipeline batch confiable de integración Spotify + Grammys hacia Data Warehouse dimensional",
    schedule=None,  # Disparo manual o por evento
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["etl", "spotify", "grammys", "great_expectations", "dw"],
)
def reliable_music_pipeline():

    # ------------------------------------------------------------------
    # RAMA SPOTIFY
    # ------------------------------------------------------------------
    @task(
        task_id="extract_spotify",
        retries=2,
        retry_delay=timedelta(seconds=10),
    )
    def extract_spotify_task() -> str:
        """Extrae el catálogo de Spotify desde CSV a almacenamiento staging."""
        from src.extract import extract_spotify
        csv_path = os.getenv("SPOTIFY_CSV_PATH", "/opt/airflow/data/spotify_dataset.csv")
        output_path = "/opt/airflow/data/staging/spotify_raw.parquet"
        return extract_spotify(csv_path, output_path)

    @task(
        task_id="validate_spotify_raw",
        retries=0,  # Falla determinística de calidad: sin reintento ciego
    )
    def validate_spotify_raw_task(raw_path: str) -> dict:
        """Compuerta Raw Spotify: valida DQ-RAW-SPT-01 a DQ-RAW-SPT-04."""
        from src.validation import validate_spotify_raw
        report_path = "/opt/airflow/gx/results/spotify_raw_validation.json"
        res = validate_spotify_raw(raw_path, report_path)
        return {"dataset": "spotify_raw", "success": res["success"], "path": raw_path}

    # ------------------------------------------------------------------
    # RAMA GRAMMY AWARDS (Base de Datos Operacional)
    # ------------------------------------------------------------------
    @task(
        task_id="extract_grammys",
        retries=2,
        retry_delay=timedelta(seconds=10),
    )
    def extract_grammys_task() -> str:
        """Extrae Grammys desde la base relacional PostgreSQL (Sección 4.3)."""
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
        retries=0,  # Falla determinística de calidad: sin reintento ciego
    )
    def validate_grammys_raw_task(raw_path: str) -> dict:
        """Compuerta Raw Grammys: valida DQ-RAW-GRM-01 y DQ-RAW-GRM-02."""
        from src.validation import validate_grammys_raw
        report_path = "/opt/airflow/gx/results/grammys_raw_validation.json"
        res = validate_grammys_raw(raw_path, report_path)
        return {"dataset": "grammys_raw", "success": res["success"], "path": raw_path}

    # ------------------------------------------------------------------
    # CONVERGENCIA: TRANSFORMACIÓN E INTEGRACIÓN
    # ------------------------------------------------------------------
    @task(
        task_id="transform_and_integrate",
        retries=0,  # Reglas de negocio determinísticas
    )
    def transform_and_integrate_task(spotify_val: dict, grammys_val: dict) -> str:
        """Aplica limpieza justificada, armonización y contrato de integración."""
        from src.transform import transform_and_integrate
        spotify_path = spotify_val["path"]
        grammys_path = grammys_val["path"]
        output_path = "/opt/airflow/data/staging/prepared_music_data.parquet"
        return transform_and_integrate(spotify_path, grammys_path, output_path)

    # ------------------------------------------------------------------
    # COMPUERTA PREPARED DATA
    # ------------------------------------------------------------------
    @task(
        task_id="validate_prepared",
        retries=0,  # Falla crítica previa al DW
    )
    def validate_prepared_task(prep_path: str) -> dict:
        """Compuerta Prepared: verifica aptitud para carga dimensional (DQ-PREP-INT)."""
        from src.validation import validate_prepared
        report_path = "/opt/airflow/gx/results/prepared_validation.json"
        res = validate_prepared(prep_path, report_path)
        return {"dataset": "prepared_music", "success": res["success"], "path": prep_path}

    # ------------------------------------------------------------------
    # CARGA DIMENSIONAL AL DATA WAREHOUSE (IDEMPOTENTE)
    # ------------------------------------------------------------------
    @task(
        task_id="load_dw",
        retries=1,
        retry_delay=timedelta(seconds=10),
    )
    def load_dw_task(prep_val: dict) -> dict:
        """Carga en PostgreSQL dw_music_analytics garantizando Safe Rerun."""
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
    # DEFINICIÓN DEL FLUJO DE DEPENDENCIAS
    # ------------------------------------------------------------------
    s_raw_path = extract_spotify_task()
    s_val = validate_spotify_raw_task(s_raw_path)

    g_raw_path = extract_grammys_task()
    g_val = validate_grammys_raw_task(g_raw_path)

    # Ambas ramas convergen en la transformación
    prep_path = transform_and_integrate_task(s_val, g_val)

    # Validación antes de carga
    prep_val = validate_prepared_task(prep_path)

    # Carga dimensional final
    load_dw_task(prep_val)

pipeline = reliable_music_pipeline()
