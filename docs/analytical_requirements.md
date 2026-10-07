# Documento de Requisitos Analíticos y Alcance (Fase 0)
**Workshop-2: Building a Reliable Batch Data Pipeline**
*Curso: ETL (G01) — Universidad Autónoma de Occidente*

---

## 1. Declaración de Alcance (*Scope Statement*)
El presente proyecto tiene como objetivo diseñar e implementar un sistema de ingeniería de datos por lotes (batch) que integre dos fuentes de datos no homogéneas: el catálogo y características sonoras de canciones de **Spotify** (`spotify_dataset.csv`) y el registro histórico de nominaciones y premiaciones de los **Grammy Awards** (`the_grammy_awards.csv` alojado en base de datos relacional PostgreSQL).

El Data Warehouse dimensional resultante soportará la toma de decisiones estratégicas de la industria musical, permitiendo a analistas de producto y directores de A&R (Artistas y Repertorio) evaluar el impacto tangible del reconocimiento académico/institucional (Grammys) sobre el consumo digital y perfil sonoro de las pistas musicales.

---

## 2. Matriz de Requisitos Analíticos (Sección 6.1 del Brief)

| ID | Requisito Analítico | Pregunta de Negocio / Decisión Soportada | Atributos Requeridos | Fuentes | KPI(s) Esperado(s) | Nivel de Detalle (Grano) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RQ-01** | **Perfil Acústico y Sonoro de Canciones Premiadas vs. No Premiadas** | ¿Existen patrones sonoros diferenciales (Danceability, Energy, Valence, Acousticness) que distingan a las canciones ganadoras y nominadas de las pistas del catálogo general? *Decisión: Optimización de producción y curaduría para postulaciones a premios.* | `track_name`, `artists`, `danceability`, `energy`, `valence`, `acousticness`, `tempo`, `nominee`, `artist`, `winner`, `category`, `year` | **Spotify:** Métricas de audio y nombres.<br>**Grammys:** Categoría, estado (ganador/nominado) y año. | **KPI 1.1:** Índice de Diferencial Acústico (*Avg Feature Score Ratio* Ganador vs No Nominado).<br>**KPI 1.2:** Perfil Sonoro Promedio por Estado de Galardón (*Danceability / Energy Radar*). | Por pista musical (`track_id`), año de premiación y categoría Grammy. |
| **RQ-02** | **Impacto del Galardón Grammy en la Popularidad por Género Musical** | ¿Cómo varía la distribución del índice de popularidad en Spotify entre canciones ganadoras, nominadas y no nominadas a través de diferentes géneros? *Decisión: Asignación de presupuesto de marketing y promoción según género.* | `track_genre`, `popularity`, `track_name`, `artists`, `nominee`, `artist`, `winner`, `category` | **Spotify:** `track_genre`, `popularity`.<br>**Grammys:** `category`, `winner`. | **KPI 2.1:** Popularidad Promedio por Estatus de Premiación (Ganador vs Nominado vs Sin nominación).<br>**KPI 2.2:** Tasa de Concentración de Alta Popularidad (% canciones con `popularity` > 70 en pistas galardonadas vs catálogo general). | Por género musical (`track_genre`) y estatus de reconocimiento. |
| **RQ-03** | **Tendencia Histórica de Colaboraciones y Contenido Explícito en Premiaciones** | ¿Cómo ha evolucionado la proporción de canciones premiadas con múltiples artistas (colaboraciones) y contenido explícito a lo largo de las décadas en comparación con las tendencias de streaming? *Decisión: Políticas editoriales y contratación de featurings.* | `year`, `explicit`, `artists`, `artist`, `workers`, `winner`, `category`, `nominee` | **Spotify:** `explicit`, lista de artistas colaboradores.<br>**Grammys:** Año de edición, categoría y créditos. | **KPI 3.1:** Tasa de Contenido Explícito Premiado (% de ganadoras con `explicit = True` por década/año).<br>**KPI 3.2:** Ratio de Colaboración (*% tracks con 2 o más artistas acreditados* en galardonados vs catálogo). | Por año de edición de los premios Grammy y década. |

---

## 3. Justificación de la Integración Cruzada
Ninguna de las dos fuentes puede responder a estas necesidades de manera aislada:
1. **Spotify** cuenta con telemetría de consumo (`popularity`) y métricas perceptuales de procesamiento de señales de audio (`danceability`, `energy`, etc.), pero carece de metadatos sobre aclamación de la crítica, nominaciones y premios de la industria.
2. **Grammy Awards** contiene el prestigio y registro oficial histórico de la Recording Academy (desde 1958), pero no incluye métricas de reproducción, atributos acústicos ni categorización estandarizada por géneros de consumo moderno.

La unión contractual y armonización de ambas fuentes crea un activo de datos único que correlaciona mérito artístico institucional con consumo y características perceptuales del audio.

---

## 4. Cadena de Trazabilidad Descendente
Cada uno de los 3 requisitos analíticos anteriores rige las siguientes fases:
* **Fase de Perfilamiento:** Búsqueda activa de discrepancias ortográficas en nombres de artistas (`artists` con separadores `;` vs `artist` en Grammys con conectores tipo `Featuring` o comas), presencia de nulos en `popularity` y valores fuera de escala en atributos acústicos ($[0.0, 1.0]$).
* **Fase de Reglas GX:** Reglas estrictas para asegurar que ningún registro cargado al DW carezca de año válido, métricas sonoras en rango, o identificadores únicos.
* **Modelo Dimensional:** Fact table diseñada para almacenar medidas numéricas (`popularity`, métricas acústicas, conteo de victorias) y dimensiones de contexto (`dim_artist`, `dim_track`, `dim_genre`, `dim_grammy_category`, `dim_time`).
