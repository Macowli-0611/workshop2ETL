"""
Automated Data Quality Validation Module: src/validation.py
-----------------------------------------------------------
Implements quality validation gates using Great Expectations (GX):
- Raw Data Validation Gates (Spotify Raw, Grammys Raw).
- Prepared Data Validation Gate (Integrated ready-to-load dataset).

Enforces operational policy based on severity levels (Section 6.5 & 6.6):
- Critical: Raises CriticalDataQualityError, halting affected downstream pipeline branches.
- Warning: Emits warning logs, records metrics in audit summary, allows progression.
- Informational: Preserves trend and context signals without blocking execution.
"""

import os
import json
import logging
import pandas as pd
import great_expectations as gx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ETL_Validation")

class CriticalDataQualityError(Exception):
    """Exception raised when a Critical severity quality rule is violated."""
    pass

def _save_validation_result(result_dict: dict, output_path: str):
    """Persists machine-readable validation results to disk for auditability."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2, default=str)
    logger.info(f"Validation evidence artifact saved to: {output_path}")

def validate_spotify_raw(raw_path: str, report_path: str = "gx/results/spotify_raw_validation.json") -> dict:
    """
    Raw Validation Gate: Spotify Dataset.
    Answers: Is incoming Spotify data safe enough to enter transformation?
    Evaluates: DQ-RAW-SPT-01 through DQ-RAW-SPT-04.
    """
    logger.info(f"Executing Raw Validation Gate for Spotify: {raw_path}")
    df = pd.read_parquet(raw_path) if raw_path.endswith(".parquet") else pd.read_csv(raw_path)

    context = gx.get_context()
    data_source = context.data_sources.add_pandas("pandas_spotify_raw")
    data_asset = data_source.add_dataframe_asset("spotify_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("spotify_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name="spotify_raw_suite")

    # DQ-RAW-SPT-01 [Critical]: track_id must be 100% non-null
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
        column="track_id",
        notes="DQ-RAW-SPT-01 [Critical]: Technical track identifier must be 100% non-null."
    ))

    # DQ-RAW-SPT-02 [Critical]: duration_ms > 1000 ms (Raw tolerance: mostly=0.999)
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
        column="duration_ms",
        min_value=1000,
        mostly=0.999,
        notes="DQ-RAW-SPT-02 [Critical]: Track physical duration must exceed 1,000 ms in at least 99.9% of the raw batch."
    ))

    # DQ-RAW-SPT-03 [Critical]: Audio features normalized in [0.0, 1.0]
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
        column="danceability",
        min_value=0.0,
        max_value=1.0,
        notes="DQ-RAW-SPT-03 [Critical]: Danceability must be within normalized bounds [0.0, 1.0]."
    ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
        column="energy",
        min_value=0.0,
        max_value=1.0,
        notes="DQ-RAW-SPT-03 [Critical]: Energy must be within normalized bounds [0.0, 1.0]."
    ))

    # DQ-RAW-SPT-04 [Critical]: Popularity integer bounded [0, 100]
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
        column="popularity",
        min_value=0,
        max_value=100,
        notes="DQ-RAW-SPT-04 [Critical]: Popularity index must be within integer bounds [0, 100]."
    ))

    validation_result = batch.validate(suite)

    audit_summary = {
        "dataset": "spotify_raw",
        "file_path": raw_path,
        "total_records": len(df),
        "success": validation_result.success,
        "rules_evaluated": []
    }

    critical_failures = []
    for res in validation_result.results:
        rule_note = res.expectation_config.notes or "Unspecified rule"
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
        error_msg = f"Critical Quality Gate Failure in Spotify Raw: {', '.join(critical_failures)}"
        logger.error(error_msg)
        raise CriticalDataQualityError(error_msg)

    logger.info("Raw Validation Gate for Spotify: PASSED successfully.")
    return audit_summary

def validate_grammys_raw(raw_path: str, report_path: str = "gx/results/grammys_raw_validation.json") -> dict:
    """
    Raw Validation Gate: Grammy Awards.
    Answers: Are relational Grammy records safe enough to enter transformation?
    Evaluates: DQ-RAW-GRM-01 and DQ-RAW-GRM-02.
    """
    logger.info(f"Executing Raw Validation Gate for Grammys: {raw_path}")
    df = pd.read_parquet(raw_path) if raw_path.endswith(".parquet") else pd.read_csv(raw_path)

    context = gx.get_context()
    data_source = context.data_sources.add_pandas("pandas_grammys_raw")
    data_asset = data_source.add_dataframe_asset("grammys_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("grammys_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name="grammys_raw_suite")

    # DQ-RAW-GRM-01 [Critical]: Award year within [1958, 2026]
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
        column="year",
        min_value=1958,
        max_value=2026,
        notes="DQ-RAW-GRM-01 [Critical]: Award year must fall within historical Academy range [1958, 2026]."
    ))

    # DQ-RAW-GRM-02 [Warning]: Nominee mostly non-null (>= 99.5%)
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
        column="nominee",
        mostly=0.995,
        notes="DQ-RAW-GRM-02 [Warning]: Nominee title must be populated in at least 99.5% of raw records."
    ))

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
        rule_note = res.expectation_config.notes or "Unspecified rule"
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
                logger.warning(f"Warning in Grammys Raw Gate: {rule_note} was partially violated but satisfies Warning tolerance threshold.")

    _save_validation_result(audit_summary, report_path)

    if critical_failures:
        error_msg = f"Critical Quality Gate Failure in Grammys Raw: {', '.join(critical_failures)}"
        logger.error(error_msg)
        raise CriticalDataQualityError(error_msg)

    logger.info("Raw Validation Gate for Grammys: PASSED successfully.")
    return audit_summary

def validate_prepared(prepared_path: str, report_path: str = "gx/results/prepared_validation.json") -> dict:
    """
    Prepared Data Validation Gate.
    Answers: Did transformation produce acceptable, load-ready dimensional data?
    Evaluates: DQ-PREP-INT-01, DQ-PREP-INT-02 and post-transformation invariants.
    """
    logger.info(f"Executing Prepared Validation Gate: {prepared_path}")
    df = pd.read_parquet(prepared_path) if prepared_path.endswith(".parquet") else pd.read_csv(prepared_path)

    context = gx.get_context()
    data_source = context.data_sources.add_pandas("pandas_prepared")
    data_asset = data_source.add_dataframe_asset("prepared_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("prepared_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name="prepared_music_suite")

    # DQ-PREP-INT-02 [Critical]: Dimension natural business keys and titles non-null
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
        column="track_id_spotify",
        notes="DQ-PREP-INT-02 [Critical]: Prepared track natural key must be 100% non-null."
    ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
        column="track_name",
        notes="DQ-PREP-INT-02 [Critical]: Clean track title must be 100% non-null."
    ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
        column="artist_name",
        notes="DQ-PREP-INT-02 [Critical]: Clean primary artist must be 100% non-null."
    ))

    # DQ-PREP-INT-01 [Informational]: Award boolean indicator in allowed domain
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
        column="is_grammy_winner",
        value_set=[True, False],
        notes="DQ-PREP-INT-01 [Informational]: Award recognition flag must be a valid boolean."
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
        rule_note = res.expectation_config.notes or "Unspecified rule"
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
        error_msg = f"Critical Prepared Validation Gate Failure: {', '.join(critical_failures)}"
        logger.error(error_msg)
        raise CriticalDataQualityError(error_msg)

    logger.info("Prepared Validation Gate: PASSED. Dataset is verified load-ready for DW.")
    return audit_summary
