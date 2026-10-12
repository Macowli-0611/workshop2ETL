# Integration Contract — Spotify × Grammy Awards

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

## Assumptions and limitations

- **Low coverage is expected and measured, not hidden.** The Grammy file spans 1958–2019 and covers many categories that are not songs (albums, classical works, craft and production awards). Of the 4,810 rows, 1,840 have no `artist`, so their key cannot match a Spotify track. The Spotify sample (114k tracks, about 1k per genre) contains only part of the awarded songs.
- **Exact matching on normalized text.** Live versions, remasters ("- Remastered 2011"), translated titles or different artist credits do not match. These tracks stay in the "General Catalog" group, which slightly dilutes the winner/catalog contrast. No fuzzy matching is applied, to avoid false positives that cannot be audited.
- **Only winners exist in the source.** All 4,810 Grammy rows have `winner = True`, so `is_grammy_nominee` equals `is_grammy_winner` and RQ-01/RQ-02 compare *winners* vs *catalog* (there is no nominee tier).
- **Multi-award keys** keep the latest award year. RQ-03 trends are therefore measured at the track's most recent award.
- **Popularity is a 2022 snapshot** of Spotify, while awards span six decades. RQ-02 measures association, not a causal post-award effect.
