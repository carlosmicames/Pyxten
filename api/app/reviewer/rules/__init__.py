"""
The rule engine: rules are data, evaluated by deterministic Python.

No module in this package imports an LLM client, and a test enforces that. A
model may extract facts; only this code decides what a check's outcome is.
"""
from app.reviewer.rules.engine import (
    HALLAZGO_IDENTIFICADO,
    REQUIERE_CRITERIO,
    SIN_HALLAZGOS,
    CheckResult,
    evaluate_case,
    evaluate_rule,
    summarize,
)
from app.reviewer.rules.grammar import Context, ExternalResult, Fact, validate_condition
from app.reviewer.rules.tri import Tri

__all__ = [
    "Context",
    "ExternalResult",
    "Fact",
    "Tri",
    "CheckResult",
    "evaluate_rule",
    "evaluate_case",
    "summarize",
    "validate_condition",
    "SIN_HALLAZGOS",
    "HALLAZGO_IDENTIFICADO",
    "REQUIERE_CRITERIO",
]
