# Reporte de Evidencia: Test C — Repetibilidad y Reejecución Segura (Safe Rerun)
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Curso: ETL (G01) — Sección 7.3 del Brief*

---

## 1. Declaración de la Estrategia de Idempotencia
* **Principio de Ingeniería:** *"A rerun must not silently corrupt the analytical target."*
* **Mecanismo Implementado:** Estrategia de **Upsert Controlado / Reemplazo Atómico por Grano de Negocio**.
* **Restricción Clave:**
  ```sql
  CONSTRAINT uq_fact_grain UNIQUE (track_sk, genre_sk, time_sk, category_sk)
  ```
* **Comando SQL de Carga:**
  ```sql
  INSERT INTO fact_music_performance (...)
  SELECT ... FROM temp_prepared_staging
  ON CONFLICT (track_sk, genre_sk, time_sk, category_sk) DO UPDATE
  SET popularity = EXCLUDED.popularity,
      danceability = EXCLUDED.danceability,
      energy = EXCLUDED.energy,
      valence = EXCLUDED.valence,
      acousticness = EXCLUDED.acousticness,
      loudness = EXCLUDED.loudness,
      tempo = EXCLUDED.tempo,
      is_grammy_winner = EXCLUDED.is_grammy_winner,
      is_grammy_nominee = EXCLUDED.is_grammy_nominee,
      award_count = EXCLUDED.award_count,
      batch_id = EXCLUDED.batch_id,
      loaded_at = CURRENT_TIMESTAMP;
  ```

---

## 2. Comparativo Cuantitativo Antes y Después de la Reejecución

| Tabla / Métrica Evaluada | Conteo Previo (Run 1) | Conteo Posterior (Rerun 2) | Variación Neta | Estado de Idempotencia |
| :--- | :---: | :---: | :---: | :---: |
| `fact_music_performance` (Total Filas) | **113,549** | **113,549** | **0** | **100% Idempotente** |
| Pistas Ganadoras de Grammy (`is_grammy_winner = True`) | **475** | **475** | **0** | **Sin duplicados** |
| `dim_artist` (Artistas únicos) | **17,645** | **17,645** | **0** | **Sin duplicados** |
| `dim_track` (Pistas únicas) | **89,740** | **89,740** | **0** | **Sin duplicados** |
| `dim_genre` (Géneros de catálogo) | **114** | **114** | **0** | **Sin duplicados** |
| Suma Total de Medida `popularity` | **3,778,820** | **3,778,820** | **0.0** | **Invariante** |
| Promedio de Medida `danceability` | **0.5670** | **0.5670** | **0.0** | **Invariante** |

---

## 3. Tratamiento de Fallas Parciales
Si una ejecución se interrumpe antes de la tarea de carga, la transacción en PostgreSQL se cancela automáticamente mediante el bloque transaccional `with engine.begin() as conn:`. Al reiniciar el DAG, el rerun sobrescribe o completa las tuplas correspondientes de manera atómica, garantizando que el Data Warehouse nunca quede en un estado inconsistente o semi-cargado.
