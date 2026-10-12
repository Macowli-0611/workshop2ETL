# Analytics & BI Dashboard (Section 8.1)

Every output queries the **dimensional Data Warehouse** `dw_music_analytics` (never the CSV files) through four analytical views defined in [`sql/dw_schema.sql`](../sql/dw_schema.sql).

## 1. BI tool and connection

- **Tool: Looker Studio** (named in the brief). Live report: https://lookerstudio.google.com/reporting/c356ff56-e259-40bf-86e3-083f3924a837
- **Why a published copy:** Looker Studio connects from Google's servers and cannot reach the local PostgreSQL (bound to 127.0.0.1). `scripts/publish_dw.py` copies the star schema and its KPI views to a cloud PostgreSQL (Neon free tier) after each load: schema via `sql/dw_schema.sql`, data via COPY in one transaction, sequences realigned, and row counts and KPI values reconciled local vs cloud ([`publish_report.json`](evidence/bi_publication/publish_report.json)).
- **Least privilege:** Looker Studio logs in as `bi_reader`, a role with `SELECT` on the analytical views only. Querying the tables is denied.
- **Data sources (one per view):** `vw_kpi_scorecards`, `vw_kpi1_audio_profile_long`, `vw_kpi2_genre_uplift_comparable`, `vw_kpi3_decade_trends`. These views have the exact shape each chart needs, because Looker Studio cannot compute across rows (e.g. the uplift).
- **Setup guide:** [bi_looker_studio_guide.md](bi_looker_studio_guide.md) · **Screenshot:** [`docs/evidence/kpi/looker_studio_dashboard.png`](evidence/kpi/looker_studio_dashboard.png)
- **Alternatives on the same views:** a local Metabase dashboard built from code (`scripts/setup_metabase.py`, [`metabase_dashboard.png`](evidence/kpi/metabase_dashboard.png)) for offline demos, and Tableau Desktop ([bi_tableau_guide.md](bi_tableau_guide.md)).

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
