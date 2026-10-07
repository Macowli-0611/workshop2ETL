# Especificación de Analítica y Dashboard de BI (Sección 8.1)
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Curso: ETL (G01) — Universidad Autónoma de Occidente*

---

## 1. Conexión de BI al Data Warehouse
> **Principio de Evaluación:** *"Direct CSV connections are not accepted as the assessed dashboard solution. The dashboard should answer the analytical requirements using trusted data from the Data Warehouse."*

### Parámetros de Conexión (Power BI / Tableau / Looker Studio):
* **Motor:** PostgreSQL Database
* **Servidor (Host):** `localhost` (o IP del host si corre en contenedor remoto)
* **Puerto:** `5432`
* **Base de Datos:** `dw_music_analytics`
* **Modo de Acceso:** DirectQuery o Import
* **Tablas a Importar / Consultar:**
  * `fact_music_performance` (Tabla de Hechos)
  * `dim_artist`, `dim_track`, `dim_genre`, `dim_time`, `dim_grammy_category` (Dimensiones)

---

## 2. Matriz de KPIs y Visualizaciones Implementadas

| ID KPI | Requisito Analítico | Elemento del DW / Consulta SQL | Tipo de Visualización | Insight Principal Revelado |
| :--- | :--- | :--- | :--- | :--- |
| **KPI-01** | **RQ-01:** Perfil Acústico de Canciones Premiadas vs. No Premiadas | `fact_music_performance` agrupado por `is_grammy_winner` promediando `danceability`, `energy`, `valence`, `acousticness`. | **Gráfico de Barras Agrupadas / Perfil Radar** (`kpi1_audio_profile.png`) | Las canciones ganadoras de Grammy presentan significativamente mayor **Valence** (0.53 vs 0.47) y **Energy** (0.67 vs 0.64), y menor **Acousticness** (0.24 vs 0.31), denotando una preferencia por producciones de alta energía y tono positivo. |
| **KPI-02** | **RQ-02:** Impacto del Galardón en la Popularidad por Género | Join de `fact_music_performance` y `dim_genre`, comparando `popularity` promedio entre ganadores y catálogo general. | **Gráfico de Barras Doble con Delta de Popularidad** (`kpi2_genre_popularity.png`) | Los géneros tradicionales como **Soul** (+45.6 pts) y **Country** (+23.6 pts) experimentan el mayor multiplicador de popularidad digital tras el reconocimiento de la Recording Academy. |
| **KPI-03** | **RQ-03:** Evolución Temporal de Colaboraciones y Contenido Explícito | Join de `fact_music_performance`, `dim_time`, `dim_track` y `dim_artist`, calculando tasas porcentuales por década. | **Gráfico de Líneas Multi-Serie Temporal** (`kpi3_temporal_trends.png`) | Entre los 1950s y 1980s el contenido explícito premiado fue del 0.0%. A partir de los 2000s sube al 10.16% y en los 2010s alcanza el **15.27%**, coincidiendo con una explosión de colaboraciones (**44.27%** de ganadores con múltiples artistas). |

---

## 3. Guía de Reproducción del Dashboard
Para regenerar automáticamente los gráficos de evidencia técnica desde el Data Warehouse:
```bash
python3 scripts/generate_kpi_charts.py
```
Las imágenes generadas de alta resolución se almacenan en:
* `docs/evidence/kpi1_audio_profile.png`
* `docs/evidence/kpi2_genre_popularity.png`
* `docs/evidence/kpi3_temporal_trends.png`
