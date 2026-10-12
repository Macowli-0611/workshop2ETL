# Alternative BI: Tableau Desktop on the same Data Warehouse

Alternative to the main Looker Studio dashboard (for example, for an offline demo). Tableau is in the brief's approved list, runs on macOS and Windows, and is free for students through the *Tableau for Students* program. The KPIs are already defined as views in the DW, so the dashboard only needs the views; no logic lives in the BI tool.

1. Start the stack and load the DW (`docker compose up -d`, then trigger `reliable_music_pipeline` or run `bash scripts/run_reliability_tests.sh`).
2. Tableau Desktop → **Connect → To a Server → PostgreSQL**
   - Server `localhost`, Port `5432`, Database `dw_music_analytics`
   - Username / password: the values of `POSTGRES_USER` / `POSTGRES_PASSWORD` in your `.env`
   - Require SSL: off (local only).
3. In *Table*, drag these views (schema `public`):
   - `vw_kpi1_audio_profile` → **KPI-01**: columns `award_status`; Measure Names/Values filtered to `avg_danceability`, `avg_energy`, `avg_valence`, `avg_acousticness` → side-by-side bars. Add a text sheet with `avg_popularity` per status.
   - `vw_kpi2_genre_uplift` → **KPI-02**: filter `n_winner_tracks >= 5`; rows `genre_name`, columns `popularity_uplift`, sort descending; tooltip `n_winner_tracks`.
   - `vw_kpi3_decade_trends` → **KPI-03**: columns `decade` (discrete), rows `pct_explicit` and `pct_collaboration` (dual line).
4. Combine the three sheets in one dashboard titled "Workshop-2 · Spotify x Grammy KPIs (DW)". Export a screenshot to `docs/evidence/kpi/tableau_dashboard.png` and save the workbook as `docs/evidence/kpi/workshop2_kpis.twb` (a `.twb` stores only the connection and layout, not the password).

The views are the contract: if a KPI changes, change the view in `sql/dw_schema.sql` and Looker Studio, Metabase and Tableau all pick it up.
