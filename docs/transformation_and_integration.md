# Transformation & Integration

## 1. Transformation decision record

Section 6.8 of the brief. Every rule is implemented in `src/transform.py` (marked with its `TR-xx` ID) and is justified independently of the validation result. Validation detects; these rules transform. Counts come from [`runs/test_a_success/integration_report.json`](evidence/runs/test_a_success/integration_report.json).

| ID | Rule and rationale | Affected fields / records | Before → after | Exception handling | Analytical impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TR-01** | Drop catalog rows without `track_name`, `artists` or `track_id`. Profiling found 1 corrupted row (index 65,900) with null metadata. | Whole row. | 114,000 → 113,999 (1 removed). | Not repairable: there is no source of truth for the missing title or artist. | `dim_track` / `dim_artist` require non-null business keys (DQ-PREP-INT-02). |
| **TR-02** | Drop rows with `duration_ms` ≤ 1,000 ms, which is physically implausible for a track. | Whole row. | 0 additional rows this batch (the 0 ms row was already removed by TR-01). | Rows are discarded, not imputed: an imputed duration would invent data. | Protects duration and audio-feature averages (RQ-03, DQ-PREP-INT-04). |
| **TR-03** | Remove exact duplicates on (`track_id`, `track_genre`). Profiling found 450 (0.39%), and they are full-row duplicates. | Whole row. | 113,999 → 113,549 (450 removed). | The first occurrence is kept; the rows are identical, so nothing is lost. | Prevents double counting in genre KPIs (RQ-02) and enforces the fact grain. |
| **TR-04** | Text normalization for matching: lower-case, trim, punctuation → space, collapse spaces. | Derived `clean_track_name`, `clean_nominee` (originals preserved for display). | `"Don't Stop Believin'"` → `"don t stop believin"`. | Null → empty string, which never matches. | Makes the cross-source key comparable (integration contract). |
| **TR-05** | Primary artist extraction: Spotify splits on `;`; Grammys split on `featuring`, `feat.`, `&`, `with`. | `primary_artist` → `artist_name`; derived `clean_*_artist`. | `"Lady Gaga;Bradley Cooper"` → `"Lady Gaga"`. | Null artist → `"Unknown Artist"`, which does not match any Spotify artist. | Makes the artist part of the key compatible; `dim_artist` business key. |
| **TR-06** | Exclude Grammy rows with null `nominee` from matching (6 rows, Warning rule DQ-RAW-GRM-02). | Grammy rows. | 4,810 → 4,804 rows used for matching. | Counted in the integration report. | Avoids an empty-title key matching empty titles. |
| **TR-07** | Aggregate Grammy rows per normalized key: `year`=max, `category`=first, `award_count`=count. | Grammy side of the join. | 4,804 rows → 4,438 keys (286 with more than one award). | — | Guarantees the many-to-one cardinality (no duplicate matches). |
| **TR-08** | Derive `artist_type`: `Collaboration` if `artists` contains `;`, else `Solo`. | New attribute of `dim_artist`. | — | Null artists cannot reach this step (TR-01). | RQ-03 collaboration ratio. |
| **TR-09** | Unmatched catalog rows: `is_grammy_winner=False`, `award_count=0`, `award_year=0`, `grammy_category='No Nomination / Not Applicable'` (default dimension members, SK 0). | Award attributes of the 113,074 unmatched rows. | NaN → explicit defaults. | Checked by DQ-PREP-INT-06. | Keeps the comparison group for RQ-01/RQ-02 without NULL foreign keys. |
| **TR-10** | Derive `decade` from `award_year` (e.g. 2014 → `2010s`; 0 → `Unknown`). | `decade` (`dim_time`). | — | — | RQ-03 decade grouping. |
| **TR-11** | Final dedup on the fact grain (`track_id_spotify`, `genre_name`, `award_year`, `grammy_category`). | Prepared rows. | 0 removed this batch (TR-03 + TR-07 already guarantee uniqueness). | Defensive; DQ-PREP-INT-05 still verifies it. | Required by the `uq_fact_grain` upsert. |
| **TR-12** | Type conversion and rounding: `duration_ms`/`popularity` → int, `explicit` → bool, audio features rounded to 4 decimals, `loudness`/`tempo` to 3. | Measures. | float64 → `NUMERIC(6,4)` / `NUMERIC(7,3)` compatible values. | Out-of-range values would fail the DW `CHECK` constraints and DQ-PREP-INT-04. | Exact, stable measures across reruns (Test C compares sums). |

**Reconciliation (test_a_success):** 114,000 raw − 1 (TR-01) − 0 (TR-02) − 450 (TR-03) = 113,549 clean rows = 113,549 prepared rows = 113,549 fact rows (`load_report.json`: `fact_rows_equal_prepared_rows: true`).

## 2. Integration contract

Section 6.8 of the brief. Implemented in `src/transform.py:transform_and_integrate`. The metrics below are computed on every run and written to `docs/evidence/runs/<run_id>/integration_report.json`; the figures are from [`test_a_success`](evidence/runs/test_a_success/integration_report.json).

| Item | Team decision | Evidence (test_a_success) |
| :--- | :--- | :--- |
| **Integration key(s)** | Spotify (`track_name`, primary artist of `artists`) ↔ Grammy (`nominee`, primary artist of `artist`). Both sides are normalized into `(clean_track_name, clean_primary_artist)`. | 4,438 distinct Grammy keys after TR-07. |
| **Cardinality** | **Many-to-one** (Spotify rows → Grammy key). Grammy rows are first aggregated to one row per key (TR-07), so a Spotify row can match at most one award record. This is enforced by `pandas.merge(..., validate="many_to_one")`, which raises an error if it is violated. One Grammy key can match several Spotify rows: the same song in several genres, or several releases of the song. | 181 matched keys → 475 matched rows → 282 distinct tracks. 49 keys match more than one `track_id` (max 9). |
| **Preprocessing** | TR-04: lower-case, trim, punctuation → space, collapse whitespace. TR-05: primary artist = text before the first `;` (Spotify) or before `featuring`/`feat.`/`&`/`with` (Grammys). TR-06: Grammy rows without `nominee` are excluded from matching. | Notebook §8c: raw text matches 161 of 4,446 keys (3.62%), normalized key 181 of 4,438 (4.08%). |
| **Join type** | `LEFT JOIN` from the Spotify catalog: every catalog row is kept, because RQ-01/RQ-02 need the non-awarded catalog as the comparison group. | prepared rows = clean Spotify rows = 113,549 (`spotify_clean_rows_equal_prepared_rows: true`). |
| **Unmatched records** | *Spotify side:* kept, with `is_grammy_winner=False`, `award_count=0`, `award_year=0` → `dim_time` SK 0 ("Unknown"), category → `dim_grammy_category` SK 0 ("No Nomination / Not Applicable"). *Grammy side:* unmatched keys are counted, not loaded (the DW grain is a catalog track). | Matched rows 0.418% of the catalog. Unmatched Grammy keys: 4,257 (95.9%). |
| **Duplicate matches** | Impossible by design: the key is aggregated first, and `validate="many_to_one"` stops the task if it ever happens. Multi-award keys keep `award_count` (number of award rows), the latest `year` and the first `category`. | 286 keys with more than one award; `duplicate_matches_per_spotify_row: 0`. |
| **Quality checks on the result** | DQ-PREP-INT-05 (grain unique), DQ-PREP-INT-06 (matched ⇒ valid year and award_count ≥ 1; unmatched ⇒ year 0), DQ-PREP-INT-07 (both tiers exist and matched rows ≥ 0.1%, the floor that catches a broken key, see Test E), DQ-PREP-INT-08 (match rate ≤ 5%). | `prepared_validation.json`: 19/19 passed. Test E: a key break (71 rows) is stopped. |

### Assumptions and limitations

- **Low coverage is expected and measured, not hidden.** The Grammy file spans 1958–2019 and covers many categories that are not songs (albums, classical works, craft and production awards). Of the 4,810 rows, 1,840 have no `artist`, so their key cannot match a Spotify track. The Spotify sample (114k tracks, about 1k per genre) contains only part of the awarded songs.
- **Exact matching on normalized text.** Live versions, remasters ("- Remastered 2011"), translated titles or different artist credits do not match. These tracks stay in the "General Catalog" group, which slightly dilutes the winner/catalog contrast. No fuzzy matching is applied, to avoid false positives that cannot be audited.
- **Only winners exist in the source.** All 4,810 Grammy rows have `winner = True`, so `is_grammy_nominee` equals `is_grammy_winner` and RQ-01/RQ-02 compare *winners* vs *catalog* (there is no nominee tier).
- **Multi-award keys** keep the latest award year. RQ-03 trends are therefore measured at the track's most recent award.
- **Popularity is a 2022 snapshot** of Spotify, while awards span six decades. RQ-02 measures association, not a causal post-award effect.
