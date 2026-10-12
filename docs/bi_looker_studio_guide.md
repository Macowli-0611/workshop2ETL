# BI Dashboard in Looker Studio (on the Data Warehouse)

Looker Studio is one of the BI tools named in the brief. It runs in the browser (any OS) and reads the Data Warehouse through PostgreSQL.

## Why a published copy of the DW

Looker Studio connects from Google's servers, so it cannot reach the local PostgreSQL (bound to `127.0.0.1`). After each successful `load_dw`, `scripts/publish_dw.py` copies the star schema and its KPI views to a cloud PostgreSQL (Neon free tier). Looker Studio then reads that copy with a **read-only role that can only see the analytical views**.

```
local dw_music_analytics ──publish_dw.py (1 transaction, reconciled)──► cloud PostgreSQL (Neon) ──bi_reader, views only──► Looker Studio
```

The local DW stays the system of record. Each publish overwrites the copy atomically and writes `docs/evidence/bi_publication/publish_report.json` (row counts and KPI values, local vs cloud, no credentials).

## 1. Cloud database (once)

1. Create a free project at <https://neon.tech> (PostgreSQL 16 or 17, region close to you).
2. In the Neon console create a database named `dw_music_analytics` (or use the default `neondb`).
3. Copy the **owner** connection string (Dashboard → *Connect*) and paste it into `.env`:
   ```
   BI_DW_URL=postgresql://<owner>:<password>@<endpoint>.neon.tech/dw_music_analytics?sslmode=require
   ```
   `BI_READER_PASSWORD` is already in `.env` (random value); `BI_READER_USER` defaults to `bi_reader`.
4. Apply the variables and publish:
   ```bash
   docker compose up -d airflow
   docker compose exec airflow python /opt/airflow/scripts/publish_dw.py
   ```
   Expected output: 6 tables copied (113,549 fact rows), `role bi_reader: SELECT on 7 views only`, `reconciliation local == published: True`.

## 2. Data sources in Looker Studio

<https://lookerstudio.google.com> → **Create → Data source → PostgreSQL**, with these connection settings:

| Field | Value |
| :--- | :--- |
| Host name | the Neon endpoint host (`ep-…neon.tech`) |
| Port | `5432` |
| Database | `dw_music_analytics` |
| Username / Password | `bi_reader` / value of `BI_READER_PASSWORD` in `.env` |
| Enable SSL | checked. If a server certificate is requested, upload ISRG Root X1 (<https://letsencrypt.org/certs/isrgrootx1.pem>) |

Create **four data sources**, one per view (the role cannot see the raw tables):

| Data source | View | Used by |
| :--- | :--- | :--- |
| `DW · scorecards` | `vw_kpi_scorecards` | KPI tiles |
| `DW · audio profile` | `vw_kpi1_audio_profile_long` | KPI-01 chart |
| `DW · genre uplift` | `vw_kpi2_genre_uplift_comparable` | KPI-02 chart + table |
| `DW · decade trends` | `vw_kpi3_decade_trends` | KPI-03 chart |

## 3. Report layout

Create a report titled **"Workshop-2 · Spotify x Grammy KPIs (DW)"** and add:

| # | Chart type | Data source | Dimension | Metric(s) | Setup |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Scorecard | scorecards | — | `kpi1_popularity_uplift` | Label "KPI-01 · Popularity uplift of Grammy winners (pts)" |
| 2 | Scorecard | scorecards | — | `awarded_tracks` | "Awarded tracks matched in the catalog" |
| 3 | Scorecard | scorecards | — | `kpi3_explicit_latest_decade` | "KPI-03 · Explicit share of awarded tracks, 2010s (%)" |
| 4 | Scorecard | scorecards | — | `catalog_tracks` | "Catalog tracks in the DW" |
| 5 | Column chart | audio profile | `feature`, breakdown `award_status` | `mean_value` (aggregation **Average**) | Data labels on; title "KPI-01 · Audio profile: Grammy winners vs catalog" |
| 6 | Bar chart (horizontal) | genre uplift | `genre_name` | `popularity_uplift` (**Sum**) | Sort by `popularity_uplift` descending, 12 bars; title "KPI-02 · Popularity uplift by genre (≥ 5 awarded tracks)" |
| 7 | Table | genre uplift | `genre_name` | `n_winner_tracks`, `n_catalog_tracks`, `avg_pop_winners`, `avg_pop_catalog`, `popularity_uplift` | Title "KPI-02 · Genre detail with sample sizes" |
| 8 | Line chart | decade trends | `decade` | `pct_explicit`, `pct_collaboration` (**Sum**) | Sort by `decade` ascending, data labels on; title "KPI-03 · Explicit and collaboration share by decade" |

Expected values (same as the DW): uplift **12.04**, **282** awarded tracks, **20.24%** explicit in the 2010s, **89,740** catalog tracks; soul +45.6 (n=20) leads KPI-02.

## 4. Share and capture

**Share → Manage access → "Anyone with the link can view"** (the data are public datasets; the link only exposes the report, not the credentials). Then:
- paste the link into the README (section 15) and `docs/dashboard_spec.md`;
- save a screenshot as `docs/evidence/kpi/looker_studio_dashboard.png`.

## Re-publishing after a new batch

```bash
docker compose exec airflow python /opt/airflow/scripts/publish_dw.py
```

Looker Studio refreshes from the views (data freshness default: 12 h; use *Refresh data* in the report to force it).
