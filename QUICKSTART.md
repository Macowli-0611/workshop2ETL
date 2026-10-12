# Quickstart — from zero to a running pipeline and dashboard

Step-by-step guide to get everything ready: environment, pipeline runs, reliability tests, dashboard and the live demo. Every command is run from the repository root.

**Live dashboard (Looker Studio):** https://lookerstudio.google.com/reporting/c356ff56-e259-40bf-86e3-083f3924a837
**Repository:** https://github.com/Macowli-0611/workshop2ETL

---

## 0. Prerequisites

| Tool | Notes |
| :--- | :--- |
| Docker Desktop (Compose v2) | Start it and wait until it says *Running*. Allocate at least 4 GB of RAM. |
| Git | To clone the repository. |
| A browser | Airflow UI, Metabase and Looker Studio. |

Nothing else is installed on the host: Python, Airflow, Great Expectations and PostgreSQL all run in containers.

## 1. Get the code and configure `.env`

```bash
git clone https://github.com/Macowli-0611/workshop2ETL.git
cd workshop2ETL
cp .env.example .env
```

Edit `.env`:

| Variable | What to put |
| :--- | :--- |
| `POSTGRES_PASSWORD` | any strong password (local database) |
| `MB_ADMIN_PASSWORD` | any strong password (local Metabase admin) |
| `AIRFLOW_PORT`, `METABASE_PORT` | keep `8080` / `3000`, or change them if those ports are busy on your machine |
| `BI_DW_URL`, `BI_READER_PASSWORD` | only for the Looker Studio publication (step 6) |

`.env` is git-ignored: credentials never leave your machine.

## 2. Start the stack

```bash
docker compose up -d --build
```

The first build takes a few minutes. Docker starts, in order:

1. `postgres`: creates the databases `source_music_db`, `dw_music_analytics`, `airflow_db`, `metabase_db`
2. `airflow-init`: migrates the Airflow metadata database
3. `source-seed`: loads the Grammy CSV into `source_music_db.grammy_awards` and reconciles it (4,810 = 4,810 rows → `docs/evidence/source_preparation/seed_report.json`)
4. `airflow`: Airflow 3.1.8 (API server, scheduler, DAG processor, triggerer)
5. `metabase`: local BI tool

Check that everything is up:

```bash
docker compose ps
docker compose logs source-seed | tail -5          # must say RECONCILIATION SUCCESSFUL
```

## 3. Open Airflow and run the pipeline

Open `http://localhost:8080` (or your `AIRFLOW_PORT`). There is no login screen in this local setup. Find the DAG **`reliable_music_pipeline`**.

Run it from the UI (**Trigger** button) or from the terminal:

```bash
docker compose exec airflow airflow dags trigger reliable_music_pipeline
```

In about 40 seconds the Grid view shows **7 green tasks**. The first run also creates the Data Warehouse schema.

## 4. Reproduce the reliability tests (A–E)

```bash
bash scripts/run_reliability_tests.sh          # all tests, about 8 minutes
bash scripts/run_reliability_tests.sh B        # or only some of them: A C B D E
```

| Test | What it shows | Expected result |
| :--- | :--- | :--- |
| A | clean run (DW rebuilt first) | 7/7 success, 113,549 rows loaded |
| C | same batch again | 0 inserted, 113,549 updated, 0 duplicates |
| B | year 1800 injected in the source DB | raw gate fails, 3 tasks `upstream_failed`, DW unchanged |
| D | source DB refuses connections for a moment | `extract_grammys` try 1 fails, try 2 succeeds |
| E | artist credits change format at the source | raw gates pass, prepared gate fails, load blocked |

Evidence is written to `docs/evidence/` (per-run JSON in `runs/`, reports, logs). The script cleans up every change it makes to the source database.

## 5. Optional: notebook, KPI charts, screenshots

```bash
# Re-execute the profiling notebook (outputs saved in place)
docker compose exec -w /opt/airflow/notebooks airflow jupyter nbconvert --to notebook --execute --inplace data_profiling.ipynb

# Static KPI charts + CSV from the DW views
docker compose exec airflow python /opt/airflow/scripts/generate_kpi_charts.py

# Screenshots of Airflow, Metabase and Looker Studio (official Playwright image)
docker run --rm --network workshop2etl_workshop2_net -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright/python:v1.47.0-jammy \
  bash -c "pip install -q playwright==1.47.0 && python scripts/capture_airflow_evidence.py"

# Rebuild the defense deck (docs/presentation.html)
python3 scripts/build_presentation.py
```

## 6. Dashboard

### Looker Studio (main dashboard)

Live report: https://lookerstudio.google.com/reporting/c356ff56-e259-40bf-86e3-083f3924a837

Looker Studio cannot reach a database on `localhost`, so the DW is published to a cloud PostgreSQL (Neon). After a new load:

```bash
docker compose up -d airflow                                   # only if you just edited .env
docker compose exec airflow python /opt/airflow/scripts/publish_dw.py
```

Expected output: 6 tables copied, `role bi_reader: SELECT on 7 views only`, `reconciliation local == published: True`. Then use **Refresh data** in the report. To build the report from scratch, follow [`docs/bi_looker_studio_guide.md`](docs/bi_looker_studio_guide.md).

### Metabase (local alternative, works offline)

```bash
docker compose exec airflow python /opt/airflow/scripts/setup_metabase.py
```

Open the *Public URL* it prints (`http://localhost:3000/public/dashboard/...`).

## 7. Defense day checklist

**30 minutes before**

1. Start Docker Desktop, then run `docker compose up -d` in the project folder. Wait about one minute.
2. Open Airflow (`http://localhost:8080` or your `AIRFLOW_PORT`) and check that the DAG is there.
3. Open the Looker Studio report once. The free Neon database sleeps when idle, and the first load takes a few seconds.
4. Open `docs/presentation.html` in the browser. Press **F** for fullscreen and **N** for speaker notes.
5. Keep a terminal open in the project folder with the demo commands below ready to paste.

**Live demo (about 3 minutes)**

```bash
# 1 · Successful run → Grid: 7 green tasks; open the load_dw log
docker compose exec airflow airflow dags trigger reliable_music_pipeline

# 2 · Controlled failure: inject an impossible award year into the SOURCE database
docker compose exec postgres psql -U postgres -d source_music_db -c \
  "INSERT INTO grammy_awards (year, title, category, nominee, artist, winner) VALUES (1800, 'demo', 'Record Of The Year', 'demo', 'demo', TRUE);"
docker compose exec airflow airflow dags trigger reliable_music_pipeline
#    → validate_grammys_raw is red, 3 tasks upstream_failed; open its log: DQ-RAW-GRM-01

# 3 · Fix and rerun: same row count, no duplicates
docker compose exec postgres psql -U postgres -d source_music_db -c "DELETE FROM grammy_awards WHERE year = 1800;"
docker compose exec airflow airflow dags trigger reliable_music_pipeline
docker compose exec postgres psql -U postgres -d dw_music_analytics -c \
  "SELECT COUNT(*) AS fact_rows, SUM(popularity) AS sum_popularity FROM fact_music_performance;"
#    → 113549 | 3783956
```

If something fails live, switch to the deck: slides 11–15 are screenshots of the same runs.

**Rehearse once the day before:** run the three demo steps exactly as above. It confirms that Docker, the ports and the commands work on the machine you will present with, and how long each step takes.

## 8. Troubleshooting

| Problem | Fix |
| :--- | :--- |
| `port is already allocated` | Set another `AIRFLOW_PORT` / `METABASE_PORT` in `.env`, then `docker compose up -d`. |
| The DAG does not appear | Wait 30 s and reload; check `docker compose exec airflow airflow dags list-import-errors`. |
| Looker Studio keeps loading | Neon was asleep: wait 20 s and reload, or run `publish_dw.py` once to wake it up. |
| You want an empty DW | `docker compose exec postgres psql -U postgres -d dw_music_analytics -f /sql/dw_reset.sql`; the next run recreates it. |
| The demo row 1800 was left in the source | `docker compose exec postgres psql -U postgres -d source_music_db -c "DELETE FROM grammy_awards WHERE year = 1800;"` |
| Stop everything | `docker compose down` (keeps data) · `docker compose down -v` (also deletes the databases) |

More detail: [`README.md`](README.md) · design and rationale: [`docs/project_context.md`](docs/project_context.md).
