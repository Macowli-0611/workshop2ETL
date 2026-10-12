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
import json
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_USER = os.environ["POSTGRES_USER"]
DB_PASSWORD = os.environ["POSTGRES_PASSWORD"]
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("SOURCE_DB_NAME", "source_music_db")

CSV_PATH = os.getenv("GRAMMY_CSV_PATH", os.path.join(PROJECT_ROOT, "data", "the_grammy_awards.csv"))
SQL_DDL_PATH = os.path.join(PROJECT_ROOT, "sql", "source_setup.sql")
REPORT_PATH = os.getenv("SEED_REPORT_PATH", os.path.join(PROJECT_ROOT, "docs", "evidence", "source_preparation", "seed_report.json"))

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
        db_count = conn.execute(text("SELECT COUNT(*) FROM grammy_awards;")).scalar()
        db_winners = conn.execute(text("SELECT COUNT(*) FROM grammy_awards WHERE winner;")).scalar()
        db_years = conn.execute(text("SELECT MIN(year), MAX(year) FROM grammy_awards;")).one()
        db_null_nominee = conn.execute(text("SELECT COUNT(*) FROM grammy_awards WHERE nominee IS NULL;")).scalar()

    report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "source_file": os.path.basename(CSV_PATH),
        "target": f"{DB_NAME}.grammy_awards",
        "ddl": "sql/source_setup.sql",
        "csv_rows": int(total_csv_rows),
        "db_rows": int(db_count),
        "row_discrepancy": int(total_csv_rows - db_count),
        "csv_winner_true": int(df_raw["winner"].sum()),
        "db_winner_true": int(db_winners),
        "csv_year_range": [int(df_raw["year"].min()), int(df_raw["year"].max())],
        "db_year_range": [int(db_years[0]), int(db_years[1])],
        "csv_null_nominee": int(df_raw["nominee"].isna().sum()),
        "db_null_nominee": int(db_null_nominee),
        "decisions": [
            "Original CSV preserved untouched in data/; values are inserted as-is (no cleaning).",
            "published_at / updated_at parsed to TIMESTAMPTZ (UTC); unparseable values would become NULL.",
            "Surrogate id SERIAL and created_at added by the source DDL; the extraction query does not use them.",
            "Re-running the seed drops and recreates the table, so the source always mirrors the provided CSV.",
        ],
    }
    report["reconciled"] = (report["row_discrepancy"] == 0 and report["csv_winner_true"] == report["db_winner_true"]
                            and report["csv_year_range"] == report["db_year_range"]
                            and report["csv_null_nominee"] == report["db_null_nominee"])
    try:
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[+] Reconciliation report saved to {REPORT_PATH}")
    except OSError as exc:
        print(f"[!] Could not write reconciliation report: {exc}")

    print("\n" + "="*50)
    print("OPERATIONAL SOURCE RECONCILIATION REPORT:")
    print(f" - Rows in raw input CSV: {total_csv_rows}")
    print(f" - Rows in PostgreSQL source table: {db_count}")
    print(f" - Net Discrepancy: {total_csv_rows - db_count}")
    if report["reconciled"]:
        print("RESULT: RECONCILIATION SUCCESSFUL (100% of rows loaded).")
        print("="*50 + "\n")
    else:
        print("WARNING: Reconciliation mismatch detected.")
        print("="*50 + "\n")
        sys.exit(2)

if __name__ == "__main__":
    main()
