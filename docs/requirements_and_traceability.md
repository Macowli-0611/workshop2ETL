# Analytical Requirements & Traceability

Section 6.1 of the brief. The requirement IDs (RQ-01..RQ-03) are used consistently in the rules (`DQ-*`), transformations (`TR-*`), DW views and KPIs. See [section 6](#6-end-to-end-traceability-matrix).

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
- Each KPI combines an attribute that exists only in Spotify (features, popularity, genre, explicit, collaborations) with one that exists only in the Grammys (winner status, award year). The integration contract ([integration_contract.md](transformation_and_integration.md#2-integration-contract)) joins them on the normalized (title, primary artist) key.

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

## 6. End-to-end traceability matrix

Section 8.2 of the brief. These representative rows follow each requirement through the full chain: data → profiling risk → rule → GX Expectation → transformation → DW element → KPI. They are not an exhaustive list.

| Requirement | Required data | Quality risk (profiling evidence) | DQ rule | GX Expectation | Transformation | DW element | KPI / Visualization |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| RQ-01 | Spotify audio features | Values outside [0, 1] would corrupt the profile (all in range today, notebook §6) | DQ-RAW-SPT-03 (Critical) · DQ-PREP-INT-04 (Critical) | `expect_column_values_to_be_between(0, 1)` on 4 features, raw and prepared | TR-12 rounding to `NUMERIC(6,4)` | `fact_music_performance.danceability…acousticness` + `CHECK` → `vw_kpi1_audio_profile` | KPI-01 bar chart "Audio profile: Grammy winners vs catalog" |
| RQ-01 | Spotify `track_name`, `artists` + Grammy `nominee`, `artist` | Different artist delimiters (`;` vs `feat.`/`&`): raw text matches 161 keys, normalized key 181 (notebook §8c) | DQ-PREP-INT-07 (Critical: both tiers + matched rows ≥ 0.1%, Test E) · DQ-PREP-INT-08 (Warning: ≤ 5%) | `expect_column_distinct_values_to_contain_set`; `expect_column_values_to_be_in_set` with `mostly=0.001` (True) and `mostly=0.95` (False) on `is_grammy_winner` | TR-04 normalization, TR-05 primary artist, TR-07 aggregation | `is_grammy_winner` flag → `vw_track_profile` | KPI-01 tiles "Popularity uplift" and "Awarded tracks matched" |
| RQ-01 / RQ-03 | Grammy `year` | Out-of-range years break `dim_time` (range 1958–2019, notebook §7) | DQ-RAW-GRM-01 (Critical) | `expect_column_values_to_be_between(1958, 2026)` on `year` | TR-10 decade derivation; TR-09 default year 0 | `dim_time (time_sk = year)` | KPI-03 line chart by decade (**Test B** blocks the run when violated) |
| RQ-02 | Spotify (`track_id`, `track_genre`) | 450 duplicated pairs = 0.39% (notebook §4) would double count genre means | DQ-RAW-SPT-06 (Warning) · DQ-PREP-INT-05 (Critical) | `expect_compound_columns_to_be_unique` (raw `mostly=0.99`; prepared on the fact grain) | TR-03 dedup, TR-11 grain dedup | `uq_fact_grain` → `vw_kpi2_genre_uplift` | KPI-02 row chart "Popularity uplift by genre" + detail table with sample sizes |
| RQ-02 | Spotify `popularity` | Scale must be 0–100 for comparable means (notebook §6, §8b) | DQ-RAW-SPT-04 · DQ-PREP-INT-04 (Critical) | `expect_column_values_to_be_between(0, 100)` raw and prepared | TR-12 cast to int | `fact_music_performance.popularity` + `CHECK` | KPI-02 uplift values |
| RQ-03 | Spotify `duration_ms`, metadata | 1 corrupted row (0 ms, null title) (notebook §3, §6) | DQ-RAW-SPT-02 (Critical, mostly 0.999) · DQ-PREP-INT-02/04 | `expect_column_values_to_be_between(>1000)`; `expect_column_values_to_not_be_null` | TR-01, TR-02 drop | `dim_track.duration_ms`, NOT NULL keys | Clean base for every KPI |
| RQ-03 | Spotify `artists` (collaborations), `explicit` | Collaboration only identifiable via `;` in the credit list (notebook §8) | DQ-RAW-SPT-05 (Critical, schema) | `expect_table_columns_to_match_set` | TR-08 `artist_type` | `dim_artist.artist_type`, `dim_track.explicit` → `vw_kpi3_decade_trends` | KPI-03 "% explicit / % collaborations by decade"; tile "Explicit share 2010s" |
| RQ-01..03 | Grammy rows matched / unmatched | Matched rows must carry award data; unmatched must use defaults | DQ-PREP-INT-06 (Critical) | `expect_column_values_to_be_between` with `row_condition` on `is_grammy_winner` | TR-09 default members | `dim_time` / `dim_grammy_category` SK 0 | All KPIs (winner vs catalog split) |
