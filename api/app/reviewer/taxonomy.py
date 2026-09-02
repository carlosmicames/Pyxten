"""
The Permiso Unico document taxonomy the reviewer console classifies into.

Source of truth for the ten required/optional documents is the existing
`DocumentService.PERMISO_UNICO_DOCUMENTS`, so the reviewer side and the applicant
side agree on what a complete package contains. Two document types that recur in
real Permiso Unico packages but are only listed under PCOC are added here.

`desconocido` is a first-class outcome. A reviewer would rather see "I could not
tell" than a confident wrong label, so nothing in this system forces a guess.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.services.document_service import DocumentService

# Always available, never inferred from the source list.
UNKNOWN = "desconocido"

# Present in real packages; carried over from the PCOC list.
_EXTRA_TYPES = [
    {
        "code": "memorial_explicativo",
        "name": "Memorial Explicativo",
        "description": "Documento narrativo que describe el proyecto propuesto",
    },
    {
        "code": "fotos_predio",
        "name": "Fotos del Predio",
        "description": "Fotografias actuales del predio mostrando condiciones existentes",
    },
]


def permiso_unico_types() -> List[Dict[str, str]]:
    """Every classifiable type, plus `desconocido`."""
    types: List[Dict[str, str]] = [
        {
            "code": doc["code"],
            "name": doc["name"],
            "description": doc["description"],
        }
        for doc in DocumentService.get_permiso_unico_requirements()
    ]
    types.extend(_EXTRA_TYPES)
    types.append(
        {
            "code": UNKNOWN,
            "name": "Desconocido",
            "description": (
                "El documento no corresponde claramente a ninguna categoria, "
                "o no hay evidencia suficiente para clasificarlo."
            ),
        }
    )
    return types


def valid_codes() -> set:
    return {t["code"] for t in permiso_unico_types()}


def label_for(code: Optional[str]) -> str:
    if not code:
        return "Desconocido"
    for entry in permiso_unico_types():
        if entry["code"] == code:
            return entry["name"]
    return code


def catalog_for_prompt() -> str:
    """The taxonomy rendered for the classifier prompt."""
    lines = []
    for entry in permiso_unico_types():
        if entry["code"] == UNKNOWN:
            continue
        lines.append(f"- {entry['code']}: {entry['name']} - {entry['description']}")
    return "\n".join(lines)
