#!/usr/bin/env python3
"""
BI publication: copies the Data Warehouse to a cloud PostgreSQL so Looker Studio can query it.

Looker Studio connects from Google's servers and cannot reach the local PostgreSQL
(bound to 127.0.0.1). This script publishes a read-only copy of dw_music_analytics:

  1. applies sql/dw_schema.sql on the target (same tables, constraints and KPI views)
  2. in ONE transaction: TRUNCATE the star schema, then COPY every dimension and the fact
     table from the local DW (COPY streams, no intermediate files), and realign sequences
  3. creates/updates a LOGIN role with SELECT on the analytical views only (bi_reader)
  4. reconciles row counts and KPI values local vs target and writes
     docs/evidence/bi_publication/publish_report.json (no credentials)

The local DW stays the system of record; the target is overwritten on every publish,
so publishing is idempotent and a failure rolls back to the previous published copy.

Environment (.env):
  BI_DW_URL           owner connection string of the target, e.g.
                      postgresql://owner:***@ep-xxx.region.aws.neon.tech/dw_music_analytics?sslmode=require
  BI_READER_PASSWORD  password for the read-only role used by Looker Studio
  BI_READER_USER      optional, default "bi_reader"

Run after a successful load_dw:
  docker compose exec airflow python /opt/airflow/scripts/publish_dw.py
"""

import io
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import psycopg2
from psycopg2 import sql

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_SQL = os.path.join(ROOT, "sql", "dw_schema.sql")
REPORT = os.path.join(ROOT, "docs", "evidence", "bi_publication", "publish_report.json")

# Load order respects foreign keys; columns exclude nothing (exact copy).
TABLES = ["dim_artist", "dim_track", "dim_genre", "dim_time", "dim_grammy_category", "fact_music_performance"]
SERIALS = {"dim_artist": "artist_sk", "dim_track": "track_sk", "dim_genre": "genre_sk",
           "dim_grammy_category": "category_sk", "fact_music_performance": "fact_id"}
VIEWS = ["vw_kpi_scorecards", "vw_kpi1_audio_profile", "vw_kpi1_audio_profile_long",
         "vw_kpi2_genre_uplift", "vw_kpi2_genre_uplift_comparable", "vw_kpi3_decade_trends", "vw_track_profile"]
CHECKS = {
    "fact_rows": "SELECT COUNT(*) FROM fact_music_performance",
    "sum_popularity": "SELECT SUM(popularity) FROM fact_music_performance",
    "winner_rows": "SELECT COUNT(*) FROM fact_music_performance WHERE is_grammy_winner",
    "kpi1_popularity_uplift": "SELECT kpi1_popularity_uplift FROM vw_kpi_scorecards",
    "kpi3_explicit_latest_decade": "SELECT kpi3_explicit_latest_decade FROM vw_kpi_scorecards",
    "kpi2_comparable_genres": "SELECT COUNT(*) FROM vw_kpi2_genre_uplift_comparable",
}


def local_dsn() -> str:
    return "postgresql://{u}:{p}@{h}:{port}/{db}".format(
        u=os.environ["POSTGRES_USER"], p=os.environ["POSTGRES_PASSWORD"],
        h=os.getenv("POSTGRES_HOST", "localhost"), port=os.getenv("POSTGRES_PORT", "5432"),
        db=os.getenv("DW_DB_NAME", "dw_music_analytics"))


def snapshot(conn) -> dict:
    with conn.cursor() as cur:
        out = {}
        for k, q in CHECKS.items():
            cur.execute(q)
            v = cur.fetchone()[0]
            out[k] = float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, int) else v
        return out


def main():
    target = os.getenv("BI_DW_URL")
    reader_pwd = os.getenv("BI_READER_PASSWORD")
    reader = os.getenv("BI_READER_USER", "bi_reader")
    if not target or not reader_pwd:
        sys.exit("Set BI_DW_URL and BI_READER_PASSWORD in .env (see .env.example).")

    src = psycopg2.connect(local_dsn())
    dst = psycopg2.connect(target)
    print(f"[*] Publishing local DW -> {urlparse(target).hostname}")

    with open(SCHEMA_SQL, encoding="utf-8") as f:
        ddl = f.read()
    with dst, dst.cursor() as cur:  # schema first (idempotent DDL)
        cur.execute(ddl)

    copied = {}
    try:
        with dst.cursor() as cur:  # one transaction for the data swap
            cur.execute("TRUNCATE " + ", ".join(reversed(TABLES)) + " CASCADE")
            for t in TABLES:
                buf = io.StringIO()
                with src.cursor() as s:
                    s.copy_expert(sql.SQL("COPY {} TO STDOUT WITH CSV").format(sql.Identifier(t)), buf)
                buf.seek(0)
                cur.copy_expert(sql.SQL("COPY {} FROM STDIN WITH CSV").format(sql.Identifier(t)), buf)
                copied[t] = cur.rowcount
                if t in SERIALS:
                    cur.execute(sql.SQL("SELECT setval(pg_get_serial_sequence(%s, %s), "
                                        "GREATEST((SELECT COALESCE(MAX({c}), 0) FROM {t}), 1))").format(
                        c=sql.Identifier(SERIALS[t]), t=sql.Identifier(t)), (t, SERIALS[t]))
                print(f"[+] {t}: {copied[t]:,} rows")
        dst.commit()
    except Exception:
        dst.rollback()
        raise

    with dst, dst.cursor() as cur:  # read-only role for Looker Studio: views only
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (reader,))
        verb = "ALTER" if cur.fetchone() else "CREATE"
        cur.execute(sql.SQL(verb + " ROLE {} WITH LOGIN PASSWORD %s").format(sql.Identifier(reader)), (reader_pwd,))
        cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(reader)))
        cur.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(sql.Identifier(reader)))
        for v in VIEWS:
            cur.execute(sql.SQL("GRANT SELECT ON {} TO {}").format(sql.Identifier(v), sql.Identifier(reader)))
        print(f"[+] role {reader}: SELECT on {len(VIEWS)} views only")

    local, published = snapshot(src), snapshot(dst)
    reconciled = local == published
    report = {
        "published_at": datetime.now(timezone.utc).isoformat(),
        "source": "local dw_music_analytics",
        "target": "cloud PostgreSQL (host omitted)",
        "rows_copied": copied,
        "read_only_role": reader,
        "views_granted": VIEWS,
        "local": local,
        "published": published,
        "reconciled": reconciled,
    }
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"[{'+' if reconciled else '!'}] reconciliation local == published: {reconciled}")
    print(f"[+] report: {os.path.relpath(REPORT, ROOT)}")
    if not reconciled:
        sys.exit(2)


if __name__ == "__main__":
    main()
