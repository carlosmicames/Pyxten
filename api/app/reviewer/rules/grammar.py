"""
What a rule is allowed to say.

`applies_when` and the three condition fields are jsonb, which is one careless
commit away from an unbounded interpreter nobody can audit. A municipality's
counsel will eventually ask what a rule is capable of doing, and the answer has
to fit on one page. So this is a CLOSED grammar:

  combinators   all · any · not
  predicates    doc_present · profile_is · field_present · field_equals
                field_matches · field_contains · date_on_or_after · issued_by
                external_agrees
  normalizers   catastro · address · entity_name · person_name
                municipality · exact

No arithmetic beyond date comparison. No loops. No arbitrary attribute paths.
Anything a rule references that does not exist resolves to UNKNOWN, never to
false.

Evidence is collected as a side effect of evaluation: every predicate that reads
a fact records the document and page it came from. That is what makes "no
finding without evidence" automatic rather than something a rule author has to
remember.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Dict, List, Optional

from app.reviewer.rules.normalize import NORMALIZERS, compare, norm_date
from app.reviewer.rules.tri import Tri, tri_all, tri_any, tri_not

# Formats a rule may assert a field conforms to.
FORMATS = {
    # 11 digits, however the document punctuated them.
    "catastro": lambda v: bool(re.fullmatch(r"\d{11}", re.sub(r"\D", "", v or ""))),
    "date": lambda v: norm_date(v) is not None,
    "non_empty": lambda v: bool((v or "").strip()),
}


@dataclass
class Fact:
    """One extracted fact, with the provenance that makes it citable."""
    field_key: str
    value_text: Optional[str] = None
    value_date: Optional[date] = None
    value_num: Optional[float] = None
    document_id: Optional[str] = None
    source_page: Optional[int] = None
    band: str = "media"
    status: str = "extraido"

    @property
    def usable(self) -> bool:
        """A fact that could not be located is not evidence of anything."""
        return self.status == "extraido"

    @property
    def value(self):
        if self.value_text is not None:
            return self.value_text
        if self.value_date is not None:
            return self.value_date
        return self.value_num


@dataclass
class ExternalResult:
    """One recorded external lookup, e.g. the CRIM parcel at a coordinate."""
    source: str
    value: Optional[str] = None
    matched: bool = False
    quality_flag: str = "ok"

    @property
    def usable(self) -> bool:
        # Anything but a clean result forces escalation on rules that need it.
        return self.quality_flag == "ok"


@dataclass
class Context:
    """Everything a rule may look at, and nothing else."""
    facts: Dict[str, Fact] = field(default_factory=dict)
    document_types: List[str] = field(default_factory=list)
    document_ids_by_type: Dict[str, str] = field(default_factory=dict)
    # Classification band per document type. For a presence rule this IS the
    # relevant confidence: "is there a fire certificate?" rests on having
    # correctly identified a document as one.
    document_bands: Dict[str, str] = field(default_factory=dict)
    profile: Dict[str, Any] = field(default_factory=dict)
    case: Dict[str, Any] = field(default_factory=dict)
    externals: Dict[str, ExternalResult] = field(default_factory=dict)

    # Filled during evaluation.
    evidence: List[str] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def reset_evidence(self) -> None:
        self.evidence = []
        self.citations = []
        self.notes = []

    def cite(self, fact: Fact) -> None:
        """Record where a value came from, so a finding can point at it."""
        if fact.document_id and fact.document_id not in self.evidence:
            self.evidence.append(fact.document_id)
        self.citations.append(
            {
                "field_key": fact.field_key,
                "document_id": fact.document_id,
                "page": fact.source_page,
                "value": str(fact.value) if fact.value is not None else None,
                "band": fact.band,
            }
        )

    def cite_document(self, doc_type: str) -> None:
        """
        Record a located document as evidence.

        This also produces a citation, so a presence check derives its band from
        how confidently the document was classified rather than defaulting to
        `baja` for having read no fields.
        """
        document_id = self.document_ids_by_type.get(doc_type)
        if not document_id:
            return
        if document_id not in self.evidence:
            self.evidence.append(document_id)
        self.citations.append(
            {
                "field_key": f"documento.{doc_type}",
                "document_id": document_id,
                "page": None,
                "value": doc_type,
                # Unknown classification band is not high confidence.
                "band": self.document_bands.get(doc_type, "media"),
            }
        )

    def cite_inventory(self) -> None:
        """
        Evidence that a required document is missing.

        "You did not file a fire certificate" is the commonest deficiency there
        is, and it has no document of its own to point at. What it does have is
        the inventory: these are the documents that WERE filed, and none of them
        is the one required. That is the evidence, and it is what a reviewer
        would attach to the notice.

        A case with nothing filed at all cites nothing, so the evidence net
        escalates it - an empty expediente is an intake problem, not eleven
        findings against an applicant.
        """
        for document_id in self.document_ids_by_type.values():
            if document_id and document_id not in self.evidence:
                self.evidence.append(document_id)
        if self.document_ids_by_type:
            self.citations.append(
                {
                    "field_key": "expediente.inventario",
                    "document_id": None,
                    "page": None,
                    "value": ", ".join(sorted(self.document_types)),
                    # The inventory is what the office received; that is certain.
                    "band": "alta",
                }
            )

    def resolve(self, path: str) -> Optional[Fact]:
        """
        Look up a field. `case.*` and `profile.*` read the application record;
        anything else is an extracted fact keyed by `doctype.field`.
        """
        if path.startswith("case."):
            value = self.case.get(path[5:])
            if value is None:
                return None
            return Fact(field_key=path, value_text=str(value), band="alta")

        if path.startswith("profile."):
            value = self.profile.get(path[8:])
            if value is None:
                return None
            return Fact(field_key=path, value_text=str(value), band="alta")

        return self.facts.get(path)


# =============================================================================
# Predicates
# =============================================================================

def _p_doc_present(args: Dict, ctx: Context) -> Tri:
    doc_type = args.get("type")
    if not doc_type:
        return Tri.UNKNOWN
    present = doc_type in ctx.document_types
    if present:
        ctx.cite_document(doc_type)
    else:
        ctx.cite_inventory()
    return Tri.of(present)


def _p_profile_is(args: Dict, ctx: Context) -> Tri:
    key, expected = args.get("key"), args.get("value")
    if key is None:
        return Tri.UNKNOWN
    actual = ctx.profile.get(key)
    # An unanswered profile question is unknown, not "no".
    if actual is None:
        ctx.notes.append(f"perfil_incompleto:{key}")
        return Tri.UNKNOWN
    return Tri.of(actual == expected)


def _p_field_present(args: Dict, ctx: Context) -> Tri:
    fact = ctx.resolve(args.get("field", ""))
    if fact is None:
        return Tri.FALSE
    if not fact.usable:
        ctx.cite(fact)
        return Tri.UNKNOWN
    ctx.cite(fact)
    return Tri.of(fact.value is not None)


def _p_field_equals(args: Dict, ctx: Context) -> Tri:
    left = ctx.resolve(args.get("left", ""))
    right = ctx.resolve(args.get("right", ""))

    if left is None or right is None:
        missing = args.get("left") if left is None else args.get("right")
        ctx.notes.append(f"campo_ausente:{missing}")
        for fact in (left, right):
            if fact is not None:
                ctx.cite(fact)
        return Tri.UNKNOWN

    ctx.cite(left)
    ctx.cite(right)

    if not left.usable or not right.usable:
        return Tri.UNKNOWN

    # A comparison resting on a low-band reading is not a conclusion.
    if "baja" in (left.band, right.band):
        ctx.notes.append("banda_baja_en_comparacion")
        return Tri.UNKNOWN

    return compare(left.value, right.value, args.get("normalize", "exact"))


def _p_field_matches(args: Dict, ctx: Context) -> Tri:
    fact = ctx.resolve(args.get("field", ""))
    checker = FORMATS.get(args.get("format", ""))

    if fact is None or checker is None:
        return Tri.UNKNOWN

    ctx.cite(fact)
    if not fact.usable or fact.value is None:
        return Tri.UNKNOWN

    return Tri.of(checker(str(fact.value)))


def _as_date(value) -> Optional[date]:
    """Accept a date, an ISO string, or anything norm_date can read."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return norm_date(value)


def _p_date_on_or_after(args: Dict, ctx: Context) -> Tri:
    """Validity: is the document's date at or after the reference date?"""
    fact = ctx.resolve(args.get("field", ""))
    if fact is None:
        ctx.notes.append(f"campo_ausente:{args.get('field')}")
        return Tri.UNKNOWN

    ctx.cite(fact)
    if not fact.usable:
        return Tri.UNKNOWN

    # value_date is a date object in memory but an ISO string when it comes back
    # from PostgREST, so everything is coerced rather than compared as-is.
    subject = _as_date(fact.value_date) or norm_date(fact.value_text)
    reference_path = args.get("reference", "case.filing_date")
    reference_fact = ctx.resolve(reference_path)
    reference = None
    if reference_fact is not None:
        reference = _as_date(reference_fact.value_date) or norm_date(reference_fact.value_text)

    if subject is None or reference is None:
        ctx.notes.append("fecha_ilegible")
        return Tri.UNKNOWN

    return Tri.of(subject >= reference)


def _p_field_contains(args: Dict, ctx: Context) -> Tri:
    """
    Does a field mention any of these keywords?

    Keyword rather than exact match, because agencies and forms write the same
    thing many ways - "Activo", "ESTATUS: ACTIVO", "Comerciante activo".
    """
    fact = ctx.resolve(args.get("field", ""))
    expected = args.get("expected")
    keywords = args.get("keywords") or ([expected] if expected else [])

    if fact is None or not keywords:
        return Tri.UNKNOWN

    ctx.cite(fact)
    if not fact.usable or fact.value is None:
        return Tri.UNKNOWN

    from app.reviewer.rules.normalize import basic

    haystack = basic(str(fact.value))
    return Tri.of(any(basic(word) in haystack for word in keywords if word))


def _p_issued_by(args: Dict, ctx: Context) -> Tri:
    """
    Did the expected agency issue this document?

    Same mechanics as field_contains, kept as its own name because a rule that
    reads `issued_by` states its intent to anyone auditing the ruleset.
    """
    return _p_field_contains(args, ctx)


def _p_external_agrees(args: Dict, ctx: Context) -> Tri:
    """
    Compare a filed value against an external source.

    GIS is evidence, not truth. Disagreement is UNKNOWN - it escalates with both
    values shown - and an unreachable or ambiguous lookup is also UNKNOWN. This
    predicate can never on its own produce a finding against the applicant.
    """
    result = ctx.externals.get(args.get("source", ""))
    fact = ctx.resolve(args.get("field", ""))

    if result is None:
        ctx.notes.append(f"consulta_externa_ausente:{args.get('source')}")
        return Tri.UNKNOWN
    if not result.usable:
        ctx.notes.append(f"consulta_externa_{result.quality_flag}:{result.source}")
        return Tri.UNKNOWN
    if fact is None or not fact.usable:
        ctx.notes.append(f"campo_ausente:{args.get('field')}")
        return Tri.UNKNOWN

    ctx.cite(fact)
    outcome = compare(fact.value, result.value, args.get("normalize", "exact"))

    if outcome is Tri.FALSE:
        ctx.notes.append(
            f"discrepancia_externa:{result.source}:"
            f"documento={fact.value}:fuente={result.value}"
        )
        return Tri.UNKNOWN

    return outcome


PREDICATES: Dict[str, Callable[[Dict, Context], Tri]] = {
    "doc_present": _p_doc_present,
    "profile_is": _p_profile_is,
    "field_present": _p_field_present,
    "field_equals": _p_field_equals,
    "field_matches": _p_field_matches,
    "date_on_or_after": _p_date_on_or_after,
    "field_contains": _p_field_contains,
    "issued_by": _p_issued_by,
    "external_agrees": _p_external_agrees,
}


# =============================================================================
# Evaluation
# =============================================================================

def evaluate(condition: Optional[Dict], ctx: Context) -> Tri:
    """
    Evaluate one condition node.

    An empty condition is UNKNOWN, not vacuously true - a rule with no stated
    pass condition has not been authored, and should reach a person.
    """
    if not condition or not isinstance(condition, dict):
        return Tri.UNKNOWN

    if "all" in condition:
        return tri_all(evaluate(child, ctx) for child in condition["all"] or [])
    if "any" in condition:
        return tri_any(evaluate(child, ctx) for child in condition["any"] or [])
    if "not" in condition:
        return tri_not(evaluate(condition["not"], ctx))

    # Exactly one predicate key expected.
    for name, args in condition.items():
        predicate = PREDICATES.get(name)
        if predicate is None:
            ctx.notes.append(f"predicado_desconocido:{name}")
            return Tri.UNKNOWN
        if not isinstance(args, dict):
            return Tri.UNKNOWN
        return predicate(args, ctx)

    return Tri.UNKNOWN


def validate_condition(condition: Optional[Dict]) -> List[str]:
    """
    Static check of a rule definition. Used when seeding a ruleset so a typo in
    a predicate name is caught at publish time rather than discovered when a
    real case silently escalates.
    """
    problems: List[str] = []

    def walk(node, path="$"):
        if node is None:
            return
        if not isinstance(node, dict):
            problems.append(f"{path}: se esperaba un objeto")
            return

        for combinator in ("all", "any"):
            if combinator in node:
                children = node[combinator]
                if not isinstance(children, list) or not children:
                    problems.append(f"{path}.{combinator}: se esperaba una lista no vacia")
                    return
                for index, child in enumerate(children):
                    walk(child, f"{path}.{combinator}[{index}]")
                return

        if "not" in node:
            walk(node["not"], f"{path}.not")
            return

        if len(node) != 1:
            problems.append(f"{path}: se esperaba exactamente un predicado, hay {len(node)}")
            return

        name, args = next(iter(node.items()))
        if name not in PREDICATES:
            problems.append(f"{path}: predicado desconocido '{name}'")
            return
        if not isinstance(args, dict):
            problems.append(f"{path}.{name}: se esperaba un objeto de argumentos")
            return

        normalizer = args.get("normalize")
        if normalizer is not None and normalizer not in NORMALIZERS:
            problems.append(f"{path}.{name}: normalizador desconocido '{normalizer}'")

        fmt = args.get("format")
        if fmt is not None and fmt not in FORMATS:
            problems.append(f"{path}.{name}: formato desconocido '{fmt}'")

    walk(condition)
    return problems
