# Dimensional Model — `dw_music_analytics`

Sections 6.4 and 6.10 of the brief. Executable definition: [`sql/dw_schema.sql`](../sql/dw_schema.sql) (idempotent, applied by `load_dw`). Destructive rebuild: [`sql/dw_reset.sql`](../sql/dw_reset.sql) (manual only).

## Design decisions

| Design decision | Content |
| :--- | :--- |
| **Business process** | Catalog performance of a music track: its Spotify popularity and audio profile in a catalog genre, enriched with the Grammy recognition the track received. |
| **Grain of the fact table** | One row per **Spotify track × catalog genre × award edition (year) × award category**. Tracks without an award use the default members `time_sk = 0` and `category_sk = 0`, so in this batch every track/genre has exactly one row (113,549 rows = clean catalog rows). |
| **Dimensions** | `dim_track` (track, album, duration, explicit) · `dim_artist` (primary artist, Solo/Collaboration) · `dim_genre` (Spotify genre) · `dim_time` (award year, decade) · `dim_grammy_category` (award category). |
| **Measures** | `popularity` (0–100), `danceability`, `energy`, `valence`, `acousticness` (0–1), `loudness`, `tempo` (non-additive: averaged); `is_grammy_winner`, `is_grammy_nominee` (flags, counted); `award_count` (additive). |
| **Keys** | Surrogate keys `SERIAL` for track, artist, genre and category; `dim_time` uses the year as a smart key (0 = Unknown). Business keys with `UNIQUE` constraints: `track_id_spotify`, `artist_name`, `genre_name`, `category_name`. The fact table has `fact_id BIGSERIAL` plus the grain constraint `uq_fact_grain`. |
| **Relationships** | Every fact foreign key `REFERENCES` its dimension (`NOT NULL`). Default members (SK 0) avoid NULL foreign keys for unmatched tracks. `CHECK` constraints enforce measure ranges at the database level. |
| **Audit** | `batch_id` (= Airflow `run_id`) and `loaded_at` on every fact row. |

```mermaid
erDiagram
    dim_track ||--o{ fact_music_performance : track_sk
    dim_artist ||--o{ fact_music_performance : artist_sk
    dim_genre ||--o{ fact_music_performance : genre_sk
    dim_time ||--o{ fact_music_performance : time_sk
    dim_grammy_category ||--o{ fact_music_performance : category_sk

    fact_music_performance {
        bigint fact_id PK
        int track_sk FK
        int artist_sk FK
        int genre_sk FK
        int time_sk FK
        int category_sk FK
        int popularity
        numeric danceability
        numeric energy
        numeric valence
        numeric acousticness
        numeric loudness
        numeric tempo
        boolean is_grammy_winner
        boolean is_grammy_nominee
        int award_count
        varchar batch_id
        timestamptz loaded_at
    }
    dim_track {
        int track_sk PK
        varchar track_id_spotify UK
        text track_name
        text album_name
        int duration_ms
        boolean explicit
    }
    dim_artist {
        int artist_sk PK
        varchar artist_name UK
        varchar artist_type
    }
    dim_genre {
        int genre_sk PK
        varchar genre_name UK
    }
    dim_time {
        int time_sk PK
        int year
        varchar decade
    }
    dim_grammy_category {
        int category_sk PK
        varchar category_name UK
        varchar category_field
    }
```

## Requirement support

| Requirement | Facts / dimensions used | DW element (view) |
| :--- | :--- | :--- |
| RQ-01 Audio profile, winners vs catalog | audio measures, `popularity`, `is_grammy_winner`, `dim_track` | `vw_track_profile` → `vw_kpi1_audio_profile` |
| RQ-02 Popularity uplift by genre | `popularity`, `is_grammy_winner`, `dim_genre` | `vw_kpi2_genre_uplift` |
| RQ-03 Explicit and collaboration share by decade | `dim_track.explicit`, `dim_artist.artist_type`, `dim_time.decade`, `is_grammy_winner` | `vw_track_profile` → `vw_kpi3_decade_trends` |

Because a track can appear in several genres, the track-level KPIs (RQ-01, RQ-03) first collapse the facts to one row per track (`vw_track_profile`) so that a song is never counted more than once. RQ-02 is genre-level, so it uses the fact grain directly and reports the sample size (`n_winner_tracks`) per genre.

## Loaded volumes (test_a_success)

| Table | Rows |
| :--- | ---: |
| `fact_music_performance` | 113,549 (475 winner rows) |
| `dim_track` | 89,740 |
| `dim_artist` | 17,645 |
| `dim_genre` | 114 |
| `dim_time` | 53 (52 award years + Unknown) |
| `dim_grammy_category` | 68 (67 + default) |
