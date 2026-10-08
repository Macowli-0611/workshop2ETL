#!/usr/bin/env python3
"""
Operational Source Seeding & Reconciliation Script: Grammy Awards
-----------------------------------------------------------------
This script loads the initial provided `the_grammy_awards.csv` dataset into
the relational PostgreSQL database (table `grammy_awards`).

ENGINEERING PRINCIPLE (Section 4.3 & 6.2 of the Brief):
Populating this relational database prepares the operational extraction source.
It is NOT the final ETL load into the analytical Data Warehouse.
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
    print("[*] Initiating seeding of Grammy Awards operational source...")
    print(f"[*] Connecting to PostgreSQL: {DB_HOST}:{DB_PORT}/{DB_NAME} (User: {DB_USER})")

    if not os.path.exists(CSV_PATH):
        print(f"[!] ERROR: Source CSV file not found at: {CSV_PATH}")
        sys.exit(1)

    # 1. Read raw CSV and record baseline metrics
    df_raw = pd.read_csv(CSV_PATH)
    total_csv_rows = len(df_raw)
    print(f"[*] CSV successfully read. Total rows in file: {total_csv_rows}")

    # 2. Connect to PostgreSQL and execute DDL
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            if os.path.exists(SQL_DDL_PATH):
                with open(SQL_DDL_PATH, "r", encoding="utf-8") as f:
                    ddl_sql = f.read()
                conn.execute(text(ddl_sql))
                conn.commit()
                print(f"[+] DDL from {SQL_DDL_PATH} executed successfully.")
            else:
                print(f"[!] Warning: {SQL_DDL_PATH} not found, assuming existing schema.")
    except Exception as e:
        print(f"[!] Error connecting or executing DDL in PostgreSQL: {e}")
        sys.exit(1)

    # 3. Format and sanitize timestamps preserving UTC
    df_to_load = df_raw.copy()
    df_to_load["published_at"] = pd.to_datetime(df_to_load["published_at"], utc=True, errors="coerce")
    df_to_load["updated_at"] = pd.to_datetime(df_to_load["updated_at"], utc=True, errors="coerce")

    # 4. Insert data into grammy_awards table
    try:
        df_to_load.to_sql(
            "grammy_awards",
            con=engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000
        )
        print("[+] Batch insert completed.")
    except Exception as e:
        print(f"[!] Error inserting records into PostgreSQL: {e}")
        sys.exit(1)

    # 5. Row-count reconciliation
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM grammy_awards;"))
        db_count = result.scalar()

    print("\n" + "="*50)
    print("OPERATIONAL SOURCE RECONCILIATION REPORT:")
    print(f" - Rows in raw input CSV: {total_csv_rows}")
    print(f" - Rows in PostgreSQL source table: {db_count}")
    print(f" - Net Discrepancy: {total_csv_rows - db_count}")
    if total_csv_rows == db_count:
        print("RESULT: RECONCILIATION SUCCESSFUL (100% of rows loaded).")
        print("="*50 + "\n")
    else:
        print("WARNING: Reconciliation mismatch detected.")
        print("="*50 + "\n")
        sys.exit(2)

if __name__ == "__main__":
    main()
