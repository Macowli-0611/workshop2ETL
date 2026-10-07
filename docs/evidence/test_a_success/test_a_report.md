# Reporte de Evidencia: Test A — Ejecución Exitosa Completa
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Curso: ETL (G01) — Apache Airflow 3.1.8*

---

## 1. Identificadores de Ejecución
* **DAG ID:** `reliable_music_pipeline`
* **DAG Run ID:** `manual__2026-10-07T22:30:45.658550+00:00`
* **Estado Final:** `success`
* **Inicio:** `2026-10-07T22:30:46.044064+00:00`
* **Fin:** `2026-10-07T22:31:25.180737+00:00`
* **Duración Total:** 39.14 segundos

---

## 2. Registro de Estados de Instancias de Tarea (Task Instances)

| Tarea (`task_id`) | Rama / Etapa | Estado | Inicio (UTC) | Fin (UTC) | Duración |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `extract_spotify` | Spotify Branch (CSV) | **success** | 22:30:46 | 22:30:49 | 3.8s |
| `extract_grammys` | Grammy Branch (PostgreSQL) | **success** | 22:30:46 | 22:30:49 | 3.4s |
| `validate_spotify_raw` | Raw Validation Gate | **success** | 22:30:50 | 22:30:59 | 9.6s |
| `validate_grammys_raw` | Raw Validation Gate | **success** | 22:30:50 | 22:30:59 | 9.1s |
| `transform_and_integrate`| Convergence & Cleaning | **success** | 22:31:00 | 22:31:02 | 1.9s |
| `validate_prepared` | Prepared Validation Gate | **success** | 22:31:02 | 22:31:08 | 5.7s |
| `load_dw` | Star Schema Load | **success** | 22:31:08 | 22:31:24 | 16.5s |

---

## 3. Reconciliación de Datos y Conteos en el Data Warehouse

* **Total de registros en `fact_music_performance`:** 113,549 filas
* **Total de pistas galardonadas con Grammy en DW:** 475 pistas
* **Total de artistas únicos en `dim_artist`:** 17,645 artistas
* **Total de pistas únicas en `dim_track`:** 89,740 canciones
* **Total de géneros musicales en `dim_genre`:** 114 géneros
* **Total de categorías de premios en `dim_grammy_category`:** 192 categorías activas con coincidencia

---

## 4. Conclusión de Ingeniería
El flujo completó su ciclo de extremo a extremo sin intervención manual, verificando que:
1. Las fuentes heterogéneas fueron extraídas correctamente (Spotify desde archivo y Grammys desde base de datos relacional).
2. Las compuertas de validación de Great Expectations para datos crudos y preparados evaluaron y aprobaron el lote.
3. Las dimensiones y la tabla de hechos se poblaron con éxito en el Data Warehouse.
