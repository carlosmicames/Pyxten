"""
Three-valued logic.

This is the smallest and most important idea in the rule engine.

A compliance check has three outcomes, not two, so the logic underneath it needs
three values too. If a predicate whose evidence is missing returned False, the
engine would manufacture a confident finding out of an absence - "the fire
certificate is expired" when the truth is "no fire certificate was found". That
is the error that ends up in an appeal.

So UNKNOWN is a first-class value and it is contagious: any condition that
depends on something unknowable is itself unknown, and an unknown condition
resolves the check to `requiere_criterio`.
"""
from __future__ import annotations

from enum import Enum


class Tri(Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"

    @classmethod
    def of(cls, value: bool) -> "Tri":
        return cls.TRUE if value else cls.FALSE

    @property
    def is_known(self) -> bool:
        return self is not Tri.UNKNOWN


def tri_all(values) -> Tri:
    """
    Conjunction. FALSE wins over UNKNOWN: if one requirement is definitely
    unmet, the whole condition is unmet regardless of what else is unclear.
    """
    seen_unknown = False
    for value in values:
        if value is Tri.FALSE:
            return Tri.FALSE
        if value is Tri.UNKNOWN:
            seen_unknown = True
    return Tri.UNKNOWN if seen_unknown else Tri.TRUE


def tri_any(values) -> Tri:
    """
    Disjunction. TRUE wins over UNKNOWN: one satisfied alternative is enough,
    whatever is unclear about the others.
    """
    seen_unknown = False
    for value in values:
        if value is Tri.TRUE:
            return Tri.TRUE
        if value is Tri.UNKNOWN:
            seen_unknown = True
    return Tri.UNKNOWN if seen_unknown else Tri.FALSE


def tri_not(value: Tri) -> Tri:
    """Negation. The negation of "I cannot tell" is still "I cannot tell"."""
    if value is Tri.TRUE:
        return Tri.FALSE
    if value is Tri.FALSE:
        return Tri.TRUE
    return Tri.UNKNOWN
