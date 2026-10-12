# Project Context — what was built, how, and why

**Author:** Michael Macowli Cardona Rodriguez · ETL (G01) · Workshop-2 · 2026-2

This document explains the whole project in one place: the problem, what the brief asks for, how each requirement was implemented, which tools were used, and the reasoning behind every important decision. It is meant to be read before the defense; the other documents in `docs/` go deeper into each part.

---

## 1. The project in one paragraph

Two datasets describe music from two different worlds. **Spotify** (114,000 track–genre rows, a CSV file) says how songs sound (danceability, energy, valence, acousticness) and how popular they are. **The Grammy Awards** (4,810 awards from 1958–2019) say which songs were recognized by the Recording Academy. The brief requires that the Grammy data be extracted from a relational database, so it is first loaded into PostgreSQL and the pipeline reads it from there. We built a **batch pipeline orchestrated by Airflow** that extracts both sources, **checks their quality with Great Expectations before and after transforming them**, integrates them on a normalized (title, artist) key, and loads a **star-schema Data Warehouse** in PostgreSQL. A **Looker Studio dashboard** reads that warehouse to answer three business questions. The focus of the brief is reliability: the system must anticipate failures, stop bad data before it reaches the warehouse, retry only what can succeed on retry, and be safe to run again.

## 2. What the brief asks for, and where it is

| Brief section | Requirement | How it is met | Where |
| :--- | :--- | :--- | :--- |
| 6.1 | ≥ 3 analytical requirements that need both sources | RQ-01 audio profile, RQ-02 genre uplift, RQ-03 decade trends | `docs/requirements_and_traceability.md` |
| 6.2 | Docker, Airflow 3.1.8, PostgreSQL, Grammy CSV loaded into a source DB, no secrets in git | `docker-compose.yaml` (5 services), `source-seed` service with row-count reconciliation, `.env` git-ignored | `docker-compose.yaml`, `scripts/seed_source_db.py` |
| 6.3 | Reproducible profiling with evidence for every risk | Executed notebook with tables and figures; risk matrix | `notebooks/data_profiling.ipynb` |
| 6.4 / 6.10 | Requirements-driven dimensional model in PostgreSQL | Star schema: 1 fact + 5 dimensions, grain, keys, KPI views | `docs/dimensional_model.md`, `sql/dw_schema.sql` |
| 6.5 | ≥ 6 rules with dimension, threshold, severity, requirement | 18 rules (13 Critical, 3 Warning, 2 Informational) | `docs/quality_rules.md` |
| 6.6 | GX suites, validation definitions, checkpoints, rule mapping, results | 3 suites / 32 expectations, each tagged with its rule ID; per-run JSON results | `src/validation.py`, `gx/`, `docs/evidence/runs/` |
| 6.7 | Two observable source branches with raw gates; a controlled Critical failure | `extract_* → validate_*_raw` per source; Test B | `dags/reliable_music_pipeline.py`, Test B |
| 6.8 | Justified transformations and an integration contract | 12 TR rules; key, cardinality, unmatched and duplicate handling, all measured | `docs/transformation_and_integration.md`, `docs/transformation_and_integration.md` |
| 6.9 | Separate prepared gate that gates the load | `validate_prepared` (19 expectations); Test E proves it blocks `load_dw` | Test E |
| 6.11 | Meaningful tasks, dependencies, small XCom, selective retries, logging | 7 tasks; paths in XCom; retries only for transient failures; batch context in every log | `docs/architecture.md` |
| 7.1–7.3 | Success, controlled failure, safe rerun | Tests A, B, C (+ D for retries, E for the prepared gate) | `docs/evidence/test_*` |
| 4.4 / 8.3 | Evidence register and minimum evidence set | EV-01 … EV-20 | `docs/evidence/evidence_register.md` |
| 8.1 | ≥ 3 KPIs from the DW (no CSV) in a BI tool | Looker Studio report on DW views | `docs/dashboard.md` |
| 8.2 | End-to-end traceability | requirement → data → risk → rule → expectation → transformation → DW → KPI | `docs/requirements_and_traceability.md` |
| 9.2 | README with 17 sections | Sections 1–17 | `README.md` |

## 3. Tools and why they were chosen

| Tool | Role | Why |
| :--- | :--- | :--- |
| **Docker Compose** | Runs everything | One command reproduces the environment on any machine. |
| **Apache Airflow 3.1.8** (TaskFlow, `airflow.sdk`) | Orchestration | Required by the brief. TaskFlow keeps the DAG short; the logic lives in `src/`. |
| **Great Expectations 1.x** | Automated validation | Required. Its Suite → Validation Definition → Checkpoint model gives auditable, per-rule results. |
| **PostgreSQL 16** | Grammy source DB and Data Warehouse | Required (no SQLite). Transactions, `ON CONFLICT` upserts and `CHECK` constraints are what make the load safe. |
| **pandas / pyarrow** | Transformation and staging | The data fits in memory; Parquet keeps the types between tasks. |
| **Looker Studio** | Main dashboard | Named in the brief, runs in the browser, so it works on macOS (Power BI Desktop is Windows-only). |
| **Neon (cloud PostgreSQL)** | Published copy of the DW for Looker Studio | Looker Studio runs on Google's servers and cannot reach `localhost`. |
| **Metabase** | Local alternative dashboard | Works offline and is rebuilt from code. |
| **Playwright** | Screenshots | Evidence screenshots are captured by a script, so they can be regenerated. |

## 4. How the pipeline works

```
Spotify CSV ──► extract_spotify ──► validate_spotify_raw ──┐
                                                           ├──► transform_and_integrate ──► validate_prepared ──► load_dw ──► DW ──► publish_dw ──► Looker Studio
Grammy DB ────► extract_grammys ──► validate_grammys_raw ──┘
```

1. **Extract.** Each source is copied as-is to a staging Parquet file for the current run (`data/staging/<run_id>/`). Nothing is cleaned here, so source problems stay visible to the gate.
2. **Raw gates.** Each source is checked by its own expectation suite: schema, IDs, ranges, years, nulls, duplicates, volume. A Critical failure stops that run.
3. **Transform and integrate.** Corrupted and duplicated rows are removed, text is normalized, the primary artist is extracted, Grammy rows are aggregated per key, and the catalog is LEFT-joined to the awards. Every count is written to `integration_report.json`.
4. **Prepared gate.** The integrated data is checked again: exact schema, ranges with no tolerance, a unique fact grain, integration integrity and a minimum match rate.
5. **Load.** Dimensions and facts are written in **one transaction** with an upsert on the grain and a purge of stale rows, then reconciled.
6. **Dashboard.** `publish_dw.py` copies the warehouse to Neon and checks the counts; Looker Studio reads the KPI views through a role that can only read those views.

Every task logs a `BATCH CONTEXT` line (run ID, task, try), and every run writes its own evidence folder, so earlier runs are never overwritten.

## 5. Key decisions and the reasoning behind them

**Requirements first.** The three questions were defined before profiling. Each one combines something only Spotify has (sound, popularity, genre, explicit, credits) with something only the Grammys have (winner, year). That is what justifies integrating the two sources.

**Profiling drives the rules.** The rules come from what the data showed, not from a generic checklist:
- 450 duplicated (track, genre) rows → a uniqueness warning and a dedup transformation
- 1 corrupted row with 0 ms duration → a duration rule with a 99.9% tolerance
- 38% of awards without an artist → a measured coverage limit
- 100% of Grammy rows are winners → "winners vs catalog", not nominees

**Validation never fixes data.** The gates only measure and decide. Cleaning happens in the transformation, with rules (TR-01 … TR-12) that are justified on their own. Values that cannot be repaired are dropped and counted, never invented.

**Severities have consequences.** Critical stops the run and protects the warehouse. Warning lets the run continue but is logged and recorded. Informational is a trend signal. Thresholds were chosen from the evidence. For example, the minimum match rate (0.1%) protects KPI-02, which needs genres with at least five winners.

**The GX context is ephemeral, the configuration is not.** The two raw gates run in parallel. A shared file-based GX context would be written by two processes at once, so each task creates its own context and exports the suites, validation definitions and checkpoints to `gx/` on every run.

**Integration is a contract.** The key is the normalized title plus the primary artist. Cardinality is many-to-one: Grammy rows are aggregated per key first, and pandas enforces it (`validate="many_to_one"`). Unmatched rows on both sides are counted, not hidden. No fuzzy matching is used, because its false positives could not be audited.

**The grain decides the model.** One fact row = track × genre × award year × category. Unmatched tracks use default members (key 0), so foreign keys are never NULL. KPI views sit on top of the warehouse. Track-level KPIs collapse genres first, so a song that appears in several genres counts once.

**Retries only where they can help.** Extractions retry twice with backoff, because a database can be briefly unavailable. The load retries once, because it is a single atomic transaction. Gates and the transformation never retry, because the same batch fails the same way.

**Reruns are safe by construction.** The load is an upsert on the grain followed by a purge of rows that are not in the current batch, all in one transaction. Running the same batch twice changes nothing but the audit stamp. A failure at any point rolls back to the last good load.

**Evidence is generated, not hand-made.** `scripts/run_reliability_tests.sh` reproduces Tests A–E and writes all their evidence. Screenshots, logs and the deck are also generated by scripts. Anyone can regenerate the evidence and check it.

## 6. How it maps to the rubric

| Criterion (points) | What demonstrates it |
| :--- | :--- |
| Analytical requirements & architecture (0.40) | 3 requirements that need both sources; required architecture implemented as-is; traceability matrix |
| Profiling & quality risks (0.60) | Executed notebook; 18 evidence-based rules with dimension, threshold and severity |
| Transformation & integration (0.60) | 12 justified TR rules; integration contract with measured counts; full reconciliation 114,000 → 113,549 |
| Great Expectations (0.80) | 3 suites, 32 expectations mapped to rule IDs; validation definitions and checkpoints; JSON results for success and failure |
| Airflow orchestration & reliability (0.90) | 7-task DAG with dependencies; selective retries; batch-context logs; Tests A–E |
| Dimensional DW & analytics (0.40) | Star schema with constraints; KPI views; Looker Studio dashboard on the DW |
| Repository & documentation (0.30) | One-command setup; README with 17 sections; evidence register; no secrets; English throughout |
| Presentation & defense (1.00) | 19-slide deck with speaker notes; live demo plan with a screenshot fallback |

## 7. What the tests proved

| Test | Situation | Result |
| :--- | :--- | :--- |
| A | normal batch | 7/7 tasks, 32/32 expectations, 113,549 rows loaded = prepared |
| B | a 1800 award year in the source DB | raw gate stops; transform, prepared gate and load blocked; DW unchanged |
| C | same batch run again | 0 inserted, 113,549 updated, 0 purged; same totals |
| D | source DB refuses connections briefly | try 1 fails, try 2 succeeds after backoff |
| E | artist credits change format at the source | raw gates pass, matched rows drop 475 → 71, prepared gate stops the load |

## 8. Lessons learned during the build

- **Testing the gates found a real gap.** The first run of Test E passed the prepared gate, because it only required "at least one match". The minimum match rate was added, and all tests were rerun.
- **Averages can double count.** Early KPIs averaged fact rows, so songs listed in several genres counted more than once. Track-level views fixed it (the 2010s explicit share moved from 15.3% to 20.2%).
- **Reruns with the same run ID append logs.** Airflow kept the old log in the same file, so the test script now clears it before each repetition.
- **Security hygiene matters.** An old password was found in the git history and rotated before publishing; the dashboard uses a read-only role limited to the views.

## 9. Limitations

- Only winners exist in the Grammy file, so there is no nominee tier.
- Exact matching on a normalized key: 4.1% of award keys match (many categories are not songs, 38% have no artist). Coverage is measured on every run.
- Spotify popularity is a single snapshot, so the KPIs show association, not cause.
- Some genres have few winners; the sample size (n) is always shown.
- The dashboard reads a published copy of the DW, refreshed by `publish_dw.py` after each load.

## 10. Results in short

- Grammy winners are **12.04 popularity points** above the rest of the catalog (45.21 vs 33.17). They have higher valence and lower acousticness.
- The uplift is largest in **soul (+45.6, n = 20)**, jazz and country, and negative in pop and electro.
- Explicit content among awarded tracks rose from **0% before the 1990s to 20.2% in the 2010s**, and collaborations reached **35.7%**.
