#!/usr/bin/env python3
"""
DW Analytics & KPI Visualizations Generator: scripts/generate_kpi_charts.py
--------------------------------------------------------------------------
Queries the analytical views of the dimensional Data Warehouse (dw_music_analytics)
and renders static copies of the three KPI visualizations, plus a CSV with the exact
numbers behind each chart. The interactive dashboard lives in Metabase
(scripts/setup_metabase.py) and reads the same views.

Run inside the Airflow container (all dependencies are installed there):
    docker compose exec airflow python /opt/airflow/scripts/generate_kpi_charts.py
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(PROJECT_ROOT, "docs", "evidence", "kpi")
MIN_WINNER_TRACKS = 5  # genres with fewer awarded tracks are not compared (unstable means)

DW_URL = "postgresql://{u}:{p}@{h}:{port}/{db}".format(
    u=os.environ["POSTGRES_USER"], p=os.environ["POSTGRES_PASSWORD"],
    h=os.getenv("POSTGRES_HOST", "localhost"), port=os.getenv("POSTGRES_PORT", "5432"),
    db=os.getenv("DW_DB_NAME", "dw_music_analytics"),
)

os.makedirs(OUT_DIR, exist_ok=True)
sns.set_theme(style="whitegrid", palette="muted")
engine = create_engine(DW_URL)


def _save(fig_name: str, df: pd.DataFrame):
    out_png = os.path.join(OUT_DIR, f"{fig_name}.png")
    plt.savefig(out_png, dpi=170)
    plt.close()
    df.to_csv(os.path.join(OUT_DIR, f"{fig_name}.csv"), index=False)
    print(f"[+] {out_png} (+ .csv)")


def generate_kpi1():
    df = pd.read_sql("SELECT * FROM vw_kpi1_audio_profile ORDER BY award_status DESC", engine)
    features = ["avg_danceability", "avg_energy", "avg_valence", "avg_acousticness"]
    melted = df.melt(id_vars=["award_status", "n_tracks"], value_vars=features,
                     var_name="feature", value_name="mean")
    melted["feature"] = melted["feature"].str.replace("avg_", "").str.capitalize()
    labels = {r.award_status: f"{r.award_status} (n={r.n_tracks:,} tracks)" for r in df.itertuples()}
    melted["award_status"] = melted["award_status"].map(labels)

    plt.figure(figsize=(9, 5))
    ax = sns.barplot(data=melted, x="feature", y="mean", hue="award_status", palette=["#e67e22", "#3498db"])
    for p in ax.patches:
        if p.get_height() > 0:
            ax.annotate(f"{p.get_height():.2f}", (p.get_x() + p.get_width() / 2, p.get_height() + 0.01),
                        ha="center", fontsize=9)
    pops = ", ".join(f"{r.award_status}: {r.avg_popularity}" for r in df.itertuples())
    plt.title(f"KPI 1 (RQ-01): Audio profile, Grammy winners vs catalog\nMean popularity: {pops}",
              fontsize=12, fontweight="bold")
    plt.ylabel("Mean value [0-1]")
    plt.xlabel("")
    plt.ylim(0, 1)
    plt.legend(title="", loc="upper right")
    plt.tight_layout()
    _save("kpi1_audio_profile", df)


def generate_kpi2():
    df = pd.read_sql(f"""
        SELECT * FROM vw_kpi2_genre_uplift
        WHERE n_winner_tracks >= {MIN_WINNER_TRACKS}
        ORDER BY popularity_uplift DESC
    """, engine)
    top = df.head(10)
    plt.figure(figsize=(10, 5.5))
    colors = ["#27ae60" if v >= 0 else "#c0392b" for v in top["popularity_uplift"]]
    ax = sns.barplot(data=top, y="genre_name", x="popularity_uplift", palette=colors, hue="genre_name", legend=False)
    for i, r in enumerate(top.itertuples()):
        ax.annotate(f"{r.popularity_uplift:+.1f}  (n={r.n_winner_tracks} winners)",
                    (max(r.popularity_uplift, 0) + 0.5, i), va="center", fontsize=9)
    plt.title(f"KPI 2 (RQ-02): Popularity uplift of Grammy winners by genre\n"
              f"(winner avg - catalog avg; genres with >= {MIN_WINNER_TRACKS} awarded tracks)",
              fontsize=12, fontweight="bold")
    plt.xlabel("Popularity uplift (points, 0-100 scale)")
    plt.ylabel("")
    plt.tight_layout()
    _save("kpi2_genre_uplift", df)


def generate_kpi3():
    df = pd.read_sql("SELECT * FROM vw_kpi3_decade_trends ORDER BY decade", engine)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(df["decade"], df["pct_explicit"], marker="o", linewidth=2.5, label="% explicit", color="#e74c3c")
    ax.plot(df["decade"], df["pct_collaboration"], marker="s", linewidth=2.5, label="% collaborations",
            color="#2980b9")
    for r in df.itertuples():
        ax.annotate(f"n={r.n_winner_tracks}", (r.decade, -4), ha="center", fontsize=8, color="#555")
    ax.set_ylim(-7, max(60, df[["pct_explicit", "pct_collaboration"]].max().max() + 10))
    plt.title("KPI 3 (RQ-03): Explicit content and collaborations among awarded tracks, by decade",
              fontsize=12, fontweight="bold")
    plt.xlabel("Award decade")
    plt.ylabel("Share of distinct awarded tracks (%)")
    plt.legend(loc="upper left")
    plt.tight_layout()
    _save("kpi3_decade_trends", df)


if __name__ == "__main__":
    generate_kpi1()
    generate_kpi2()
    generate_kpi3()
    print("[+] KPI charts rendered from the Data Warehouse views.")
