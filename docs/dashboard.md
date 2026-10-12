# BI Dashboard (Section 8.1)

Every output queries the **dimensional Data Warehouse** `dw_music_analytics` (never the CSV files) through four analytical views defined in [`sql/dw_schema.sql`](../sql/dw_schema.sql).

## 1. BI tool and connection

- **Tool: Looker Studio** (named in the brief). Live report: https://lookerstudio.google.com/reporting/c356ff56-e259-40bf-86e3-083f3924a837
- **Why a published copy:** Looker Studio connects from Google's servers and cannot reach the local PostgreSQL (bound to 127.0.0.1). `scripts/publish_dw.py` copies the star schema and its KPI views to a cloud PostgreSQL (Neon free tier) after each load: schema via `sql/dw_schema.sql`, data via COPY in one transaction, sequences realigned, and row counts and KPI values reconciled local vs cloud ([`publish_report.json`](evidence/bi_publication/publish_report.json)).
- **Least privilege:** Looker Studio logs in as `bi_reader`, a role with `SELECT` on the analytical views only. Querying the tables is denied.
- **Data sources (one per view):** `vw_kpi_scorecards`, `vw_kpi1_audio_profile_long`, `vw_kpi2_genre_uplift_comparable`, `vw_kpi3_decade_trends`. These views have the exact shape each chart needs, because Looker Studio cannot compute across rows (e.g. the uplift).
- **Setup guide:** [section 4](#4-setup-guide-looker-studio) · **Screenshot:** [`docs/evidence/kpi/looker_studio_dashboard.png`](evidence/kpi/looker_studio_dashboard.png)
- **Alternative on the same views:** a local Metabase dashboard built from code (`scripts/setup_metabase.py`, [`metabase_dashboard.png`](evidence/kpi/metabase_dashboard.png)) for offline demos.

## 2. Requirement → DW element → KPI

| Analytical requirement | DW element / query | KPI / Visualization |
| :--- | :--- | :--- |
| RQ-01 Audio profile, winners vs catalog | `vw_kpi1_audio_profile` (built on `vw_track_profile`: one row per distinct track) | **KPI-01** scorecard "Popularity uplift" (pts) + grouped columns of mean danceability / energy / valence / acousticness by award status + scorecard "Awarded tracks matched" |
| RQ-02 Popularity uplift by genre | `vw_kpi2_genre_uplift` (fact grain track × genre, filter `n_winner_tracks >= 5`) | **KPI-02** bubble scatter (catalog vs winners popularity per genre, bubble size = awarded tracks) + heat-map table with sample sizes, sorted by uplift |
| RQ-03 Explicit and collaborations by decade | `vw_kpi3_decade_trends` (distinct awarded tracks × `dim_time.decade`, `dim_track.explicit`, `dim_artist.artist_type`) | **KPI-03** combo chart: awarded tracks per decade (columns) + "% explicit" and "% collaborations" (lines) + scorecard "Explicit share, 2010s" |

## 3. Results (DW after test_a_success / test_c_safe_rerun)

| KPI | Value | Reading |
| :--- | :--- | :--- |
| KPI-01 popularity uplift | **+12.04 pts** (282 awarded tracks vs 89,458 catalog tracks) | Awarded tracks are more popular on Spotify today. They also show higher valence (0.53 vs 0.47), slightly higher energy and danceability, and lower acousticness (0.26 vs 0.33). |
| KPI-02 genre uplift | Largest in soul (+45.6, n=20), jazz (+42.4, n=9), breakbeat (+28.5, n=7), punk (+28.5, n=5), country (+23.6, n=26) | Small samples (n shown) mean that genres with n < 10 should be read with caution. |
| KPI-03 decade trends | Explicit: 0% before the 1990s → 7.3% (1990s) → 14.1% (2000s) → **20.2% (2010s)**. Collaborations: 17–18% (1980s–90s), 2.6% (2000s), **35.7% (2010s)**. | Explicit content among awarded tracks rises steadily; collaborations jump in the 2010s. |

Static copies of the three visualizations, with the exact numbers in CSV, are generated from the same views by `scripts/generate_kpi_charts.py` into [`docs/evidence/kpi/`](evidence/kpi/).

All values are computed on distinct tracks for RQ-01/RQ-03, so a song that appears in several genres counts once. The previous version averaged fact rows, which counted those songs several times; this is why the 2010s explicit share changed from 15.3% to 20.2%.

## 4. Setup guide: Looker Studio

Looker Studio is one of the BI tools named in the brief. It runs in the browser (any OS) and reads the Data Warehouse through PostgreSQL.

### 4.1 Why a published copy of the DW

Looker Studio connects from Google's servers, so it cannot reach the local PostgreSQL (bound to `127.0.0.1`). After each successful `load_dw`, `scripts/publish_dw.py` copies the star schema and its KPI views to a cloud PostgreSQL (Neon free tier). Looker Studio then reads that copy with a **read-only role that can only see the analytical views**.

```
local dw_music_analytics ──publish_dw.py (1 transaction, reconciled)──► cloud PostgreSQL (Neon) ──bi_reader, views only──► Looker Studio
```

The local DW stays the system of record. Each publish overwrites the copy atomically and writes `docs/evidence/bi_publication/publish_report.json` (row counts and KPI values, local vs cloud, no credentials).

### 4.2 Cloud database (once)

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

### 4.3 Data sources in Looker Studio

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

### 4.4 Report layout

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

### 4.5 Share and capture

**Share → Manage access → "Anyone with the link can view"** (the data are public datasets; the link only exposes the report, not the credentials). Then:
- paste the link into the README (section 15) and `docs/dashboard.md`;
- save a screenshot as `docs/evidence/kpi/looker_studio_dashboard.png`.

### 4.6 Re-publishing after a new batch

```bash
docker compose exec airflow python /opt/airflow/scripts/publish_dw.py
```

Looker Studio refreshes from the views (data freshness default: 12 h; use *Refresh data* in the report to force it).
