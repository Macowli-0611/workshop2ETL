# Analytics & BI Dashboard Specification (Section 8.1)
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Course: ETL (G01) — Faculty of Engineering and Basic Sciences (UAO)*

---

## 1. BI Connection to the Data Warehouse
> **Evaluation Constraint:** *"Direct CSV connections are not accepted as the assessed dashboard solution. The dashboard should answer the analytical requirements using trusted data from the Data Warehouse."*

### Connection Parameters (Power BI / Tableau / Looker Studio):
* **Database Engine:** PostgreSQL Database
* **Server (Host):** `localhost` (or host IP if connecting from remote desktop client)
* **Port:** `5432`
* **Database Name:** `dw_music_analytics`
* **Authentication:** User: `postgres`, Password: `postgres_secure_password`
* **Import Mode:** DirectQuery or Import
* **Target Schema Tables:**
  * `fact_music_performance` (Fact Table)
  * `dim_artist`, `dim_track`, `dim_genre`, `dim_time`, `dim_grammy_category` (Dimension Tables)

---

## 2. Implemented KPIs & Visualizations Matrix

| KPI ID | Analytical Requirement | DW Element / SQL Query Logic | Visualization Type | Key Empirical Insight |
| :--- | :--- | :--- | :--- | :--- |
| **KPI-01** | **RQ-01:** Acoustic Profile of Awarded vs. Non-Awarded Tracks | Grouped by `is_grammy_winner` averaging `danceability`, `energy`, `valence`, `acousticness`. | **Grouped Bar Chart / Audio Radar** (`kpi1_audio_profile.png`) | Grammy winners exhibit significantly higher **Valence** (0.53 vs 0.47) and **Energy** (0.67 vs 0.64), and lower **Acousticness** (0.24 vs 0.31), reflecting an Academy bias toward high-energy, positive sound textures. Average popularity is **42.88** vs **33.28** (+9.6 points). |
| **KPI-02** | **RQ-02:** Popularity Multiplier by Musical Genre | Inner Join between `fact_music_performance` and `dim_genre`, comparing average `popularity` between winners and general catalog. | **Comparative Genre Bar Chart with Uplift Delta** (`kpi2_genre_popularity.png`) | Traditional, vocal-heavy genres like **Soul** (+45.60 pts) and **Country** (+23.62 pts) experience the largest digital streaming popularity multiplier following Grammy acclaim. |
| **KPI-03** | **RQ-03:** Historical Evolution of Collaborations & Explicit Content | Join between `fact_music_performance`, `dim_time`, `dim_track`, and `dim_artist`, computing percentage shares across decades. | **Multi-Series Historical Line Trend Chart** (`kpi3_temporal_trends.png`) | Between the 1950s and 1980s, awarded songs featured 0.0% explicit content. By the 2000s this reached 10.16% and peaked in the 2010s at **15.27%**, accompanied by a dramatic surge in collaborations (**44.27%** of awarded tracks). |

---

## 3. Automated Replication
To regenerate all three high-resolution figures directly from PostgreSQL:
```bash
python3 scripts/generate_kpi_charts.py
```
Generated artifacts are preserved in:
* `docs/evidence/kpi1_audio_profile.png`
* `docs/evidence/kpi2_genre_popularity.png`
* `docs/evidence/kpi3_temporal_trends.png`
