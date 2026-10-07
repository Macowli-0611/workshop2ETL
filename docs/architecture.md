# Arquitectura del Sistema y Políticas de Confiabilidad
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Curso: ETL (G01) — Universidad Autónoma de Occidente*

---

## 1. Visión General de la Arquitectura

El sistema implementa un pipeline de datos por lotes (batch) orientado a la confiabilidad, diseñado para integrar datos desacoplados de Spotify y los premios Grammy Awards en un Data Warehouse analítico dimensional en PostgreSQL, orquestado mediante Apache Airflow 3.1.8.

```
+─────────────────────────────────────────────────────────────────────────────────────────────+
|                                     FUENTES DE DATOS                                        |
|  [ Spotify Dataset (CSV local) ]                  [ Grammy Awards (PostgreSQL Operacional) ]|
+──────────────────────────┬───────────────────────────────────────────────────┬──────────────+
                           │                                                   │
+──────────────────────────▼───────────────────────────────────────────────────▼──────────────+
|                                  FASE 1: EXTRACCIÓN (RAMAS PARALELAS)                       |
|  extract_spotify (staging Parquet)                extract_grammys (staging Parquet)         |
+──────────────────────────┬───────────────────────────────────────────────────┬──────────────+
                           │                                                   │
+──────────────────────────▼───────────────────────────────────────────────────▼──────────────+
|                                  FASE 2: COMPUERTA RAW (GREAT EXPECTATIONS)                 |
|  validate_spotify_raw (DQ-RAW-SPT-01..04)         validate_grammys_raw (DQ-RAW-GRM-01..02)  |
+──────────────────────────┬───────────────────────────────────────────────────┬──────────────+
                           └─────────────────────────┬─────────────────────────┘
                                                     │ (Convergencia condicional)
+────────────────────────────────────────────────────▼────────────────────────────────────────+
|                             FASE 3: TRANSFORMACIÓN E INTEGRACIÓN                            |
|  transform_and_integrate:                                                                   |
|   - Limpieza y desduplicación basadas en profiling (remoción de duplicados y duración <= 0) |
|   - Armonización textual (normalización y descomposición de artistas)                       |
|   - Contrato de integración: Left Join (canción, artista) + tratamiento de registros huérfanos |
+────────────────────────────────────────────────────┬────────────────────────────────────────+
                                                     │
+────────────────────────────────────────────────────▼────────────────────────────────────────+
|                             FASE 4: COMPUERTA PREPARED (GREAT EXPECTATIONS)                 |
|  validate_prepared (DQ-PREP-INT-01..02):                                                    |
|   - Verificación de no-nulos en claves de negocio y nombres                                 |
|   - Invariantes acústicos en rango [0.0, 1.0]                                               |
+────────────────────────────────────────────────────┬────────────────────────────────────────+
                                                     │ (Gate de carga)
+────────────────────────────────────────────────────▼────────────────────────────────────────+
|                             FASE 5: CARGA AL DATA WAREHOUSE (POSTGRESQL)                    |
|  load_dw:                                                                                   |
|   - Dimensiones: dim_artist, dim_track, dim_genre, dim_time, dim_grammy_category            |
|   - Hechos: fact_music_performance (Idempotencia garantizada por ON CONFLICT DO UPDATE)     |
+────────────────────────────────────────────────────┬────────────────────────────────────────+
                                                     │
+────────────────────────────────────────────────────▼────────────────────────────────────────+
|                             FASE 6: CONSUMO ANALÍTICO (BI DASHBOARD)                        |
|  Consultas SQL directas al DW / Power BI / Looker Studio:                                   |
|   - KPI 1: Perfil acústico y perceptual de ganadores de Grammy                              |
|   - KPI 2: Multiplicador de popularidad y concentración por género                          |
|   - KPI 3: Tendencia histórica de colaboraciones y contenido explícito                      |
+─────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Principios de Transporte e Interfaces de Tareas (Task Interfaces)
* **Prohibición de Transporte Masivo por XCom:** El paso de DataFrames en memoria a través de la base de metadatos de Airflow está estrictamente prohibido.
* **Patrón Reference-Passing:** Cada tarea de extracción o transformación persiste su salida en disco/volumen compartido (`data/staging/*.parquet`) y retorna exclusivamente una cadena de texto con la ruta del archivo o un diccionario de metadatos ligeros (conteos de filas, estado de validación).

---

## 3. Matriz de Políticas de Fallo y Reintentos Selectivos (Failure Policy)

En observancia a la Sección 6.11 y 6.12 del Brief: *"A blanket policy such as retries=3 everywhere is not evidence of reliability. Justify retry count, delay, and scope for each task class where retries are used."*

| Tarea en el DAG | Condición de Falla Posible | Clase de Falla | Respuesta del Pipeline | Reintentos (`retries`) | Retardo (`retry_delay`) | Justificación Técnica de Ingeniería |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `extract_spotify` | Error de lectura I/O de archivo montado temporalmente no disponible. | Transitoria operacional | Reintento automático acotado. | **2** | 10 segundos | Una demora temporal de montaje en disco o latencia de I/O puede recuperarse sin cambios de código. |
| `extract_grammys` | Pérdida momentánea de conexión TCP a PostgreSQL o saturación de pool. | Transitoria operacional | Reintento con backoff exponencial. | **2** | 10 segundos | La caída transitoria de socket se resuelve al restablecerse el servicio de base de datos. |
| `validate_spotify_raw` | Violación de regla con severidad `Critical` (ej. IDs nulos, corrupción masiva). | Determinística de datos / contrato | Fallo inmediato y detención del flujo descendente. | **0** | N/A | Repetir la validación sobre el mismo archivo corrupto arrojará exactamente el mismo fallo. Reintentar desperdicia recursos y enmascara el incidente. |
| `validate_grammys_raw` | Violación de regla con severidad `Critical` (ej. año de premiación fuera de rango). | Determinística de datos / contrato | Fallo inmediato y detención del flujo descendente. | **0** | N/A | Falla determinística. Requiere remediación en el origen de datos antes de continuar. |
| `transform_and_integrate`| Inconsistencia de tipos o error lógico en el join. | Determinística de código / contrato | Parada del pipeline y registro en traceback. | **0** | N/A | Un error en las reglas de transformación es invariante ante reintentos automáticos. |
| `validate_prepared` | Claves de dimensión nulas o invariantes post-transformación rotos. | Determinística de calidad | Bloqueo preventivo de la tarea de carga `load_dw`. | **0** | N/A | Protege al Data Warehouse de ser contaminado con registros incompletos o inválidos. |
| `load_dw` | Bloqueo transitorio de tabla (*deadlock*) o saturación temporal de transacciones en PostgreSQL. | Transitoria operacional | Reintento acotado. | **1** | 10 segundos | Un deadlock o bloqueo momentáneo de transacción en PostgreSQL puede liberarse en el siguiente intento. |

---

## 4. Estrategia de Idempotencia y Reejecución Segura (Safe Rerun)
Para satisfacer la Sección 7.3:
1. **Clave Única Compuesta del Grano:** La tabla de hechos `fact_music_performance` implementa la restricción única `uq_fact_grain UNIQUE (track_sk, genre_sk, time_sk, category_sk)`.
2. **Carga mediante Upsert Controlado (`ON CONFLICT DO UPDATE`):**
   * Si un registro ya existe en el Data Warehouse, se actualizan sus métricas y se registra el nuevo `batch_id` y fecha de carga.
   * Si no existe, se inserta normalmente.
3. **Efecto de Reejecución:** Reejecutar el pipeline 1, 2 o N veces con el mismo lote produce exactamente **0 duplicados** y mantiene intactos los totales analíticos y las medidas agregadas.
