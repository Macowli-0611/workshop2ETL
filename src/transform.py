"""
Módulo de Transformación e Integración: src/transform.py
-------------------------------------------------------
Implementa la fase única de ingeniería que aplica:
- Limpieza y desduplicación basadas en evidencia del perfilamiento.
- Armonización y normalización textual (contrato de integración).
- Cruce entre catálogo de Spotify y premios Grammy.
- Derivación de medidas y atributos para el modelo dimensional.

Contrato de Integración:
- Claves de cruce: (normalized_track_name, normalized_artist)
- Cardinalidad: N-a-1 (múltiples apariciones de un track en diferentes géneros hacia su galardón).
- Registros no coincidentes: Preservados con bandera is_grammy_winner = False y categoría por defecto.
"""

import os
import re
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ETL_Transform")

def _normalize_string(text_val: str) -> str:
    """Normaliza cadenas de texto para emparejamiento determinístico."""
    if pd.isna(text_val):
        return ""
    text_clean = str(text_val).lower().strip()
    # Eliminar signos de puntuación periféricos y comillas
    text_clean = re.sub(r'["\'\(\)\[\],.;:!?\-]', ' ', text_clean)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    return text_clean

def _extract_primary_artist(artist_str: str) -> str:
    """Extrae el artista principal para normalizar colaboraciones."""
    if pd.isna(artist_str):
        return "Unknown Artist"
    # En Spotify vienen separados por ';'
    first_part = str(artist_str).split(";")[0]
    # En Grammys pueden venir con Featuring, &, with
    first_part = re.split(r'\b(featuring|feat\.|&|with)\b', first_part, flags=re.IGNORECASE)[0]
    return first_part.strip()

def transform_and_integrate(spotify_raw_path: str, grammys_raw_path: str, output_path: str) -> str:
    """
    Ejecuta la limpieza, armonización, cruce e integración de datos.
    Guarda el dataset preparado en output_path (Parquet) y retorna su ruta.
    """
    logger.info("Iniciando fase de transformación e integración...")

    # 1. Cargar fuentes crudas
    df_spotify = pd.read_parquet(spotify_raw_path) if spotify_raw_path.endswith(".parquet") else pd.read_csv(spotify_raw_path)
    df_grammys = pd.read_parquet(grammys_raw_path) if grammys_raw_path.endswith(".parquet") else pd.read_csv(grammys_raw_path)

    initial_spotify_rows = len(df_spotify)
    initial_grammy_rows = len(df_grammys)
    logger.info(f"Registros entrantes: Spotify={initial_spotify_rows:,}, Grammys={initial_grammy_rows:,}")

    # 2. Limpieza de Spotify basada en evidencia de perfilamiento
    # Descartar nulos en metadatos críticos
    df_spotify = df_spotify.dropna(subset=["track_name", "artists", "track_id"])
    # Filtrar pistas con duración física inválida (<= 1000 ms)
    df_spotify = df_spotify[df_spotify["duration_ms"] > 1000]
    # Desduplicar tuplas exactas (track_id, track_genre)
    df_spotify = df_spotify.drop_duplicates(subset=["track_id", "track_genre"])

    logger.info(f"Spotify post-limpieza: {len(df_spotify):,} filas (removidas {initial_spotify_rows - len(df_spotify):,} filas inválidas/duplicadas).")

    # 3. Limpieza y preparación de Grammys
    df_grammys = df_grammys.dropna(subset=["nominee"])
    df_grammys["clean_nominee"] = df_grammys["nominee"].apply(_normalize_string)
    df_grammys["clean_grammy_artist"] = df_grammys["artist"].apply(_extract_primary_artist).apply(_normalize_string)

    # Si hay múltiples premios para la misma canción, consolidamos las categorías más representativas
    # Seleccionamos una fila por obra/artista con mayor año y conteo de premios
    grammy_agg = df_grammys.groupby(["clean_nominee", "clean_grammy_artist"]).agg({
        "year": "max",
        "category": "first",
        "winner": "any",
        "title": "count"
    }).reset_index().rename(columns={"title": "award_count", "winner": "is_grammy_winner"})

    # 4. Normalización de Spotify para el Contrato de Integración
    df_spotify["clean_track_name"] = df_spotify["track_name"].apply(_normalize_string)
    df_spotify["primary_artist"] = df_spotify["artists"].apply(_extract_primary_artist)
    df_spotify["clean_spotify_artist"] = df_spotify["primary_artist"].apply(_normalize_string)

    # Identificar tipo de artista
    df_spotify["artist_type"] = np.where(df_spotify["artists"].str.contains(";", na=False), "Collaboration", "Solo")

    # 5. Ejecutar Contrato de Integración (Left Join del catálogo con Grammys)
    # Emparejamiento prioritario: (clean_track_name, clean_spotify_artist)
    df_integrated = df_spotify.merge(
        grammy_agg,
        left_on=["clean_track_name", "clean_spotify_artist"],
        right_on=["clean_nominee", "clean_grammy_artist"],
        how="left"
    )

    # 6. Manejo de Registros No Coincidentes (Unmatched Records)
    df_integrated["is_grammy_winner"] = df_integrated["is_grammy_winner"].fillna(False).astype(bool)
    df_integrated["is_grammy_nominee"] = df_integrated["is_grammy_winner"] # En este dataset todos los registros de premios fueron ganadores/nominados
    df_integrated["award_count"] = df_integrated["award_count"].fillna(0).astype(int)
    df_integrated["grammy_category"] = df_integrated["category"].fillna("Sin Nominación / No Aplica")
    
    # Manejo de dimensión temporal: año de premiación (0 si no aplica)
    df_integrated["award_year"] = df_integrated["year"].fillna(0).astype(int)
    df_integrated["decade"] = np.where(
        df_integrated["award_year"] > 0,
        ((df_integrated["award_year"] // 10) * 10).astype(str) + "s",
        "Desconocida"
    )

    # 7. Formatear y seleccionar columnas preparadas para el Data Warehouse
    prepared_df = pd.DataFrame({
        "track_id_spotify": df_integrated["track_id"],
        "track_name": df_integrated["track_name"],
        "album_name": df_integrated["album_name"].fillna("Sin Álbum"),
        "artist_name": df_integrated["primary_artist"],
        "artist_type": df_integrated["artist_type"],
        "genre_name": df_integrated["track_genre"],
        "duration_ms": df_integrated["duration_ms"].astype(int),
        "explicit": df_integrated["explicit"].astype(bool),
        "popularity": df_integrated["popularity"].astype(int),
        "danceability": df_integrated["danceability"].round(4),
        "energy": df_integrated["energy"].round(4),
        "valence": df_integrated["valence"].round(4),
        "acousticness": df_integrated["acousticness"].round(4),
        "loudness": df_integrated["loudness"].round(3),
        "tempo": df_integrated["tempo"].round(3),
        "grammy_category": df_integrated["grammy_category"],
        "award_year": df_integrated["award_year"],
        "decade": df_integrated["decade"],
        "is_grammy_winner": df_integrated["is_grammy_winner"],
        "is_grammy_nominee": df_integrated["is_grammy_nominee"],
        "award_count": df_integrated["award_count"]
    })

    # Desduplicar tupla final del grano
    prepared_df = prepared_df.drop_duplicates(subset=["track_id_spotify", "genre_name", "award_year", "grammy_category"])

    total_prepared = len(prepared_df)
    total_winners = prepared_df["is_grammy_winner"].sum()
    logger.info(f"Integración completada: {total_prepared:,} filas preparadas.")
    logger.info(f"Pistas con reconocimiento Grammy identificadas: {total_winners:,} ({total_winners / total_prepared * 100:.2f}% del catálogo).")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    prepared_df.to_parquet(output_path, index=False)
    logger.info(f"Dataset preparado guardado en staging: {output_path}")

    return output_path

if __name__ == "__main__":
    out = transform_and_integrate(
        "data/staging/spotify_raw.parquet",
        "data/staging/grammys_raw.parquet",
        "data/staging/prepared_music_data.parquet"
    )
    print("Archivo transformado generado en:", out)
