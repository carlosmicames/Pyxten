"""
Comparing values that came out of different documents.

This is where cross-document consistency actually lives, and it is the part most
likely to produce a *wrong* finding if done naively. Two strings differing is
very weak evidence that something is wrong: a deed from 1998 carrying a married
name against a current registro carrying a maiden name is a person, not a
deficiency.

So every comparator here returns THREE outcomes, not two:

  TRUE     the values agree after normalization
  FALSE    they are substantively different - a different street, a different
           corporation, a different parcel
  UNKNOWN  they differ in a way that is a plausible naming or formatting
           variant, which escalates to a reviewer with both values shown

Everything is specific to how Puerto Rico writes names, addresses and catastro
numbers. Generic slugification is not sufficient here.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

from app.reviewer.rules.tri import Tri

# -----------------------------------------------------------------------------
# Vocabulary
# -----------------------------------------------------------------------------

# Street-type and locality abbreviations, expanded to a single canonical token.
_ADDRESS_ABBR = {
    "c": "calle", "c/": "calle", "cll": "calle",
    "ave": "avenida", "av": "avenida", "avda": "avenida",
    "urb": "urbanizacion", "urbanizacion": "urbanizacion",
    "bo": "barrio", "bda": "barriada",
    "carr": "carretera", "km": "kilometro", "kmt": "kilometro",
    "res": "residencial", "cond": "condominio", "edif": "edificio",
    "apto": "apartamento", "apt": "apartamento",
    "ste": "suite", "sect": "sector", "parc": "parcela",
    "num": "numero", "no": "numero", "nro": "numero",
    "pr": "puerto rico",
}

# Corporate suffixes carry no identity - "Panaderia Lopez Inc." and
# "Panaderia Lopez Corp." are the same trade name filed differently.
_ENTITY_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "corporacion",
    "llc", "lc", "ltd", "limited", "co", "company", "compania",
    "se", "sen", "csp", "psc", "lp", "llp", "sa", "srl",
    "dba", "hnc",  # "haciendo negocios como"
}

# Spanish name particles: not identifying on their own.
_NAME_PARTICLES = {"de", "del", "la", "las", "los", "y", "e", "san", "santa"}

_MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


# -----------------------------------------------------------------------------
# Primitives
# -----------------------------------------------------------------------------

def strip_accents(value: str) -> str:
    """
    Fold accents and enye. `Bayamón` and `Bayamon` are the same municipality,
    and government systems disagree about which one to store.
    """
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def basic(value: Optional[str]) -> str:
    """Casefold, strip accents, collapse punctuation and whitespace."""
    if not value:
        return ""
    text = strip_accents(str(value)).lower()
    text = re.sub(r"[^\w\s/]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: Optional[str]) -> list:
    return [t for t in basic(value).split(" ") if t]


# -----------------------------------------------------------------------------
# Field normalizers
# -----------------------------------------------------------------------------

def norm_catastro(value: Optional[str]) -> str:
    """
    Catastro numbers appear as `123-456-789-01`, `12345678901`, with non-ASCII
    hyphens, and sometimes with a leading municipality code. Reduce to digits;
    the comparator decides what a differing length means.
    """
    return re.sub(r"\D", "", str(value or ""))


def norm_address(value: Optional[str]) -> str:
    """
    Expand abbreviations to canonical tokens. Note that many Puerto Rico
    addresses have no street number at all and are identified by urbanizacion
    plus block and lot, so nothing here assumes a house number exists.
    """
    expanded = [_ADDRESS_ABBR.get(token, token) for token in _tokens(value)]
    return " ".join(expanded)


def norm_entity_name(value: Optional[str]) -> str:
    """Drop corporate suffixes; `&` and `y` both become `y`."""
    tokens = [("y" if t == "and" else t) for t in _tokens(value)]
    kept = [t for t in tokens if t not in _ENTITY_SUFFIXES]
    return " ".join(kept or tokens)


def norm_person_name(value: Optional[str]) -> str:
    """Drop particles, keep order - order distinguishes given names from surnames."""
    tokens = [t for t in _tokens(value) if t not in _NAME_PARTICLES and len(t) > 1]
    return " ".join(tokens)


def norm_municipality(value: Optional[str]) -> str:
    text = norm_address(value)
    return re.sub(r"\b(municipio|de)\b", "", text).strip()


def norm_date(value) -> Optional[date]:
    """
    Parse the date formats that actually turn up on Puerto Rico certifications,
    including dates written out in Spanish.
    """
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()

    # NOT basic(): that strips punctuation, and a date is mostly punctuation.
    text = strip_accents(str(value)).lower().strip()
    if not text:
        return None

    # 15 de enero de 2024
    spelled = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", text)
    if spelled and spelled.group(2) in _MONTHS_ES:
        return date(int(spelled.group(3)), _MONTHS_ES[spelled.group(2)], int(spelled.group(1)))

    for pattern, order in (
        (r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", "ymd"),
        (r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", "dmy"),
    ):
        found = re.search(pattern, text)
        if not found:
            continue
        a, b, c = (int(g) for g in found.groups())
        try:
            if order == "ymd":
                return date(a, b, c)
            # Ambiguous between d/m and m/d. Prefer m/d/y, the prevailing
            # convention on Puerto Rico government forms, and fall back.
            try:
                return date(c, a, b)
            except ValueError:
                return date(c, b, a)
        except ValueError:
            return None

    return None


NORMALIZERS = {
    "catastro": norm_catastro,
    "address": norm_address,
    "entity_name": norm_entity_name,
    "person_name": norm_person_name,
    "municipality": norm_municipality,
    "exact": basic,
}


# -----------------------------------------------------------------------------
# Three-valued comparators
# -----------------------------------------------------------------------------

def _compare_catastro(left: str, right: str) -> Tri:
    a, b = norm_catastro(left), norm_catastro(right)
    if not a or not b:
        return Tri.UNKNOWN
    if a == b:
        return Tri.TRUE
    # A differing digit count usually means one document used a different
    # numbering convention, not a different parcel. Escalate, do not accuse.
    if len(a) != len(b) and (a.endswith(b) or b.endswith(a) or a.startswith(b) or b.startswith(a)):
        return Tri.UNKNOWN
    return Tri.FALSE


def _compare_person_name(left: str, right: str) -> Tri:
    a, b = set(norm_person_name(left).split()), set(norm_person_name(right).split())
    if not a or not b:
        return Tri.UNKNOWN
    if a == b:
        return Tri.TRUE
    # One name being a subset of the other is the married-name / second-surname
    # case, and a shared given name plus one shared surname is a likely match.
    if a <= b or b <= a or len(a & b) >= 2:
        return Tri.UNKNOWN
    return Tri.FALSE


def _compare_entity_name(left: str, right: str) -> Tri:
    a, b = norm_entity_name(left), norm_entity_name(right)
    if not a or not b:
        return Tri.UNKNOWN
    if a == b:
        return Tri.TRUE
    # A legal name against a registered trade name is a real and legitimate
    # difference, so containment escalates rather than fails.
    if a in b or b in a:
        return Tri.UNKNOWN
    return Tri.FALSE


def _compare_address(left: str, right: str) -> Tri:
    a, b = norm_address(left), norm_address(right)
    if not a or not b:
        return Tri.UNKNOWN
    if a == b:
        return Tri.TRUE

    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return Tri.UNKNOWN

    overlap = len(ta & tb) / max(len(ta), len(tb))
    # Substantial overlap means the same place written differently, or the same
    # building with a unit number on only one document.
    return Tri.UNKNOWN if overlap >= 0.6 else Tri.FALSE


def _compare_simple(normalizer) -> callable:
    def compare(left: str, right: str) -> Tri:
        a, b = normalizer(left), normalizer(right)
        if not a or not b:
            return Tri.UNKNOWN
        return Tri.TRUE if a == b else Tri.FALSE
    return compare


COMPARATORS = {
    "catastro": _compare_catastro,
    "person_name": _compare_person_name,
    "entity_name": _compare_entity_name,
    "address": _compare_address,
    "municipality": _compare_simple(norm_municipality),
    "exact": _compare_simple(basic),
}


def compare(left, right, normalizer: str = "exact") -> Tri:
    """
    Compare two values under a named normalizer.

    An unrecognised normalizer is a programming error in a rule definition, and
    it resolves to UNKNOWN rather than guessing - a rule nobody can evaluate
    escalates to a person instead of silently passing.
    """
    comparator = COMPARATORS.get(normalizer)
    if comparator is None:
        return Tri.UNKNOWN
    return comparator(left, right)
