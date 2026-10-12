# Analytical Requirements & Solution Scope

Section 6.1 of the brief. The requirement IDs (RQ-01..RQ-03) are used consistently in the rules (`DQ-*`), transformations (`TR-*`), DW views and KPIs. See [traceability_matrix.md](traceability_matrix.md).

## 1. Scope statement

The solution builds a reliable batch pipeline that integrates the **Spotify catalog** (114,000 track–genre rows with audio features and popularity, CSV file source) with the **Grammy Awards** history (4,810 award records, 1958–2019, extracted from the PostgreSQL source database `source_music_db`). It produces a trusted star-schema Data Warehouse (`dw_music_analytics`) and a BI dashboard.

The data product supports music analysts and A&R teams who want to compare **institutional recognition** (Grammy wins) with **listener consumption and sound profile** (Spotify). Out of scope: real-time ingestion, fuzzy or ML-based title matching, and causal claims (Spotify popularity is a single snapshot).

## 2. Analytical requirements

| ID | Analytical requirement (question / decision supported) | Required data and source of each attribute | Expected KPI(s) | Required level of detail |
| :--- | :--- | :--- | :--- | :--- |
| **RQ-01** | *Do Grammy-winning tracks have a different audio profile and popularity than the rest of the catalog?* Decision: which sound characteristics to prioritize in repertoire aimed at awards. | **Spotify:** `track_id`, `track_name`, `artists`, `danceability`, `energy`, `valence`, `acousticness`, `popularity`. **Grammys:** `nominee`, `artist`, `winner`. | **KPI-01** mean audio features and mean popularity for winners vs catalog; popularity uplift (winner mean − catalog mean). | Distinct track (winner flag); comparison by award status. |
| **RQ-02** | *In which genres is Grammy recognition associated with the largest popularity uplift?* Decision: where post-award promotion budget has the highest expected return. | **Spotify:** `track_genre`, `popularity`, `track_id`. **Grammys:** `nominee`, `artist`, `winner`. | **KPI-02** popularity uplift per genre (winner mean − catalog mean), with the number of awarded tracks per genre (≥ 5 to be compared). | Track × genre. |
| **RQ-03** | *How have explicit content and collaborations evolved among awarded tracks across decades?* Decision: editorial and collaboration strategy. | **Spotify:** `explicit`, `artists` (credited artist list → Solo/Collaboration). **Grammys:** `year`, `nominee`, `artist`, `winner`. | **KPI-03** % explicit and % collaborations among distinct awarded tracks per award decade. | Distinct awarded track × award decade. |

## 3. Why both sources are necessary

- **Spotify alone** has audio features, popularity, genre, explicit flag and credited artists, but no record of institutional recognition. It cannot tell which tracks won a Grammy, nor when.
- **Grammys alone** has the award, its year and category, but no audio profile, popularity, genre or explicit flag.
- Each KPI combines an attribute that exists only in Spotify (features, popularity, genre, explicit, collaborations) with one that exists only in the Grammys (winner status, award year). The integration contract ([integration_contract.md](integration_contract.md)) joins them on the normalized (title, primary artist) key.

## 4. Known data limitations that shape the requirements

- The Grammy file contains **only winners** (4,810/4,810 `winner = True`), so the requirements compare *winners vs catalog*, not nominees.
- Coverage of the match is low by nature (non-song categories, 38% of awards without artist, partial Spotify sample). It is measured on every run (integration report) and the KPIs report their sample sizes.
- Award years end in 2019; decade trends end in the 2010s.

## 5. Traceability references

| Requirement | Rules | Transformations | DW element | KPI |
| :--- | :--- | :--- | :--- | :--- |
| RQ-01 | DQ-RAW-SPT-01/03, DQ-RAW-GRM-01/02, DQ-PREP-INT-02/04/06/07/08 | TR-01, TR-04, TR-05, TR-07, TR-09 | `vw_kpi1_audio_profile` | KPI-01 |
| RQ-02 | DQ-RAW-SPT-04/06, DQ-PREP-INT-04/05/08 | TR-03, TR-04, TR-05, TR-09 | `vw_kpi2_genre_uplift` | KPI-02 |
| RQ-03 | DQ-RAW-SPT-02, DQ-RAW-GRM-01/04, DQ-PREP-INT-06 | TR-02, TR-07, TR-08, TR-10 | `vw_kpi3_decade_trends` | KPI-03 |
