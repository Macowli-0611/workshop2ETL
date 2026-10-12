# Comprehensive Analysis & Execution Plan: Workshop-2 (ETL)
**Building a Reliable Batch Data Pipeline**
*Faculty of Engineering and Basic Sciences — Academic Program: Data Engineering & AI*  
*Course: ETL (G01) — Universidad Autónoma de Occidente (UAO)*

---

## 1. Executive Summary & Core Engineering Principles

The primary objective of this workshop is to design, implement, validate, orchestrate, monitor, and document a **reliable, idempotent batch data pipeline** integrating two decoupled, heterogeneous sources (**Spotify** and **Grammy Awards**). The pipeline enforces automated data quality gates via **Great Expectations (GX)** and populates a **dimensional Data Warehouse (star schema)** in PostgreSQL, queried directly by an analytics dashboard.

### Core Evaluated Principles
1. **"A Data Engineer does not build scripts. A Data Engineer designs systems."**  
   The project evaluates a cohesive, reproducible system with strict separation of concerns, not disconnected scripts.
2. **"Reliable data pipelines do not assume that data is correct. They verify it."**  
   Data correctness is never taken for granted; it is verified at automated validation gates before entering subsequent layers.
3. **"Reliable does not mean that nothing fails. Reliable means that failures are anticipated, controlled, and observable."**  
   A reliable system anticipates anomalies, halts execution before contaminating downstream layers, and preserves clear, actionable logs.
4. **"Validation detects violations; transformation applies known engineering rules."**  
   Validation and transformation are distinct activities. **Modifying data solely to make a validation pass is strictly prohibited.**

---

## 2. System Scope & Deliverables

```
[Spotify CSV] ─────────► [extract_spotify] ───────► [validate_spotify_raw (GX)] ──┐
                                                                                  ├──► [transform_and_integrate] ──► [validate_prepared (GX)] ──► [load_dw] ──► [Analytics Dashboard]
[Grammy Relational DB] ──► [extract_grammys] ───────► [validate_grammys_raw (GX)] ──┘
```

### Mandatory Functional Components:
1. **Analytical Requirements Definition:** Formulation of at least **three analytical requirements** strictly requiring the combination of Spotify and Grammy datasets.
2. **Heterogeneous Extraction:**
   * **Spotify:** Direct extraction from raw CSV (`spotify_dataset.csv`, ~114,000 records).
   * **Grammy Awards:** Initial seeding of `the_grammy_awards.csv` into a **relational database (PostgreSQL)**. In operation, the pipeline **must extract Grammys from the relational database via SQL**, never from the CSV directly.
3. **Data Profiling:** A reproducible notebook (`notebooks/data_profiling.ipynb`) covering structure, completeness, uniqueness, data types, categorical distributions, numerical bounds, temporal spans, and cross-source matching.
4. **Automated Validation with Great Expectations (GX):**
   * At least **eight meaningful quality rules** mapped to severity levels (`Critical`, `Warning`, `Informational`).
   * **Raw Validation Gate:** Independently validates both incoming raw streams.
   * **Prepared Validation Gate:** Validates cleaned, integrated data prior to Data Warehouse loading.
5. **Transformation & Cross-Source Integration:**
   * Evidence-based cleaning and deduplication.
   * Formal Integration Contract: matching keys, expected cardinality, handling of unmatched catalog rows and collaborative artist tokens.
6. **Dimensional Data Warehouse:**
   * Physical implementation of a **Star Schema** in PostgreSQL.
   * Fact table with declared grain and dimension tables with surrogate keys (`SERIAL`).
   * Enforced idempotency and **Safe Rerun** strategy.
7. **Orchestration in Apache Airflow 3.1.8:**
   * Authored with the official **TaskFlow API** (`from airflow.sdk import dag, task`).
   * Strict dependency modeling, selective retry policies, and clean task interfaces.
8. **Business Intelligence & Analytics:**
   * At least **three KPIs** and **three visualizations** connected **directly to the Data Warehouse** (not to the CSV).
9. **Reliability Tests & Audit Evidence:**
   * **Test A:** Successful end-to-end execution.
   * **Test B:** Controlled critical quality failure (intentional violation halting the DAG and blocking downstream tasks).
   * **Test C:** Repeatability and safe rerun (demonstrating identical row counts and measure sums upon re-execution).

---

## 3. Technology Stack & Constraints

| Domain | Required Choice / Constraint | Rationale & Strict Rules |
| :--- | :--- | :--- |
| **Orchestrator** | **Apache Airflow 3.1.8** in Docker / Docker Compose | Must explicitly report version `3.1.8`. |
| **DAG Authoring** | **Python + Airflow TaskFlow API** | Mandatory import: `from airflow.sdk import dag, task`. |
| **Data Validation** | **Great Expectations (GX)** | Automated Expectation Suites and Checkpoints at raw and prepared gates. |
| **Operational DB & DW**| **PostgreSQL** (or MySQL) | ❌ **SQLite is strictly PROHIBITED**. |
| **Programming Language** | **Python 3.11+** | Modular package layout under `src/`. |
| **BI Tool** | **Power BI, Tableau, or Looker Studio** | Must query relational DW. ❌ Direct CSV connections prohibited. |
| **Version Control** | **Git & GitHub** | Clean repository, no committed credentials. |
| **Containerization** | **Docker & Docker Compose** | Reproducible multi-service deployment. |

---

## 4. Evaluation Criteria & Grade Weighting

| Evaluation Criterion | Brief Section | Points | Weight |
| :--- | :--- | :---: | :---: |
| **1. Analytical Requirements & Architecture** | Section 6.1, 5 | **0.40** | 8% |
| **2. Data Profiling & Quality Risk Analysis** | Section 6.3 | **0.60** | 12% |
| **3. ETL Transformation & Integration** | Section 6.8 | **0.60** | 12% |
| **4. Automated Validation with Great Expectations** | Section 6.5, 6.6, 6.7, 6.9 | **0.80** | 16% |
| **5. Airflow Orchestration & Reliability** | Section 6.11, 7.1, 7.2, 7.3 | **0.90** | 18% |
| **6. Dimensional Data Warehouse & Analytics** | Section 6.4, 6.10, 8.1 | **0.40** | 8% |
| **7. Repository & Documentation** | Section 9.1, 9.2 | **0.30** | 6% |
| **Subtotal Engineering Solution / Repository** | | **4.00** | **80%** |
| **Presentation & Technical Defense** | Section 10.2 | **1.00** | **20%** |
| **TOTAL** | | **5.00** | **100%** |
