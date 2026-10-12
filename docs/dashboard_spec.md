# Analytics & BI Dashboard (Section 8.1)

Every output queries the **dimensional Data Warehouse** `dw_music_analytics` (never the CSV files) through four analytical views defined in [`sql/dw_schema.sql`](../sql/dw_schema.sql).

## 1. BI tool and connection

- **Tool:** Metabase (`metabase/metabase:v0.56.9`, service `metabase` in `docker-compose.yaml`). It runs on macOS/Linux/Windows with no license and can be rebuilt from code.
  > The brief lists Power BI, Tableau and Looker Studio, and says other tools need instructor approval. **Approval for Metabase must be requested.** If it is not granted, the same views work in Tableau Desktop, which is in the approved list and runs on macOS; see [bi_tableau_guide.md](bi_tableau_guide.md).
- **Connection:** PostgreSQL · host `postgres` (inside Docker) or `localhost` · port `5432` · database `dw_music_analytics` · credentials from `.env`.
- **Build:** `docker compose exec airflow python /opt/airflow/scripts/setup_metabase.py`. The script completes the Metabase setup, registers the DW, creates 8 native-SQL questions and the dashboard, and enables a local read-only public link. Re-running it rebuilds the dashboard.
- **Screenshot:** [`docs/evidence/kpi/metabase_dashboard.png`](evidence/kpi/metabase_dashboard.png)

## 2. Requirement → DW element → KPI

| Analytical requirement | DW element / query | KPI / Visualization |
| :--- | :--- | :--- |
| RQ-01 Audio profile, winners vs catalog | `vw_kpi1_audio_profile` (built on `vw_track_profile`: one row per distinct track) | **KPI-01** tile "Popularity uplift of Grammy winners" (pts) + grouped bar chart of mean danceability / energy / valence / acousticness by award status + tile "Awarded tracks matched" |
| RQ-02 Popularity uplift by genre | `vw_kpi2_genre_uplift` (fact grain track × genre, filter `n_winner_tracks >= 5`) | **KPI-02** row chart of the top-12 genres by uplift + detail table with sample sizes (winner and catalog track counts) |
| RQ-03 Explicit and collaborations by decade | `vw_kpi3_decade_trends` (distinct awarded tracks × `dim_time.decade`, `dim_track.explicit`, `dim_artist.artist_type`) | **KPI-03** line chart "% explicit" and "% collaborations" per decade + tile "Explicit share of awarded tracks, 2010s" |

## 3. Results (DW after test_a_success / test_c_safe_rerun)

| KPI | Value | Reading |
| :--- | :--- | :--- |
| KPI-01 popularity uplift | **+12.04 pts** (282 awarded tracks vs 89,458 catalog tracks) | Awarded tracks are more popular on Spotify today. They also show higher valence (0.53 vs 0.47), slightly higher energy and danceability, and lower acousticness (0.26 vs 0.33). |
| KPI-02 genre uplift | Largest in soul (+45.6, n=20), jazz (+42.4, n=9), breakbeat (+28.5, n=7), punk (+28.5, n=5), country (+23.6, n=26) | Small samples (n shown) mean that genres with n < 10 should be read with caution. |
| KPI-03 decade trends | Explicit: 0% before the 1990s → 7.3% (1990s) → 14.1% (2000s) → **20.2% (2010s)**. Collaborations: 17–18% (1980s–90s), 2.6% (2000s), **35.7% (2010s)**. | Explicit content among awarded tracks rises steadily; collaborations jump in the 2010s. |

Static copies of the three visualizations, with the exact numbers in CSV, are generated from the same views by `scripts/generate_kpi_charts.py` into [`docs/evidence/kpi/`](evidence/kpi/).

All values are computed on distinct tracks for RQ-01/RQ-03, so a song that appears in several genres counts once. The previous version averaged fact rows, which counted those songs several times; this is why the 2010s explicit share changed from 15.3% to 20.2%.
