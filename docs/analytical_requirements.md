# Analytical Requirements & Solution Scope Document (Phase 0)
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Course: ETL (G01) — Faculty of Engineering and Basic Sciences*  
*Autonomous University of the West (UAO)*

---

## 1. Scope Statement
The objective of this engineering solution is to design and implement a reliable, idempotent batch data pipeline that integrates two decoupled, heterogeneous sources: digital music catalog and audio characteristics from **Spotify** (`spotify_dataset.csv`) and the historical archive of honors and awards from the **Grammy Awards** (`the_grammy_awards.csv`, hosted in an operational PostgreSQL relational database).

The resulting dimensional Data Warehouse empowers music industry analysts, executive producers, and Artists and Repertoire (A&R) directors to evaluate the empirical correlation between formal institutional recognition (Grammys) and digital commercial consumption and sound profile on streaming platforms.

---

## 2. Analytical Requirements Matrix (Section 6.1 of the Brief)

| ID | Analytical Requirement | Business Question / Decision Supported | Required Attributes | Source(s) | Expected KPI(s) | Required Level of Detail (Grain) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RQ-01** | **Acoustic & Perceptual Profile of Awarded vs. Non-Awarded Tracks** | Do specific audio features (Danceability, Energy, Valence, Acousticness) distinguish Grammy-winning and nominated songs from standard catalog tracks? *Decision: Guide production choices and repertoire curation for awards consideration.* | `track_name`, `artists`, `danceability`, `energy`, `valence`, `acousticness`, `tempo`, `nominee`, `artist`, `winner`, `category`, `year` | **Spotify:** Audio features & metadata.<br>**Grammys:** Category, award status, year. | **KPI 1.1:** Acoustic Differential Ratio (Winner vs. Catalog).<br>**KPI 1.2:** Audio Feature Fingerprint by Award Tier. | Individual audio track (`track_id`), award edition year, and category. |
| **RQ-02** | **Impact of Grammy Acclaim on Popularity Multiplier Across Genres** | How does the distribution of Spotify popularity vary between Grammy winners, nominees, and non-awarded tracks across musical genres? *Decision: Budget allocation for genre marketing and post-nomination promotional spend.* | `track_genre`, `popularity`, `track_name`, `artists`, `nominee`, `artist`, `winner`, `category` | **Spotify:** `track_genre`, `popularity`.<br>**Grammys:** `category`, `winner`. | **KPI 2.1:** Mean Popularity by Award Tier.<br>**KPI 2.2:** Genre Popularity Uplift Delta (Winners vs. General Catalog). | Musical genre (`track_genre`) and award acclaim tier. |
| **RQ-03** | **Historical Evolution of Collaborations and Explicit Content in Awarded Music** | How has the proportion of awarded songs featuring multiple credited artists (collaborations) and explicit lyrical content evolved over decades compared to streaming catalog trends? *Decision: Editorial guidelines and collaboration investments.* | `year`, `explicit`, `artists`, `artist`, `workers`, `winner`, `category`, `nominee` | **Spotify:** `explicit`, credited artist list.<br>**Grammys:** Edition year, category, credits. | **KPI 3.1:** Awarded Explicit Content Share Rate (% winners with `explicit = True` by decade).<br>**KPI 3.2:** Awarded Collaboration Ratio (% tracks with $\ge 2$ credited artists). | Award decade and edition year. |

---

## 3. Justification for Cross-Source Integration
Neither dataset can satisfy these analytical needs independently:
1. **Spotify** provides fine-grained perceptual signal processing attributes (`danceability`, `energy`, `acousticness`) and real-world digital streaming telemetry (`popularity`), but lacks critical historical industry prestige, nomination records, and awards data.
2. **Grammy Awards** records the definitive 60+ year historical archive of Recording Academy accolades (since 1958), but contains zero digital consumption telemetry, audio signal features, or modern streaming genre classifications.

Unifying both sources through a formal Integration Contract establishes a novel analytical asset correlating institutional artistic acclaim with digital listener consumption patterns.

---

## 4. End-to-End Traceability Chain
Every downstream engineering decision traces back directly to these requirements:
* **Profiling Phase:** Specifically targets artist naming conventions (semicolon-separated in Spotify vs. collaborative tokens in Grammys), null presence in popularity, and boundary verification of acoustic metrics ($[0.0, 1.0]$).
* **Great Expectations Gates:** Enforces strict non-null and valid range constraints to ensure no corrupt timestamps or broken keys enter the Data Warehouse.
* **Dimensional Modeling:** Directly drives fact table measure definitions (`popularity`, audio features, award counts) and dimension hierarchies (`dim_artist`, `dim_track`, `dim_genre`, `dim_time`, `dim_grammy_category`).
