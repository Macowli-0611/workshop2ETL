#!/usr/bin/env python3
"""
Generador de Visualizaciones y KPIs desde el Data Warehouse: scripts/generate_kpi_charts.py
----------------------------------------------------------------------------------------
Consulta directamente el modelo dimensional en PostgreSQL (dw_music_analytics)
y genera las figuras requeridas para la Sección 8.1 del Brief.
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
    print("[*] Generando KPI 1: Perfil Acústico Comparativo...")
    query = """
        SELECT 
            CASE WHEN is_grammy_winner THEN 'Ganador Grammy' ELSE 'Catálogo General' END AS estatus,
            AVG(danceability) AS danceability,
            AVG(energy) AS energy,
            AVG(valence) AS valence,
            AVG(acousticness) AS acousticness
        FROM fact_music_performance
        GROUP BY is_grammy_winner;
    """
    df = pd.read_sql(query, engine)
    df_melted = df.melt(id_vars="estatus", var_name="Métrica Acústica", value_name="Valor Promedio")

    plt.figure(figsize=(9, 5))
    ax = sns.barplot(data=df_melted, x="Métrica Acústica", y="Valor Promedio", hue="estatus", palette=["#3498db", "#e67e22"])
    plt.title("KPI 1: Perfil Acústico Comparativo (Ganadores Grammy vs Catálogo General)", fontsize=13, fontweight="bold", pad=15)
    plt.ylabel("Valor Promedio [0.0 - 1.0]")
    plt.ylim(0, 1.0)
    for p in ax.patches:
        h = p.get_height()
        if h > 0:
            ax.annotate(f"{h:.2f}", (p.get_x() + p.get_width() / 2., h / 2), ha="center", va="center", color="white", fontweight="bold", fontsize=9)
    plt.tight_layout()
    out_path = "docs/evidence/kpi1_audio_profile.png"
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[+] KPI 1 guardado en: {out_path}")

def generate_kpi2():
    print("[*] Generando KPI 2: Multiplicador de Popularidad por Género...")
    query = """
        SELECT 
            dg.genre_name,
            AVG(CASE WHEN f.is_grammy_winner THEN f.popularity END) AS pop_ganadores,
            AVG(CASE WHEN NOT f.is_grammy_winner THEN f.popularity END) AS pop_general
        FROM fact_music_performance f
        JOIN dim_genre dg ON dg.genre_sk = f.genre_sk
        GROUP BY dg.genre_name
        HAVING COUNT(CASE WHEN f.is_grammy_winner THEN 1 END) >= 5
        ORDER BY (AVG(CASE WHEN f.is_grammy_winner THEN f.popularity END) - AVG(CASE WHEN NOT f.is_grammy_winner THEN f.popularity END)) DESC
        LIMIT 8;
    """
    df = pd.read_sql(query, engine)
    df_melted = df.melt(id_vars="genre_name", var_name="Segmento", value_name="Popularidad Promedio")
    df_melted["Segmento"] = df_melted["Segmento"].replace({"pop_ganadores": "Ganadores Grammy", "pop_general": "Catálogo General"})

    plt.figure(figsize=(10, 5))
    sns.barplot(data=df_melted, x="genre_name", y="Popularidad Promedio", hue="Segmento", palette=["#e67e22", "#95a5a6"])
    plt.title("KPI 2: Top Géneros con Mayor Multiplicador de Popularidad por Galardón Grammy", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Género Musical")
    plt.ylabel("Índice de Popularidad (0 - 100)")
    plt.xticks(rotation=20)
    plt.tight_layout()
    out_path = "docs/evidence/kpi2_genre_popularity.png"
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[+] KPI 2 guardado en: {out_path}")

def generate_kpi3():
    print("[*] Generando KPI 3: Tendencia Histórica de Colaboraciones y Explícito...")
    query = """
        SELECT 
            dtm.decade,
            ROUND(COUNT(CASE WHEN dt.explicit THEN 1 END)::NUMERIC / COUNT(*) * 100, 2) AS pct_explicito,
            ROUND(COUNT(CASE WHEN da.artist_type = 'Collaboration' THEN 1 END)::NUMERIC / COUNT(*) * 100, 2) AS pct_colaboraciones
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
    ax.plot(df["decade"], df["pct_explicito"], marker="o", linewidth=2.5, label="% Canciones con Letra Explícita", color="#e74c3c")
    ax.plot(df["decade"], df["pct_colaboraciones"], marker="s", linewidth=2.5, label="% Colaboraciones (Featurings)", color="#2980b9")
    plt.title("KPI 3: Evolución Temporal de Canciones Ganadoras de Grammy por Década", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Década de Premiación")
    plt.ylabel("Porcentaje (%) de Canciones Ganadoras")
    plt.ylim(0, 55)
    for _, row in df.iterrows():
        ax.annotate(f"{row['pct_explicito']:.1f}%", (row["decade"], row["pct_explicito"] + 2), ha="center", fontsize=8, color="#c0392b")
        ax.annotate(f"{row['pct_colaboraciones']:.1f}%", (row["decade"], row["pct_colaboraciones"] + 2), ha="center", fontsize=8, color="#2471a3")
    plt.legend(loc="upper left")
    plt.tight_layout()
    out_path = "docs/evidence/kpi3_temporal_trends.png"
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[+] KPI 3 guardado en: {out_path}")

if __name__ == "__main__":
    generate_kpi1()
    generate_kpi2()
    generate_kpi3()
    print("[+] Todas las visualizaciones fueron generadas exitosamente.")
