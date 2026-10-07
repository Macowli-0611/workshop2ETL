# Matriz de Calidad de Datos y Reglas de Validación (Fase 2)
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Curso: ETL (G01) — Universidad Autónoma de Occidente*

---

## 1. Principios de Validación de Ingeniería
1. **Separación de Responsabilidades:** La validación *detecta violaciones y genera evidencia auditable*; la transformación *aplica reglas de ingeniería conocidas*. No se modifican datos para hacer pasar una validación.
2. **Definición de Umbrales Justificada:** Un umbral no se fija porque el lote actual pase por casualidad; se establece en función del riesgo para el requisito analítico protegido.
3. **Severidades Operativas:**
   * **Critical:** Viola la integridad estructural o del negocio. **Detiene inmediatamente el pipeline downstream** (Test B demuestra esta parada).
   * **Warning:** Inconsistencia observable que no invalida el lote entero; se registra en logs y métricas y continúa bajo política documentada.
   * **Informational:** Registro contextual para monitoreo de tendencias y salud general de las fuentes.

---

## 2. Matriz de Reglas de Calidad (Sección 6.5 del Brief)

Se definen **8 reglas de calidad** distribuidas a lo largo del pipeline (Compuertas Raw y Prepared), superando el mínimo de 6 requerido:

| Rule ID | Dataset / Capa | Atributo(s) | Dimensión de Calidad | Regla de Calidad (Quality Rule) | Métrica / Umbral Aceptable | Severidad | Requisito Relacionado | Justificación de Ingeniería |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DQ-RAW-SPT-01** | Spotify / Raw | `track_id` | **Uniqueness & Completeness** | El identificador de pista no debe ser nulo. | Nulos = 0 (100% no nulo). | **Critical** | RQ-01, RQ-02 | Clave primaria técnica del catálogo digital; nulos rompen el seguimiento analítico. |
| **DQ-RAW-SPT-02** | Spotify / Raw | `duration_ms` | **Validity & Physical Plausibility** | La duración de la pista debe ser estrictamente positiva (> 1,000 ms). | Filas con `duration_ms <= 1000` = 0. | **Critical** | RQ-03 | El perfilamiento detectó registros con duración = 0 ms (pistas fantasma/corruptas) que distorsionan promedios. |
| **DQ-RAW-SPT-03** | Spotify / Raw | `danceability`, `energy`, `valence`, `acousticness` | **Validity & Range** | Los atributos acústicos deben encontrarse estrictamente en la escala normalizada $[0.0, 1.0]$. | 100% de los valores en rango $[0.0, 1.0]$. | **Critical** | RQ-01 | Valores fuera de rango desvirtúan los algoritmos de clustering y radar charts de audio. |
| **DQ-RAW-SPT-04** | Spotify / Raw | `popularity` | **Validity & Range** | El índice de popularidad debe estar en la escala de enteros $[0, 100]$. | 100% de los valores en rango $[0, 100]$. | **Critical** | RQ-02 | Métricas fuera de escala invalidan el cálculo de percentiles y KPIs de popularidad. |
| **DQ-RAW-GRM-01** | Grammys / Raw | `year` | **Validity & Temporal Range** | El año de premiación debe ser un entero entre 1958 (primer Grammy) y el año actual (<= 2026). | 100% de los valores en rango $[1958, 2026]$. | **Critical** | RQ-01, RQ-03 | Años inválidos o nulos destruyen la jerarquía de la dimensión tiempo y series temporales. |
| **DQ-RAW-GRM-02** | Grammys / Raw | `nominee` | **Completeness** | La obra o canción nominada no debe ser nula. | Nulos <= 0.2% del total de registros. | **Warning** | RQ-01, RQ-02 | El perfilamiento identificó 6 nulos (0.12%) en categorías especiales. No detiene el lote pero se aísla. |
| **DQ-PREP-INT-01** | Prepared / Gate | `is_grammy_winner` | **Consistency & Cross-Matching** | La bandera de premiación debe ser booleana y la tasa de empate debe mantenerse en el rango esperado. | Tasa de coincidencia de catálogo entre 0.5% y 5.0%. | **Informational** | RQ-01, RQ-02 | Monitorea la estabilidad del volumen de coincidencias entre lotes periódicos. |
| **DQ-PREP-INT-02** | Prepared / Gate | `track_sk`, `artist_name`, `track_name` | **Integrity & Dimensional Readiness** | Ningún registro preparado para el Data Warehouse debe tener claves de dimensión nulas o nombres vacíos. | 0% nulos en atributos clave de dimensión. | **Critical** | RQ-01, RQ-02, RQ-03 | Garantiza la integridad referencial antes de ejecutar el DDL de carga al Data Warehouse. |

---

## 3. Mapeo a Great Expectations (GX Expectation Suites)

### 3.1 Suite Raw Spotify: `spotify_raw_suite`
* `expect_column_values_to_not_be_null(column="track_id")` ➔ **DQ-RAW-SPT-01**
* `expect_column_values_to_be_between(column="duration_ms", min_value=1000)` ➔ **DQ-RAW-SPT-02**
* `expect_column_values_to_be_between(column="danceability", min_value=0.0, max_value=1.0)` ➔ **DQ-RAW-SPT-03**
* `expect_column_values_to_be_between(column="energy", min_value=0.0, max_value=1.0)` ➔ **DQ-RAW-SPT-03**
* `expect_column_values_to_be_between(column="popularity", min_value=0, max_value=100)` ➔ **DQ-RAW-SPT-04**

### 3.2 Suite Raw Grammys: `grammys_raw_suite`
* `expect_column_values_to_be_between(column="year", min_value=1958, max_value=2026)` ➔ **DQ-RAW-GRM-01**
* `expect_column_values_to_not_be_null(column="nominee", mostly=0.995)` ➔ **DQ-RAW-GRM-02**

### 3.3 Suite Prepared Integration: `prepared_music_suite`
* `expect_column_values_to_not_be_null(column="track_name")` ➔ **DQ-PREP-INT-02**
* `expect_column_values_to_not_be_null(column="artist_name")` ➔ **DQ-PREP-INT-02**
* `expect_column_values_to_be_in_set(column="is_grammy_winner", value_set=[True, False])` ➔ **DQ-PREP-INT-01**
* `expect_column_values_to_be_between(column="danceability", min_value=0.0, max_value=1.0)` ➔ **Invariant Check**
