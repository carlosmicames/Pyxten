"""
Natural Language Use Classifier
Parses Spanish user descriptions into structured use codes from Reglamento Conjunto
"""

import json
import re
from typing import List, Dict
from anthropic import Anthropic
import os


class UseClassifier:
    """
    Classifies natural language use descriptions into RC use codes
    
    Examples:
    - "quiero construir una residencia con un edificio para una panaderia"
      → [{"code": "RES-SF", ...}, {"code": "COM-RETAIL", ...}]
    
    - "voy a operar una lavanderia y una oficina"
      → [{"code": "COM-RETAIL", ...}, {"code": "COM-OFFICE", ...}]
    """
    
    def __init__(self, use_types_data: List[Dict]):
        """
        Args:
            use_types_data: List of use types from use_classifications.json
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")
        
        self.client = Anthropic(api_key=api_key)
        self.use_types = use_types_data
        
        # Build searchable index
        self._build_use_index()
    
    def _build_use_index(self):
        """Build keyword index for faster matching"""
        
        self.use_index = {}
        
        for use in self.use_types:
            code = use['code']
            keywords = [
                use['name_es'].lower(),
                use['name_en'].lower(),
                use.get('description_es', '').lower()
            ]
            
            for keyword in keywords:
                if keyword:
                    self.use_index[code] = {
                        'code': code,
                        'name_es': use['name_es'],
                        'name_en': use['name_en'],
                        'category': use['category'],
                        'keywords': keywords
                    }
    
    def parse_natural_language(
        self,
        user_input: str,
        context: Dict = None
    ) -> Dict:
        """
        Parse natural language use description into structured use codes
        
        Args:
            user_input: User's description in Spanish
            context: Optional context (municipality, zoning, etc.)
        
        Returns:
            {
                "uses": [
                    {
                        "code": "RES-SF",
                        "name": "Residencial Unifamiliar",
                        "interpretation": "Vivienda unifamiliar principal",
                        "confidence": 0.95
                    },
                    ...
                ],
                "is_mixed_use": True/False,
                "clarifications_needed": ["¿Cuántos empleados?", ...],
                "context_detected": {
                    "has_commercial": True,
                    "has_residential": True,
                    "estimated_scale": "small" | "medium" | "large"
                }
            }
        """
        
        # Build prompt with use types catalog
        use_catalog = self._format_use_catalog()
        
        context_info = ""
        if context:
            context_info = f"\n\nContexto adicional:\n"
            if context.get('municipality'):
                context_info += f"- Municipio: {context['municipality']}\n"
            if context.get('zoning'):
                context_info += f"- Zonificación: {context['zoning']}\n"
        
        prompt = f"""Eres un experto en clasificación de usos según el Reglamento Conjunto de Puerto Rico 2023.

Analiza esta descripción de uso propuesto:

"{user_input}"

{context_info}

**CATÁLOGO DE USOS DEL REGLAMENTO CONJUNTO:**

{use_catalog}

**INSTRUCCIONES:**

1. Identifica TODOS los usos mencionados o implícitos en la descripción
2. Mapea cada uso al código exacto del catálogo anterior
3. Asigna nivel de confianza (0.0-1.0) basado en claridad de la descripción
4. Detecta si es uso mixto (múltiples usos en la misma propiedad)
5. Identifica información faltante que podría afectar la clasificación

**EJEMPLOS DE INTERPRETACIÓN:**

"Residencia con panadería"
→ RES-SF (residencia) + COM-RETAIL o COM-RESTAURANT (panadería, dependiendo si vende al detal o prepara comida)

"Lavandería y oficina"
→ COM-RETAIL (lavandería) + COM-OFFICE (oficina)

"Finca agrícola"
→ AGR-FARM

"Hotel pequeño con restaurante"
→ MIX-USE o COM-OFFICE (hotel) + COM-RESTAURANT

**CONSIDERACIONES IMPORTANTES:**

- Panaderías/Repostería:
  * Si < 15 empleados → Permitido en C-L (vía excepción)
  * Si > 15 empleados → Requiere C-I o industrial
  
- Lavanderías:
  * Autoservicio → COM-RETAIL
  * Industrial/comercial → Requiere C-I o I-L
  
- Oficinas:
  * Profesionales → COM-OFFICE
  * Administrativas → COM-OFFICE

- Restaurantes:
  * Siempre requieren permiso de salud
  * Ministerial: False en la mayoría de casos

Responde SOLO en formato JSON válido (sin markdown):

{{
  "uses": [
    {{
      "code": "RES-SF",
      "name": "Residencial Unifamiliar",
      "interpretation": "Vivienda unifamiliar principal mencionada",
      "confidence": 0.95,
      "notes": "Uso claramente identificado"
    }},
    {{
      "code": "COM-RETAIL",
      "name": "Comercio al Detal",
      "interpretation": "Panadería con venta al público",
      "confidence": 0.85,
      "notes": "Podría ser panadería artesanal (< 15 empleados) o industrial"
    }}
  ],
  "is_mixed_use": true,
  "clarifications_needed": [
    "¿Cuántos empleados tendrá la panadería?",
    "¿La panadería será uso principal o accesorio a la residencia?",
    "¿Habrá venta de comida preparada (restaurante) o solo productos horneados?"
  ],
  "context_detected": {{
    "has_commercial": true,
    "has_residential": true,
    "has_industrial": false,
    "estimated_scale": "small",
    "special_requirements": [
      "Permiso de salud para panadería",
      "Verificar límite de empleados para C-L"
    ]
  }}
}}

Sé preciso y conservador. Si no estás seguro, indica confianza más baja y solicita clarificación."""

        try:
            # Call Claude API
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.1,  # Low temperature for consistency
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract response
            response_text = message.content[0].text
            
            # Parse JSON
            result = self._parse_json_response(response_text)
            
            # Validate and enrich
            result = self._validate_and_enrich(result, user_input)
            
            return result
            
        except Exception as e:
            return {
                "uses": [],
                "is_mixed_use": False,
                "clarifications_needed": [f"Error clasificando uso: {str(e)}"],
                "error": str(e),
                "confidence": 0.0
            }
    
    def _format_use_catalog(self) -> str:
        """Format use types catalog for prompt"""
        
        catalog = []
        
        # Group by category
        by_category = {}
        for use in self.use_types:
            category = use['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(use)
        
        # Format each category
        category_names = {
            "residential": "RESIDENCIAL",
            "commercial": "COMERCIAL",
            "industrial": "INDUSTRIAL",
            "agricultural": "AGRÍCOLA",
            "mixed": "USO MIXTO"
        }
        
        for cat_key, cat_name in category_names.items():
            if cat_key in by_category:
                catalog.append(f"\n### {cat_name}:\n")
                
                for use in by_category[cat_key]:
                    catalog.append(
                        f"- **{use['code']}**: {use['name_es']} "
                        f"({use['name_en']})\n"
                        f"  Descripción: {use.get('description_es', 'N/A')}\n"
                    )
        
        return "".join(catalog)
    
    def _parse_json_response(self, response_text: str) -> Dict:
        """Parse JSON from Claude's response, handling markdown fences"""
        
        # Remove markdown code fences
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
        elif '```' in response_text:
            # Try to extract any JSON between backticks
            parts = response_text.split('```')
            if len(parts) > 1:
                response_text = parts[1]
        
        # Clean and parse
        response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # Fallback: try to find JSON object
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            raise ValueError(f"Could not parse JSON: {e}")
    
    def _validate_and_enrich(self, result: Dict, original_input: str) -> Dict:
        """Validate parsed result and add enriched info"""
        
        # Ensure required fields exist
        if 'uses' not in result:
            result['uses'] = []
        
        if 'is_mixed_use' not in result:
            result['is_mixed_use'] = len(result['uses']) > 1
        
        if 'clarifications_needed' not in result:
            result['clarifications_needed'] = []
        
        # Enrich each use with full data from catalog
        enriched_uses = []
        
        for use in result['uses']:
            code = use.get('code')
            
            # Find in catalog
            full_use_data = next(
                (u for u in self.use_types if u['code'] == code),
                None
            )
            
            if full_use_data:
                enriched_use = {
                    **use,
                    'category': full_use_data['category'],
                    'compatible_zones': full_use_data.get('compatible_zones', []),
                    'ministerial': full_use_data.get('ministerial', False),
                    'requires_health_permit': full_use_data.get('requires_health_permit', False),
                    'requires_environmental': full_use_data.get('requires_environmental', False),
                    'parking_required': full_use_data.get('parking_required', 'N/A')
                }
                
                enriched_uses.append(enriched_use)
            else:
                # Keep original but flag as unknown
                use['warning'] = f"Código {code} no encontrado en catálogo"
                enriched_uses.append(use)
        
        result['uses'] = enriched_uses
        result['original_input'] = original_input
        
        return result
    
    def quick_match(self, search_term: str) -> List[Dict]:
        """
        Quick keyword-based matching (no AI)
        
        Useful for autocomplete or suggestions
        """
        
        search_term = search_term.lower().strip()
        matches = []
        
        for use in self.use_types:
            score = 0
            
            # Check name
            if search_term in use['name_es'].lower():
                score += 10
            
            if search_term in use['name_en'].lower():
                score += 5
            
            # Check description
            if search_term in use.get('description_es', '').lower():
                score += 3
            
            if score > 0:
                matches.append({
                    'code': use['code'],
                    'name': use['name_es'],
                    'category': use['category'],
                    'score': score
                })
        
        # Sort by score
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:10]  # Top 10


# Example usage
if __name__ == "__main__":
    # Load use types
    import json
    from pathlib import Path
    
    data_dir = Path(__file__).parent.parent.parent / "data" / "regulations"
    with open(data_dir / "use_classifications.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        use_types = data['use_types']
    
    # Create classifier
    classifier = UseClassifier(use_types)
    
    # Test cases
    test_cases = [
        "quiero construir una residencia con un edificio para una panaderia",
        "voy a operar una lavanderia y una oficina",
        "hotel pequeño con restaurante en la playa",
        "finca agrícola con casa",
        "almacén industrial"
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Input: {test}")
        print('='*60)
        
        result = classifier.parse_natural_language(test)
        
        print(f"\nUsos identificados: {len(result['uses'])}")
        for use in result['uses']:
            print(f"  - {use['code']}: {use['name']} (confianza: {use['confidence']*100:.0f}%)")
            print(f"    Interpretación: {use['interpretation']}")
        
        print(f"\nUso mixto: {'Sí' if result['is_mixed_use'] else 'No'}")
        
        if result['clarifications_needed']:
            print(f"\nClarificaciones necesarias:")
            for clarif in result['clarifications_needed']:
                print(f"  - {clarif}")