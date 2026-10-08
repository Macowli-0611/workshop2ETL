#!/usr/bin/env python3
"""
DW Analytics & KPI Visualizations Generator: scripts/generate_kpi_charts.py
--------------------------------------------------------------------------
Directly queries the dimensional Data Warehouse in PostgreSQL (dw_music_analytics)
and renders high-resolution figures for Section 8.1 of the workshop brief.
"""

import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres_secure_password")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("DW_DB_NAME", "dw_music_analytics")

DW_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

os.makedirs("docs/evidence", exist_ok=True)
sns.set_theme(style="whitegrid", palette="muted")
engine = create_engine(DW_URL)

def generate_kpi1():
    print("[*] Generating KPI 1: Comparative Audio Profile...")
    query = """
        SELECT 
            CASE WHEN is_grammy_winner THEN 'Grammy Winner' ELSE 'General Catalog' END AS award_status,
            AVG(danceability) AS danceability,
            AVG(energy) AS energy,
            AVG(valence) AS valence,
            AVG(acousticness) AS acousticness
        FROM fact_music_performance
        GROUP BY is_grammy_winner;
    """
    df = pd.read_sql(query, engine)
    df_melted = df.melt(id_vars="award_status", var_name="Audio Feature", value_name="Mean Value")
    df_melted["Audio Feature"] = df_melted["Audio Feature"].str.capitalize()

    plt.figure(figsize=(9, 5))
    ax = sns.barplot(
        data=df_melted, 
        x="Audio Feature", 
        y="Mean Value", 
        hue="award_status", 
        palette=["#3498db", "#e67e22"]
    )
    plt.title("KPI 1: Audio Profile Comparison (Grammy Winners vs. General Catalog)", fontsize=13, fontweight="bold", pad=15)
    plt.ylabel("Mean Normalized Value [0.0 - 1.0]", fontsize=11)
    plt.xlabel("Audio Characteristic", fontsize=11)
    plt.ylim(0, 1.0)
    for p in ax.patches:
        h = p.get_height()
        if h > 0:
            ax.annotate(f"{h:.2f}", (p.get_x() + p.get_width() / 2., h / 2), ha="center", va="center", color="white", fontweight="bold", fontsize=9)
    plt.legend(title="Award Status", loc="upper right")
    plt.tight_layout()
    out_path = "docs/evidence/kpi1_audio_profile.png"
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[+] KPI 1 saved to: {out_path}")

def generate_kpi2():
    print("[*] Generating KPI 2: Popularity Multiplier by Genre...")
    query = """
        SELECT 
            dg.genre_name,
            AVG(CASE WHEN f.is_grammy_winner THEN f.popularity END) AS pop_winners,
            AVG(CASE WHEN NOT f.is_grammy_winner THEN f.popularity END) AS pop_general
        FROM fact_music_performance f
        JOIN dim_genre dg ON dg.genre_sk = f.genre_sk
        GROUP BY dg.genre_name
        HAVING COUNT(CASE WHEN f.is_grammy_winner THEN 1 END) >= 5
        ORDER BY (AVG(CASE WHEN f.is_grammy_winner THEN f.popularity END) - AVG(CASE WHEN NOT f.is_grammy_winner THEN f.popularity END)) DESC
        LIMIT 8;
    """
    df = pd.read_sql(query, engine)
    df_melted = df.melt(id_vars="genre_name", var_name="Segment", value_name="Mean Popularity")
    df_melted["Segment"] = df_melted["Segment"].replace({"pop_winners": "Grammy Winners", "pop_general": "General Catalog"})
    df_melted["genre_name"] = df_melted["genre_name"].str.title()

    plt.figure(figsize=(10, 5))
    sns.barplot(data=df_melted, x="genre_name", y="Mean Popularity", hue="Segment", palette=["#e67e22", "#95a5a6"])
    plt.title("KPI 2: Top Genres with Largest Grammy Popularity Uplift", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Music Genre", fontsize=11)
    plt.ylabel("Popularity Index (0 - 100)", fontsize=11)
    plt.xticks(rotation=20)
    plt.legend(title="Segment", loc="upper right")
    plt.tight_layout()
    out_path = "docs/evidence/kpi2_genre_popularity.png"
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[+] KPI 2 saved to: {out_path}")

def generate_kpi3():
    print("[*] Generating KPI 3: Historical Trends in Explicit & Collaboration Content...")
    query = """
        SELECT 
            dtm.decade,
            ROUND(COUNT(CASE WHEN dt.explicit THEN 1 END)::NUMERIC / COUNT(*) * 100, 2) AS pct_explicit,
            ROUND(COUNT(CASE WHEN da.artist_type = 'Collaboration' THEN 1 END)::NUMERIC / COUNT(*) * 100, 2) AS pct_collaborations
        FROM fact_music_performance f
        JOIN dim_time dtm ON dtm.time_sk = f.time_sk
        JOIN dim_track dt ON dt.track_sk = f.track_sk
        JOIN dim_artist da ON da.artist_sk = f.artist_sk
        WHERE f.is_grammy_winner = TRUE AND dtm.time_sk > 0
        GROUP BY dtm.decade
        ORDER BY dtm.decade ASC;
    """
    df = pd.read_sql(query, engine)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(df["decade"], df["pct_explicit"], marker="o", linewidth=2.5, label="% Explicit Content Tracks", color="#e74c3c")
    ax.plot(df["decade"], df["pct_collaborations"], marker="s", linewidth=2.5, label="% Collaboration Tracks (Feat.)", color="#2980b9")
    plt.title("KPI 3: Historical Decade Evolution of Grammy-Awarded Tracks", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Award Decade", fontsize=11)
    plt.ylabel("Share of Awarded Tracks (%)", fontsize=11)
    plt.ylim(0, 55)
    for _, row in df.iterrows():
        ax.annotate(f"{row['pct_explicit']:.1f}%", (row["decade"], row["pct_explicit"] + 2), ha="center", fontsize=8.5, color="#c0392b")
        ax.annotate(f"{row['pct_collaborations']:.1f}%", (row["decade"], row["pct_collaborations"] + 2), ha="center", fontsize=8.5, color="#2471a3")
    plt.legend(loc="upper left", frameon=True)
    plt.tight_layout()
    out_path = "docs/evidence/kpi3_temporal_trends.png"
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[+] KPI 3 saved to: {out_path}")

if __name__ == "__main__":
    generate_kpi1()
    generate_kpi2()
    generate_kpi3()
    print("[+] All English analytical visualization charts rendered successfully.")
