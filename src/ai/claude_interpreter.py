# ClaudeAPI integration
import os
from anthropic import Anthropic
from typing import Dict

class ClaudeInterpreter:
    """Use Claude AI for complex regulatory interpretation"""
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        self.client = Anthropic(api_key=api_key)
    
    def interpret_edge_case(
        self,
        zoning_code: str,
        zoning_name: str,
        proposed_use: str,
        use_description: str
    ) -> Dict:
        """
        Use Claude to interpret ambiguous zoning/use compatibility cases
        """
        
        prompt = f"""Eres un experto en regulaciones de uso de suelo de Puerto Rico, 
específicamente en el Reglamento Conjunto Tomo 6.

Analiza si este uso propuesto es compatible con la zonificación:

ZONIFICACIÓN:
- Código: {zoning_code}
- Nombre: {zoning_name}

USO PROPUESTO:
- Tipo: {proposed_use}
- Descripción: {use_description}

Basándote en el Reglamento Conjunto Tomo 6, responde:

1. ¿Es este uso compatible con esta zonificación? (SÍ/NO)
2. ¿Por qué? (explica en 2-3 oraciones)
3. ¿Qué artículo del Reglamento Conjunto aplica?
4. ¿Es ministerial o discrecional?

Responde en formato JSON:
{{
  "compatible": true/false,
  "reasoning": "explicación",
  "article": "artículo aplicable",
  "permit_type": "ministerial" o "discrecional"
}}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            response_text = message.content[0].text
            
            # Parse response (Claude should return JSON)
            # In production, add better JSON extraction
            import json
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text.strip())
            result["ai_interpreted"] = True
            return result
            
        except Exception as e:
            return {
                "compatible": None,
                "reasoning": f"Error en interpretación AI: {str(e)}",
                "article": "No disponible",
                "permit_type": "desconocido",
                "ai_interpreted": False,
                "error": str(e)
            }
