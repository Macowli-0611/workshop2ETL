# Reporte de Evidencia: Test B — Falla Crítica Controlada de Calidad
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Curso: ETL (G01) — Sección 7.2 del Brief*

---

## 1. Declaración de la Falla Inducida
* **Regla Crítica Evaluada:** `DQ-RAW-GRM-01` [Critical] — *"El año de premiación debe pertenecer al rango histórico válido [1958, 2026]"*.
* **Condición Anómala Activada:** Se inyectó intencionalmente un registro en la base de datos relacional de origen (`source_music_db.grammy_awards`) con `year = 1800` (anterior al origen de la Recording Academy en 1958).
* **DAG Run ID:** `manual__2026-10-07T22:33:55.085717+00:00`

---

## 2. Comportamiento Observado en Apache Airflow 3.1.8

### Tabla de Estados de Tarea (Task Instance States):
```text
dag_id                  | task_id                 | state           | start_date                       | end_date
========================+=========================+=================+==================================+=================================
reliable_music_pipeline | extract_grammys         | success         | 2026-10-07T22:33:55.601128+00:00 | 2026-10-07T22:33:56.276505+00:00
reliable_music_pipeline | extract_spotify         | success         | 2026-10-07T22:33:55.600749+00:00 | 2026-10-07T22:33:56.640342+00:00
reliable_music_pipeline | validate_spotify_raw    | success         | 2026-10-07T22:33:57.688741+00:00 | 2026-10-07T22:34:01.745844+00:00
reliable_music_pipeline | validate_grammys_raw    | failed          | 2026-10-07T22:33:56.635248+00:00 | 2026-10-07T22:34:05.811114+00:00
reliable_music_pipeline | transform_and_integrate | upstream_failed | 2026-10-07T22:34:06.541336+00:00 | 2026-10-07T22:34:06.541336+00:00
reliable_music_pipeline | validate_prepared       | upstream_failed | 2026-10-07T22:34:07.575243+00:00 | 2026-10-07T22:34:07.575243+00:00
reliable_music_pipeline | load_dw                 | upstream_failed | 2026-10-07T22:34:08.606695+00:00 | 2026-10-07T22:34:08.606695+00:00
```

---

## 3. Evidencia Emitida por Great Expectations (`grammys_raw_validation.json`)
```json
{
  "dataset": "grammys_raw",
  "total_records": 4810,
  "success": false,
  "rules_evaluated": [
    {
      "expectation_type": "expect_column_values_to_be_between",
      "rule_description": "DQ-RAW-GRM-01 [Critical]: El año debe pertenecer al rango histórico válido [1958, 2026].",
      "success": false,
      "observed_value": {
        "element_count": 4810,
        "unexpected_count": 1,
        "unexpected_percent": 0.02079,
        "partial_unexpected_list": [ 1800 ]
      }
    }
  ]
}
```

---

## 4. Análisis y Explicación Técnica de Ingeniería
1. **Detección Determinística:** La tarea `extract_grammys` extrajo los datos con éxito; la compuerta `validate_grammys_raw` identificó el año 1800 como una violación a la regla de rango $[1958, 2026]$.
2. **Aislamiento Inmediato (`retries=0`):** Al ser una regla clasificada como `Critical`, la validación arrojó una excepción `CriticalDataQualityError` sin reintentos ciegos, marcando la tarea en estado `failed`.
3. **Bloqueo de Downstream (`upstream_failed`):** El scheduler de Airflow detectó la falla en la dependencia upstream y **bloqueó de inmediato** las tareas de transformación (`transform_and_integrate`), validación preparada (`validate_prepared`) y carga al Data Warehouse (`load_dw`).
4. **Protección del Almacén Analítico:** Ningún dato anómalo o corrupto llegó a la capa dimensional, preservando la pureza y confianza del Data Warehouse.
