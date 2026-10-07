#!/usr/bin/env python3
"""
Script de Sembrado (Seeding) y Reconciliación de Fuente Operacional: Grammy Awards
---------------------------------------------------------------------------------
Este script toma el archivo original `the_grammy_awards.csv` y lo carga en la
base de datos relacional PostgreSQL (tabla `grammy_awards`).

IMPORTANTE (Sección 4.3 y 6.2 del Brief):
Poblar esta base de datos crea la fuente operacional para la extracción del pipeline.
NO constituye la carga final de ETL al Data Warehouse analítico.
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres_secure_password")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("SOURCE_DB_NAME", "source_music_db")

CSV_PATH = os.getenv("GRAMMY_CSV_PATH", "the_grammy_awards.csv")
SQL_DDL_PATH = "sql/source_setup.sql"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def main():
    print(f"[*] Iniciando sembrado de fuente operacional Grammy Awards...")
    print(f"[*] Conectando a PostgreSQL: {DB_HOST}:{DB_PORT}/{DB_NAME} (Usuario: {DB_USER})")

    if not os.path.exists(CSV_PATH):
        print(f"[!] ERROR: Archivo CSV no encontrado en: {CSV_PATH}")
        sys.exit(1)

    # 1. Leer CSV original y verificar métricas iniciales
    df_raw = pd.read_csv(CSV_PATH)
    total_csv_rows = len(df_raw)
    print(f"[*] CSV leído exitosamente. Total filas en archivo: {total_csv_rows}")

    # 2. Conectar a PostgreSQL
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Ejecutar DDL
            if os.path.exists(SQL_DDL_PATH):
                with open(SQL_DDL_PATH, "r", encoding="utf-8") as f:
                    ddl_sql = f.read()
                conn.execute(text(ddl_sql))
                conn.commit()
                print(f"[+] DDL de {SQL_DDL_PATH} ejecutado exitosamente.")
            else:
                print(f"[!] Advertencia: No se encontró {SQL_DDL_PATH}, asumiendo tabla existente.")
    except Exception as e:
        print(f"[!] Error conectando o ejecutando DDL en PostgreSQL: {e}")
        sys.exit(1)

    # 3. Formatear y preparar para inserción en tabla operacional
    df_to_load = df_raw.copy()
    # Conversión de fechas respetando UTC
    df_to_load["published_at"] = pd.to_datetime(df_to_load["published_at"], utc=True, errors="coerce")
    df_to_load["updated_at"] = pd.to_datetime(df_to_load["updated_at"], utc=True, errors="coerce")

    # 4. Insertar datos en la tabla grammy_awards
    try:
        df_to_load.to_sql(
            "grammy_awards",
            con=engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000
        )
        print(f"[+] Inserción completada.")
    except Exception as e:
        print(f"[!] Error al insertar datos en PostgreSQL: {e}")
        sys.exit(1)

    # 5. Reconciliación de conteo de filas
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM grammy_awards;"))
        db_count = result.scalar()

    print("\n" + "="*50)
    print("REPORTE DE RECONCILIACIÓN DE FUENTE OPERACIONAL:")
    print(f" - Filas en CSV original: {total_csv_rows}")
    print(f" - Filas en BD PostgreSQL (grammy_awards): {db_count}")
    print(f" - Discrepancia: {total_csv_rows - db_count}")
    if total_csv_rows == db_count:
        print("RESULTADO: RECONCILIACIÓN EXITOSA (100% de registros cargados).")
        print("="*50 + "\n")
    else:
        print("ADVERTENCIA: Discrepancia detectada en la reconciliación.")
        print("="*50 + "\n")
        sys.exit(2)

if __name__ == "__main__":
    main()
