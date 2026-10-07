"""
Módulo de Extracción de Datos: src/extract.py
--------------------------------------------
Maneja la extracción independiente de las dos fuentes heterogéneas:
1. Spotify Dataset (desde archivo CSV).
2. Grammy Awards (desde la base de datos relacional PostgreSQL).

Principio de ingeniería:
La extracción no aplica limpieza prematura para no ocultar problemas de calidad
a la compuerta de validación raw.
"""

import os
import logging
import pandas as pd
from sqlalchemy import create_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ETL_Extract")

def extract_spotify(csv_path: str, output_path: str) -> str:
    """
    Extrae los datos crudos de Spotify desde el archivo CSV provisto.
    Guarda el resultado en almacenamiento intermedio (Parquet) y retorna su ruta.
    """
    logger.info(f"Iniciando extracción de Spotify desde: {csv_path}")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Archivo de Spotify no encontrado en la ruta: {csv_path}")

    # Lectura cruda sin alteraciones para permitir que GX evalúe el estado real
    df_spotify = pd.read_csv(csv_path)
    total_rows = len(df_spotify)
    logger.info(f"Spotify extraído con éxito: {total_rows:,} registros, {df_spotify.shape[1]} columnas.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_spotify.to_parquet(output_path, index=False)
    logger.info(f"Dataset crudo de Spotify guardado en staging: {output_path}")

    return output_path

def extract_grammys(db_url: str, output_path: str) -> str:
    """
    Extrae los datos crudos de Grammy Awards desde la base de datos relacional PostgreSQL.
    Cumple con el requerimiento de la Sección 4.3 del Brief.
    """
    logger.info(f"Iniciando extracción de Grammy Awards desde base de datos relacional.")
    engine = create_engine(db_url)

    query = """
        SELECT 
            year,
            title,
            published_at,
            updated_at,
            category,
            nominee,
            artist,
            workers,
            img,
            winner
        FROM grammy_awards
        ORDER BY year ASC, category ASC;
    """

    with engine.connect() as conn:
        df_grammys = pd.read_sql(query, conn)

    total_rows = len(df_grammys)
    logger.info(f"Grammy Awards extraídos de PostgreSQL con éxito: {total_rows:,} registros.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_grammys.to_parquet(output_path, index=False)
    logger.info(f"Dataset crudo de Grammys guardado en staging: {output_path}")

    return output_path

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_pass = os.getenv("POSTGRES_PASSWORD", "postgres_secure_password")
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("SOURCE_DB_NAME", "source_music_db")
    db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    out_s = extract_spotify("spotify_dataset.csv", "data/staging/spotify_raw.parquet")
    out_g = extract_grammys(db_url, "data/staging/grammys_raw.parquet")
    print(f"Archivos de staging generados:\n- {out_s}\n- {out_g}")
