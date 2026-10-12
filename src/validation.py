"""
Automated Data Quality Validation Module: src/validation.py
-----------------------------------------------------------
Implements the three quality gates with Great Expectations (GX 1.x):
- Raw Data Validation Gates (Spotify Raw, Grammys Raw).
- Prepared Data Validation Gate (integrated, ready-to-load dataset).

GX design (Section 6.6 of the brief), identical for every gate:
  Data Source (pandas) -> Data Asset -> Batch Definition (whole dataframe)
  Expectation Suite    -> one Expectation per declared Rule ID (meta.rule_id / meta.severity)
  Validation Definition = Batch Definition + Expectation Suite
  Checkpoint           -> runs the Validation Definition and returns the result
                          that the pipeline policy below is applied to.

Each run persists, in the run evidence directory, <gate>_validation.json with the
per-rule result and the gate decision. The declarative configuration is exported to
gx/ (expectations/, validation_definitions/, checkpoints/) so it can be inspected
without running the DAG.

Operational severity policy (Section 6.5):
- Critical:      failure raises CriticalDataQualityError -> task fails, downstream is blocked.
- Warning:       failure is logged at WARNING level and recorded; the batch continues.
- Informational: result is recorded for monitoring; it never blocks.
"""

import os
import json
import logging
from datetime import datetime, timezone

import pandas as pd
import great_expectations as gx
import great_expectations.expectations as gxe

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ETL_Validation")

GX_CONFIG_DIR = os.getenv(
    "GX_CONFIG_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gx"),
)

CRITICAL = "Critical"
WARNING = "Warning"
INFORMATIONAL = "Informational"


class CriticalDataQualityError(Exception):
    """Raised when a Critical severity quality rule is violated."""


def _rule(expectation_cls, rule_id: str, severity: str, description: str, **kwargs):
    """Builds an Expectation tagged with its Rule ID and severity."""
    return expectation_cls(
        meta={"rule_id": rule_id, "severity": severity},
        notes=f"{rule_id} [{severity}]: {description}",
        **kwargs,
    )


# ----------------------------------------------------------------------
# Expectation Suites (one per gate). Every Expectation maps to a Rule ID
# documented in docs/quality_rules.md.
# ----------------------------------------------------------------------
AUDIO_FEATURES = ["danceability", "energy", "valence", "acousticness"]

SPOTIFY_REQUIRED_COLUMNS = [
    "track_id", "artists", "album_name", "track_name", "popularity", "duration_ms",
    "explicit", "danceability", "energy", "loudness", "acousticness", "valence",
    "tempo", "track_genre",
]

GRAMMY_REQUIRED_COLUMNS = ["year", "title", "category", "nominee", "artist", "workers", "winner"]

PREPARED_COLUMNS = [
    "track_id_spotify", "track_name", "album_name", "artist_name", "artist_type", "genre_name",
    "duration_ms", "explicit", "popularity", "danceability", "energy", "valence", "acousticness",
    "loudness", "tempo", "grammy_category", "award_year", "decade", "is_grammy_winner",
    "is_grammy_nominee", "award_count",
]


def spotify_raw_expectations() -> list:
    exps = [
        _rule(gxe.ExpectTableColumnsToMatchSet, "DQ-RAW-SPT-05", CRITICAL,
              "Source contract: every column required by RQ-01..RQ-03 must be present.",
              column_set=SPOTIFY_REQUIRED_COLUMNS, exact_match=False),
        _rule(gxe.ExpectColumnValuesToNotBeNull, "DQ-RAW-SPT-01", CRITICAL,
              "Technical track identifier must be 100% non-null.", column="track_id"),
        _rule(gxe.ExpectColumnValuesToBeBetween, "DQ-RAW-SPT-02", CRITICAL,
              "Track duration must exceed 1,000 ms in at least 99.9% of the raw batch.",
              column="duration_ms", min_value=1000, strict_min=True, mostly=0.999),
    ]
    for col in AUDIO_FEATURES:
        exps.append(_rule(gxe.ExpectColumnValuesToBeBetween, "DQ-RAW-SPT-03", CRITICAL,
                          f"{col} must be within the normalized range [0.0, 1.0].",
                          column=col, min_value=0.0, max_value=1.0))
    exps += [
        _rule(gxe.ExpectColumnValuesToBeBetween, "DQ-RAW-SPT-04", CRITICAL,
              "Popularity must be within the integer range [0, 100].",
              column="popularity", min_value=0, max_value=100),
        _rule(gxe.ExpectCompoundColumnsToBeUnique, "DQ-RAW-SPT-06", WARNING,
              "(track_id, track_genre) duplicates must not exceed 1% of the batch "
              "(profiling: 450 = 0.39%).",
              column_list=["track_id", "track_genre"], mostly=0.99),
    ]
    return exps


def grammys_raw_expectations() -> list:
    return [
        _rule(gxe.ExpectTableColumnsToMatchSet, "DQ-RAW-GRM-03", CRITICAL,
              "Source contract: every column required by the integration must be present.",
              column_set=GRAMMY_REQUIRED_COLUMNS, exact_match=False),
        _rule(gxe.ExpectColumnValuesToBeBetween, "DQ-RAW-GRM-01", CRITICAL,
              "Award year must fall within the Recording Academy range [1958, 2026].",
              column="year", min_value=1958, max_value=2026),
        _rule(gxe.ExpectColumnValuesToNotBeNull, "DQ-RAW-GRM-02", WARNING,
              "Nominee title must be populated in at least 99.5% of raw records.",
              column="nominee", mostly=0.995),
        _rule(gxe.ExpectTableRowCountToBeBetween, "DQ-RAW-GRM-04", INFORMATIONAL,
              "Source volume monitor: expected 4,000-10,000 award rows per extraction.",
              min_value=4000, max_value=10000),
    ]


def prepared_expectations() -> list:
    exps = [
        _rule(gxe.ExpectTableColumnsToMatchSet, "DQ-PREP-INT-03", CRITICAL,
              "Prepared schema must match the load contract exactly.",
              column_set=PREPARED_COLUMNS, exact_match=True),
    ]
    for col in ["track_id_spotify", "track_name", "artist_name", "genre_name"]:
        exps.append(_rule(gxe.ExpectColumnValuesToNotBeNull, "DQ-PREP-INT-02", CRITICAL,
                          f"Dimension business key / label {col} must be 100% non-null.", column=col))
    exps.append(_rule(gxe.ExpectColumnValuesToBeBetween, "DQ-PREP-INT-04", CRITICAL,
                      "Popularity must be within [0, 100] after transformation.",
                      column="popularity", min_value=0, max_value=100))
    exps.append(_rule(gxe.ExpectColumnValuesToBeBetween, "DQ-PREP-INT-04", CRITICAL,
                      "Duration must exceed 1,000 ms after cleaning (no tolerance).",
                      column="duration_ms", min_value=1000, strict_min=True))
    for col in AUDIO_FEATURES:
        exps.append(_rule(gxe.ExpectColumnValuesToBeBetween, "DQ-PREP-INT-04", CRITICAL,
                          f"{col} must be within [0.0, 1.0] after transformation.",
                          column=col, min_value=0.0, max_value=1.0))
    exps += [
        _rule(gxe.ExpectCompoundColumnsToBeUnique, "DQ-PREP-INT-05", CRITICAL,
              "Fact grain (track, genre, award year, category) must be unique.",
              column_list=["track_id_spotify", "genre_name", "award_year", "grammy_category"]),
        _rule(gxe.ExpectColumnValuesToBeBetween, "DQ-PREP-INT-06", CRITICAL,
              "Integration integrity: matched (winner) rows must carry a valid award year.",
              column="award_year", min_value=1958, max_value=2026,
              row_condition="is_grammy_winner==True", condition_parser="pandas"),
        _rule(gxe.ExpectColumnValuesToBeBetween, "DQ-PREP-INT-06", CRITICAL,
              "Integration integrity: matched (winner) rows must have award_count >= 1.",
              column="award_count", min_value=1,
              row_condition="is_grammy_winner==True", condition_parser="pandas"),
        _rule(gxe.ExpectColumnValuesToBeBetween, "DQ-PREP-INT-06", CRITICAL,
              "Integration integrity: unmatched rows must map to the default year (0).",
              column="award_year", min_value=0, max_value=0,
              row_condition="is_grammy_winner==False", condition_parser="pandas"),
        _rule(gxe.ExpectColumnDistinctValuesToContainSet, "DQ-PREP-INT-07", CRITICAL,
              "Analytical readiness: both award tiers must exist (zero matches = broken integration).",
              column="is_grammy_winner", value_set=[True, False]),
        _rule(gxe.ExpectColumnValuesToBeInSet, "DQ-PREP-INT-08", WARNING,
              "Match-rate monitor: matched rows must not exceed 5% of the catalog (over-matching risk).",
              column="is_grammy_winner", value_set=[False], mostly=0.95),
        _rule(gxe.ExpectColumnValuesToBeInSet, "DQ-PREP-INT-01", INFORMATIONAL,
              "Award recognition flag must be a valid boolean.",
              column="is_grammy_winner", value_set=[True, False]),
    ]
    return exps


# ----------------------------------------------------------------------
# Generic gate runner: Suite -> Validation Definition -> Checkpoint -> policy
# ----------------------------------------------------------------------
def _export_config(gate: str, suite, source_name: str, asset_name: str, batch_def_name: str,
                   checkpoint_name: str):
    """Writes the declarative GX objects to gx/ so the design is inspectable in the repository."""
    try:
        paths = {
            "suite": os.path.join(GX_CONFIG_DIR, "expectations", f"{suite.name}.json"),
            "vd": os.path.join(GX_CONFIG_DIR, "validation_definitions", f"{gate}_validation_definition.json"),
            "checkpoint": os.path.join(GX_CONFIG_DIR, "checkpoints", f"{checkpoint_name}.json"),
        }
        for p in paths.values():
            os.makedirs(os.path.dirname(p), exist_ok=True)

        suite_dict = suite.to_json_dict()
        suite_dict.pop("id", None)
        for e in suite_dict.get("expectations", []):
            e.pop("id", None)
        with open(paths["suite"], "w", encoding="utf-8") as f:
            json.dump(suite_dict, f, indent=2, default=str)
        with open(paths["vd"], "w", encoding="utf-8") as f:
            json.dump({
                "name": f"{gate}_validation_definition",
                "data": {
                    "data_source": source_name,
                    "data_asset": asset_name,
                    "batch_definition": batch_def_name,
                    "batch_parameters": {"dataframe": "<staging parquet of the current DAG run>"},
                },
                "suite": suite.name,
            }, f, indent=2)
        with open(paths["checkpoint"], "w", encoding="utf-8") as f:
            json.dump({
                "name": checkpoint_name,
                "validation_definitions": [f"{gate}_validation_definition"],
                "result_format": "SUMMARY",
                "policy": "Applied in src/validation.py:run_gate (Critical -> CriticalDataQualityError, "
                          "Warning -> logged and recorded, Informational -> recorded)",
            }, f, indent=2)
    except OSError as exc:  # config export is documentation, never a reason to fail the gate
        logger.warning(f"Could not export GX configuration for {gate}: {exc}")


def run_gate(df: pd.DataFrame, gate: str, suite_name: str, expectations: list, report_path: str,
             batch_context: dict | None = None) -> dict:
    """Runs one validation gate through a GX Checkpoint and applies the severity policy."""
    context = gx.get_context(mode="ephemeral")
    source_name, asset_name, batch_def_name = f"{gate}_source", f"{gate}_asset", f"{gate}_batch"
    batch_def = (context.data_sources.add_pandas(source_name)
                 .add_dataframe_asset(asset_name)
                 .add_batch_definition_whole_dataframe(batch_def_name))

    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
    for exp in expectations:
        suite.add_expectation(exp)

    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(name=f"{gate}_validation_definition", data=batch_def, suite=suite))
    checkpoint_name = f"{gate}_checkpoint"
    checkpoint = context.checkpoints.add(gx.Checkpoint(
        name=checkpoint_name,
        validation_definitions=[validation_definition],
        result_format={"result_format": "SUMMARY"},
    ))

    _export_config(gate, suite, source_name, asset_name, batch_def_name, checkpoint_name)

    checkpoint_result = checkpoint.run(batch_parameters={"dataframe": df})
    validation_result = next(iter(checkpoint_result.run_results.values()))

    failures = {CRITICAL: [], WARNING: [], INFORMATIONAL: []}
    rules = []
    for res in validation_result.results:
        cfg = res.expectation_config
        meta = cfg.meta or {}
        severity = meta.get("severity", CRITICAL)
        rule_id = meta.get("rule_id", "UNMAPPED")
        result = res.result or {}
        target = cfg.kwargs.get("column") or cfg.kwargs.get("column_list") or "table"
        exception = res.exception_info or {}
        rules.append({
            "rule_id": rule_id,
            "severity": severity,
            "expectation_type": cfg.type,
            "target": target,
            "description": cfg.notes,
            "success": bool(res.success),
            "element_count": result.get("element_count"),
            "unexpected_count": result.get("unexpected_count"),
            "unexpected_percent": result.get("unexpected_percent"),
            "partial_unexpected_list": result.get("partial_unexpected_list"),
            "observed_value": result.get("observed_value"),
            "exception": exception.get("exception_message") if exception.get("raised_exception") else None,
        })
        if not res.success:
            failures[severity].append(f"{rule_id} ({target})")

    if failures[CRITICAL]:
        decision = "STOP"
    elif failures[WARNING]:
        decision = "CONTINUE_WITH_WARNING"
    else:
        decision = "CONTINUE"

    report = {
        "gate": gate,
        "suite": suite_name,
        "validation_definition": f"{gate}_validation_definition",
        "checkpoint": checkpoint_name,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "batch_context": batch_context or {},
        "total_records": int(len(df)),
        "gx_success": bool(checkpoint_result.success),
        "gate_decision": decision,
        "summary": {
            "expectations_evaluated": len(rules),
            "expectations_passed": sum(r["success"] for r in rules),
            "critical_failures": failures[CRITICAL],
            "warning_failures": failures[WARNING],
            "informational_failures": failures[INFORMATIONAL],
        },
        "rules_evaluated": rules,
    }
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"[{gate}] Validation evidence saved to: {report_path}")
    logger.info(f"[{gate}] {report['summary']['expectations_passed']}/{len(rules)} expectations passed "
                f"on {len(df):,} records -> gate decision {decision}")

    for item in failures[WARNING]:
        logger.warning(f"[{gate}] WARNING rule violated (batch continues by policy): {item}")
    for item in failures[INFORMATIONAL]:
        logger.info(f"[{gate}] Informational rule signal: {item}")

    if failures[CRITICAL]:
        msg = (f"Critical quality gate failure in {gate}: {', '.join(failures[CRITICAL])}. "
               f"Downstream processing is blocked. Evidence: {report_path}")
        logger.error(msg)
        raise CriticalDataQualityError(msg)

    return report


def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)


def validate_spotify_raw(raw_path: str, report_path: str, batch_context: dict | None = None) -> dict:
    """Raw gate: are the incoming Spotify data safe enough to enter transformation?"""
    logger.info(f"Executing Raw Validation Gate for Spotify: {raw_path}")
    return run_gate(_read(raw_path), "spotify_raw", "spotify_raw_suite",
                    spotify_raw_expectations(), report_path, batch_context)


def validate_grammys_raw(raw_path: str, report_path: str, batch_context: dict | None = None) -> dict:
    """Raw gate: are the relational Grammy records safe enough to enter transformation?"""
    logger.info(f"Executing Raw Validation Gate for Grammys: {raw_path}")
    return run_gate(_read(raw_path), "grammys_raw", "grammys_raw_suite",
                    grammys_raw_expectations(), report_path, batch_context)


def validate_prepared(prepared_path: str, report_path: str, batch_context: dict | None = None) -> dict:
    """Prepared gate: did transformation produce acceptable, load-ready data?"""
    logger.info(f"Executing Prepared Validation Gate: {prepared_path}")
    return run_gate(_read(prepared_path), "prepared", "prepared_music_suite",
                    prepared_expectations(), report_path, batch_context)
