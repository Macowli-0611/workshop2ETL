"""
Módulo de Validación Automatizada con Great Expectations: src/validation.py
-------------------------------------------------------------------------
Implementa las compuertas de calidad (Raw Validation Gate y Prepared Validation Gate).
Mapea cada expectativa a su Rule ID correspondiente (Sección 6.5 y 6.6 del Brief).

Severidades:
- Critical: Lanza CriticalDataQualityError y detiene el flujo downstream.
- Warning: Registra advertencia en logs y resultado JSON sin detener el pipeline.
- Informational: Provee contexto y monitoreo de tendencias.
"""

import os
import json
import logging
import pandas as pd
import great_expectations as gx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ETL_Validation")

class CriticalDataQualityError(Exception):
    """Excepción lanzada cuando una regla con severidad Critical falla."""
    pass

def _save_validation_result(result_dict: dict, output_path: str):
    """Guarda el resultado auditable en formato JSON legible por máquina."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2, default=str)
    logger.info(f"Evidencia de validación guardada en: {output_path}")

def validate_spotify_raw(raw_path: str, report_path: str = "gx/results/spotify_raw_validation.json") -> dict:
    """
    Compuerta Raw para Spotify.
    Evalúa si los datos entrantes son seguros para ingresar a transformación.
    """
    logger.info(f"Iniciando validación Raw de Spotify: {raw_path}")
    df = pd.read_parquet(raw_path) if raw_path.endswith(".parquet") else pd.read_csv(raw_path)

    context = gx.get_context()
    data_source = context.data_sources.add_pandas("pandas_spotify_raw")
    data_asset = data_source.add_dataframe_asset("spotify_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("spotify_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name="spotify_raw_suite")

    # Mapeo de reglas a expectativas
    # DQ-RAW-SPT-01 (Critical): track_id no nulo
    exp_track_id = gx.expectations.ExpectColumnValuesToNotBeNull(
        column="track_id",
        notes="DQ-RAW-SPT-01 [Critical]: El ID de pista debe ser 100% no nulo."
    )
    # DQ-RAW-SPT-02 (Critical): duration_ms > 1000 ms (Tolerancia raw: mostly=0.999)
    exp_duration = gx.expectations.ExpectColumnValuesToBeBetween(
        column="duration_ms",
        min_value=1000,
        mostly=0.999,
        notes="DQ-RAW-SPT-02 [Critical]: La duración física debe ser mayor a 1,000 ms en al menos el 99.9% del lote raw."
    )
    # DQ-RAW-SPT-03 (Critical): danceability y energy en [0.0, 1.0]
    exp_danceability = gx.expectations.ExpectColumnValuesToBeBetween(
        column="danceability",
        min_value=0.0,
        max_value=1.0,
        notes="DQ-RAW-SPT-03 [Critical]: Danceability debe estar en escala normalizada [0.0, 1.0]."
    )
    exp_energy = gx.expectations.ExpectColumnValuesToBeBetween(
        column="energy",
        min_value=0.0,
        max_value=1.0,
        notes="DQ-RAW-SPT-03 [Critical]: Energy debe estar en escala normalizada [0.0, 1.0]."
    )
    # DQ-RAW-SPT-04 (Critical): popularity en [0, 100]
    exp_popularity = gx.expectations.ExpectColumnValuesToBeBetween(
        column="popularity",
        min_value=0,
        max_value=100,
        notes="DQ-RAW-SPT-04 [Critical]: Popularidad debe estar en rango [0, 100]."
    )

    suite.add_expectation(exp_track_id)
    suite.add_expectation(exp_duration)
    suite.add_expectation(exp_danceability)
    suite.add_expectation(exp_energy)
    suite.add_expectation(exp_popularity)

    validation_result = batch.validate(suite)

    # Estructurar resultado auditable
    audit_summary = {
        "dataset": "spotify_raw",
        "file_path": raw_path,
        "total_records": len(df),
        "success": validation_result.success,
        "rules_evaluated": []
    }

    critical_failures = []
    for res in validation_result.results:
        rule_note = res.expectation_config.notes or "Regla no especificada"
        rule_success = res.success
        rule_details = {
            "expectation_type": res.expectation_config.type,
            "rule_description": rule_note,
            "success": rule_success,
            "observed_value": res.result
        }
        audit_summary["rules_evaluated"].append(rule_details)

        if not rule_success and "[Critical]" in rule_note:
            critical_failures.append(rule_note)

    _save_validation_result(audit_summary, report_path)

    if critical_failures:
        error_msg = f"Fallo Crítico en Validación Raw Spotify: {', '.join(critical_failures)}"
        logger.error(error_msg)
        raise CriticalDataQualityError(error_msg)

    logger.info("Compuerta Raw Spotify: APROBADA exitosamente.")
    return audit_summary

def validate_grammys_raw(raw_path: str, report_path: str = "gx/results/grammys_raw_validation.json") -> dict:
    """
    Compuerta Raw para Grammy Awards.
    Evalúa la integridad de los datos extraídos de PostgreSQL.
    """
    logger.info(f"Iniciando validación Raw de Grammys: {raw_path}")
    df = pd.read_parquet(raw_path) if raw_path.endswith(".parquet") else pd.read_csv(raw_path)

    context = gx.get_context()
    data_source = context.data_sources.add_pandas("pandas_grammys_raw")
    data_asset = data_source.add_dataframe_asset("grammys_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("grammys_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name="grammys_raw_suite")

    # DQ-RAW-GRM-01 (Critical): year en [1958, 2026]
    exp_year = gx.expectations.ExpectColumnValuesToBeBetween(
        column="year",
        min_value=1958,
        max_value=2026,
        notes="DQ-RAW-GRM-01 [Critical]: El año debe pertenecer al rango histórico válido [1958, 2026]."
    )
    # DQ-RAW-GRM-02 (Warning): nominee mostly no nulo (>= 99.5%)
    exp_nominee = gx.expectations.ExpectColumnValuesToNotBeNull(
        column="nominee",
        mostly=0.995,
        notes="DQ-RAW-GRM-02 [Warning]: Nominee debe ser no nulo en al menos el 99.5% de registros."
    )

    suite.add_expectation(exp_year)
    suite.add_expectation(exp_nominee)

    validation_result = batch.validate(suite)

    audit_summary = {
        "dataset": "grammys_raw",
        "file_path": raw_path,
        "total_records": len(df),
        "success": validation_result.success,
        "rules_evaluated": []
    }

    critical_failures = []
    for res in validation_result.results:
        rule_note = res.expectation_config.notes or "Regla"
        rule_success = res.success
        rule_details = {
            "expectation_type": res.expectation_config.type,
            "rule_description": rule_note,
            "success": rule_success,
            "observed_value": res.result
        }
        audit_summary["rules_evaluated"].append(rule_details)

        if not rule_success:
            if "[Critical]" in rule_note:
                critical_failures.append(rule_note)
            elif "[Warning]" in rule_note:
                logger.warning(f"Advertencia en Grammys Raw: {rule_note} no cumplió el 100%, pero cumple umbral permisivo.")

    _save_validation_result(audit_summary, report_path)

    if critical_failures:
        error_msg = f"Fallo Crítico en Validación Raw Grammys: {', '.join(critical_failures)}"
        logger.error(error_msg)
        raise CriticalDataQualityError(error_msg)

    logger.info("Compuerta Raw Grammys: APROBADA exitosamente.")
    return audit_summary

def validate_prepared(prepared_path: str, report_path: str = "gx/results/prepared_validation.json") -> dict:
    """
    Compuerta Prepared Data Validation.
    Evalúa el dataset integrado y transformado antes de permitir la carga en el DW.
    """
    logger.info(f"Iniciando validación Prepared Data: {prepared_path}")
    df = pd.read_parquet(prepared_path) if prepared_path.endswith(".parquet") else pd.read_csv(prepared_path)

    context = gx.get_context()
    data_source = context.data_sources.add_pandas("pandas_prepared")
    data_asset = data_source.add_dataframe_asset("prepared_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("prepared_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name="prepared_music_suite")

    # DQ-PREP-INT-02 (Critical): track_id_spotify, track_name, artist_name no nulos
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
        column="track_id_spotify",
        notes="DQ-PREP-INT-02 [Critical]: Clave de negocio de track no nula."
    ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
        column="track_name",
        notes="DQ-PREP-INT-02 [Critical]: Nombre de canción no nulo."
    ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
        column="artist_name",
        notes="DQ-PREP-INT-02 [Critical]: Artista normalizado no nulo."
    ))
    # DQ-PREP-INT-01 (Informational/Warning): is_grammy_winner en [True, False]
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
        column="is_grammy_winner",
        value_set=[True, False],
        notes="DQ-PREP-INT-01 [Informational]: Bandera de premio booleana válida."
    ))

    validation_result = batch.validate(suite)

    audit_summary = {
        "dataset": "prepared_music_data",
        "file_path": prepared_path,
        "total_records": len(df),
        "success": validation_result.success,
        "rules_evaluated": []
    }

    critical_failures = []
    for res in validation_result.results:
        rule_note = res.expectation_config.notes or "Regla"
        rule_success = res.success
        rule_details = {
            "expectation_type": res.expectation_config.type,
            "rule_description": rule_note,
            "success": rule_success,
            "observed_value": res.result
        }
        audit_summary["rules_evaluated"].append(rule_details)

        if not rule_success and "[Critical]" in rule_note:
            critical_failures.append(rule_note)

    _save_validation_result(audit_summary, report_path)

    if critical_failures:
        error_msg = f"Fallo Crítico en Validación Prepared: {', '.join(critical_failures)}"
        logger.error(error_msg)
        raise CriticalDataQualityError(error_msg)

    logger.info("Compuerta Prepared Data: APROBADA exitosamente para carga al DW.")
    return audit_summary
