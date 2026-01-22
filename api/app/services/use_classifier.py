"""
Natural Language Use Classifier
Parses Spanish user descriptions into structured use codes from Reglamento Conjunto
Uses OpenAI for classification (migrated from Anthropic)
"""
import json
import re
from typing import List, Dict
from openai import OpenAI
from app.config import get_settings


class UseClassifier:
    """Classifies natural language use descriptions into RC use codes"""

    def __init__(self, use_types_data: List[Dict]):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.use_types = use_types_data
        self._build_use_index()

    def _build_use_index(self):
        """Build keyword index for faster matching"""
        self.use_index = {}
        for use in self.use_types:
            code = use["code"]
            self.use_index[code] = {
                "code": code,
                "name_es": use["name_es"],
                "name_en": use["name_en"],
                "category": use["category"],
            }

    def parse_natural_language(self, user_input: str, context: Dict = None) -> Dict:
        """Parse natural language use description into structured use codes"""
        use_catalog = self._format_use_catalog()

        context_info = ""
        if context:
            context_info = "\n\nContexto adicional:\n"
            if context.get("municipality"):
                context_info += f"- Municipio: {context['municipality']}\n"
            if context.get("zoning"):
                context_info += f"- Zonificacion: {context['zoning']}\n"

        prompt = f"""Eres un experto en clasificacion de usos segun el Reglamento Conjunto de Puerto Rico 2023.

Analiza esta descripcion de uso propuesto:

"{user_input}"

{context_info}

**CATALOGO DE USOS DEL REGLAMENTO CONJUNTO:**

{use_catalog}

**INSTRUCCIONES:**

1. Identifica TODOS los usos mencionados o implicitos en la descripcion
2. Mapea cada uso al codigo exacto del catalogo anterior
3. Asigna nivel de confianza (0.0-1.0) basado en claridad de la descripcion
4. Detecta si es uso mixto (multiples usos en la misma propiedad)
5. Identifica informacion faltante que podria afectar la clasificacion

**EJEMPLOS DE INTERPRETACION:**

"Residencia con panaderia"
-> RES-SF (residencia) + COM-RETAIL o COM-RESTAURANT (panaderia)

"Lavanderia y oficina"
-> COM-RETAIL (lavanderia) + COM-OFFICE (oficina)

Responde SOLO en formato JSON valido (sin markdown):

{{
  "uses": [
    {{
      "code": "RES-SF",
      "name": "Residencial Unifamiliar",
      "interpretation": "Vivienda unifamiliar principal mencionada",
      "confidence": 0.95,
      "notes": "Uso claramente identificado"
    }}
  ],
  "is_mixed_use": false,
  "clarifications_needed": [],
  "context_detected": {{
    "has_commercial": false,
    "has_residential": true,
    "has_industrial": false,
    "estimated_scale": "small"
  }}
}}

Se preciso y conservador. Si no estas seguro, indica confianza mas baja."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=2000,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Responde SOLO en JSON valido."},
                    {"role": "user", "content": prompt}
                ],
            )

            response_text = response.choices[0].message.content
            result = self._parse_json_response(response_text)
            result = self._validate_and_enrich(result, user_input)

            return result

        except Exception as e:
            return {
                "uses": [],
                "is_mixed_use": False,
                "clarifications_needed": [f"Error clasificando uso: {str(e)}"],
                "error": str(e),
                "confidence": 0.0,
            }

    def _format_use_catalog(self) -> str:
        """Format use types catalog for prompt"""
        catalog = []

        by_category = {}
        for use in self.use_types:
            category = use["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(use)

        category_names = {
            "residential": "RESIDENCIAL",
            "commercial": "COMERCIAL",
            "industrial": "INDUSTRIAL",
            "agricultural": "AGRICOLA",
            "mixed": "USO MIXTO",
        }

        for cat_key, cat_name in category_names.items():
            if cat_key in by_category:
                catalog.append(f"\n### {cat_name}:\n")
                for use in by_category[cat_key]:
                    catalog.append(
                        f"- **{use['code']}**: {use['name_es']} "
                        f"({use['name_en']})\n"
                        f"  Descripcion: {use.get('description_es', 'N/A')}\n"
                    )

        return "".join(catalog)

    def _parse_json_response(self, response_text: str) -> Dict:
        """Parse JSON from Claude's response, handling markdown fences"""
        json_match = re.search(
            r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL
        )
        if json_match:
            response_text = json_match.group(1)
        elif "```" in response_text:
            parts = response_text.split("```")
            if len(parts) > 1:
                response_text = parts[1]

        response_text = response_text.strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            raise ValueError("Could not parse JSON response")

    def _validate_and_enrich(self, result: Dict, original_input: str) -> Dict:
        """Validate parsed result and add enriched info"""
        if "uses" not in result:
            result["uses"] = []

        if "is_mixed_use" not in result:
            result["is_mixed_use"] = len(result["uses"]) > 1

        if "clarifications_needed" not in result:
            result["clarifications_needed"] = []

        enriched_uses = []

        for use in result["uses"]:
            code = use.get("code")
            full_use_data = next(
                (u for u in self.use_types if u["code"] == code), None
            )

            if full_use_data:
                enriched_use = {
                    **use,
                    "category": full_use_data["category"],
                    "compatible_zones": full_use_data.get("compatible_zones", []),
                    "ministerial": full_use_data.get("ministerial", False),
                }
                enriched_uses.append(enriched_use)
            else:
                use["warning"] = f"Codigo {code} no encontrado en catalogo"
                enriched_uses.append(use)

        result["uses"] = enriched_uses
        result["original_input"] = original_input

        return result
