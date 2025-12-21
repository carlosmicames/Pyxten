"""
ModelRouter - Sistema de 2 modelos
GPT-4o Mini para planos (vision) + Haiku para documentos texto
NO usa Sonnet - más simple y económico
"""

import openai
import anthropic
import os
import base64
import json
import re
from typing import Dict, List

class ModelRouter:
    """Enruta documentos al modelo óptimo: GPT-4o Mini o Haiku"""
    
    def __init__(self):
        # Inicializar clientes
        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not openai_key:
            raise ValueError("OPENAI_API_KEY no encontrada en .env")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY no encontrada en .env")
        
        self.openai_client = openai.OpenAI(api_key=openai_key)
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
        
        # Configuración de modelos (solo 2)
        self.models = {
            "gpt4o_mini": "gpt-4o-mini",
            "haiku": "claude-haiku-4-5-20251001"
        }
    
    def analyze_document(
        self, 
        doc_type: str,
        file_bytes: bytes,
        requirements: List[str]
    ) -> Dict:
        """
        Analiza documento con modelo óptimo
        
        Args:
            doc_type: Tipo de documento (planta_arquitectonica, certificacion_registral, etc.)
            file_bytes: Bytes del archivo
            requirements: Lista de requisitos a validar
        
        Returns:
            {
                "score": 0.0-1.0,
                "confidence": 0.0-1.0,
                "passed": bool,
                "validations": [...],
                "extracted_data": {...},
                "issues": [...],
                "critical_issues": [...],
                "model_used": str,
                "cost_estimate": float
            }
        """
        
        # Determinar modelo óptimo
        model = self._select_optimal_model(doc_type)
        
        # Construir prompt
        prompt = self._build_prompt(doc_type, requirements)
        
        try:
            # Analizar según modelo
            if model == "gpt4o_mini":
                result = self._analyze_with_gpt4o(file_bytes, prompt)
            else:  # haiku
                result = self._analyze_with_haiku(file_bytes, prompt)
            
            # Agregar metadata
            result['model_used'] = model
            result['cost_estimate'] = self._estimate_cost(model, file_bytes, result)
            
            # Asegurar que confidence existe
            if 'confidence' not in result:
                result['confidence'] = 0.85
            
            return result
            
        except Exception as e:
            return {
                "score": 0.0,
                "confidence": 0.0,
                "passed": False,
                "error": str(e),
                "validations": [],
                "model_used": model,
                "cost_estimate": 0.0
            }
    
    def _select_optimal_model(self, doc_type: str) -> str:
        """Selecciona modelo óptimo por tipo de documento"""
        
        # Mapeo documento → modelo
        # GPT-4o Mini: Todo lo que tenga imágenes/planos
        # Haiku: Documentos texto puro
        
        vision_docs = [
            "planta_arquitectonica",
            "elevaciones", 
            "planta_conjunto",
            "secciones",
            "detalles",
            "planos"  # genérico
        ]
        
        if doc_type in vision_docs:
            return "gpt4o_mini"
        else:
            return "haiku"  # Docs texto
    
    def _analyze_with_gpt4o(self, file_bytes: bytes, prompt: str) -> Dict:
        """Analiza con GPT-4o Mini"""
        
        # Convertir a base64
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        # Detectar media type
        if file_bytes[:4] == b'%PDF':
            media_type = "application/pdf"
        elif file_bytes[:2] == b'\xff\xd8':
            media_type = "image/jpeg"
        elif file_bytes[:4] == b'\x89PNG':
            media_type = "image/png"
        else:
            media_type = "image/jpeg"  # Default
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.models["gpt4o_mini"],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{base64_image}",
                                    "detail": "high"  # Para mejor análisis
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1  # Baja temperatura para consistencia
            )
            
            result_text = response.choices[0].message.content
            return self._parse_response(result_text)
            
        except Exception as e:
            return {
                "score": 0.0,
                "confidence": 0.0,
                "passed": False,
                "error": f"Error GPT-4o Mini: {str(e)}",
                "validations": []
            }
    
    def _analyze_with_haiku(self, file_bytes: bytes, prompt: str) -> Dict:
        """Analiza con Claude Haiku"""
        
        # Convertir a base64
        base64_doc = base64.b64encode(file_bytes).decode('utf-8')
        
        # Detectar media type
        if file_bytes[:4] == b'%PDF':
            media_type = "application/pdf"
        elif file_bytes[:2] == b'\xff\xd8':
            media_type = "image/jpeg"
        elif file_bytes[:4] == b'\x89PNG':
            media_type = "image/png"
        else:
            media_type = "image/jpeg"
        
        try:
            message = self.anthropic_client.messages.create(
                model=self.models["haiku"],
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_doc
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            
            result_text = message.content[0].text
            return self._parse_response(result_text)
            
        except Exception as e:
            return {
                "score": 0.0,
                "confidence": 0.0,
                "passed": False,
                "error": f"Error Haiku: {str(e)}",
                "validations": []
            }
    
    def _build_prompt(self, doc_type: str, requirements: List[str]) -> str:
        """Construye prompt optimizado por tipo de documento"""
        
        requirements_text = "\n".join(f"{i+1}. {req}" for i, req in enumerate(requirements))
        
        # Nombres amigables para tipos de documentos
        doc_names = {
            "planta_arquitectonica": "Planta Arquitectónica",
            "elevaciones": "Elevaciones",
            "planta_conjunto": "Planta de Conjunto",
            "certificacion_registral": "Certificación Registral",
            "formulario_ogpe": "Formulario OGPe",
            "certificacion_aaa": "Certificación AAA"
        }
        
        doc_name = doc_names.get(doc_type, doc_type)
        
        return f"""Eres un experto inspector de documentos de construcción en Puerto Rico.

Analiza este documento: {doc_name}

REQUISITOS A VALIDAR (Reglamento Conjunto Sección 2.1.9):
{requirements_text}

INSTRUCCIONES:
1. Verifica CADA requisito con precisión
2. Extrae datos específicos (nombres, fechas, dimensiones, etc.)
3. Identifica errores críticos que impedirían aprobación
4. Clasifica issues por severidad (crítico vs menor)
5. Asigna nivel de confianza (0.0-1.0) a tu análisis

CRITERIOS DE EVALUACIÓN:
- ✅ CUMPLE (score ≥0.90): Todos los requisitos pasados
- ⚠️ REQUIERE ATENCIÓN (score 0.70-0.89): Issues menores corregibles
- ❌ NO CUMPLE (score <0.70): Issues críticos presentes

Responde SOLO en formato JSON válido (sin markdown):

{{
  "score": 0.95,
  "confidence": 0.98,
  "passed": true,
  "validations": [
    {{
      "check": "Nombre exacto del requisito",
      "passed": true,
      "details": "Descripción específica de lo encontrado",
      "location": "Dónde en el documento"
    }}
  ],
  "extracted_data": {{
    "key": "value"
  }},
  "issues": ["Lista de problemas menores"],
  "critical_issues": ["Lista de problemas que bloquean aprobación"]
}}

Sé extremadamente preciso. Este análisis afecta proyectos reales."""
    
    def _parse_response(self, text: str) -> Dict:
        """Parsea respuesta JSON de cualquier modelo"""
        
        # Intentar limpiar markdown
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        elif '```' in text:
            # Intentar extraer cualquier JSON entre backticks
            text = text.split('```')[1] if len(text.split('```')) > 1 else text
        
        # Limpiar texto
        text = text.strip()
        
        try:
            result = json.loads(text)
            
            # Validar estructura mínima
            if 'score' not in result:
                result['score'] = 0.0
            if 'passed' not in result:
                result['passed'] = result['score'] >= 0.9
            if 'validations' not in result:
                result['validations'] = []
            if 'confidence' not in result:
                result['confidence'] = 0.85
            
            return result
            
        except json.JSONDecodeError as e:
            # Si falla el parsing, devolver estructura de error
            return {
                "score": 0.0,
                "confidence": 0.0,
                "passed": False,
                "error": f"Error parsing JSON: {str(e)}",
                "raw_response": text[:500],  # Primeros 500 chars para debug
                "validations": []
            }
    
    def _estimate_cost(self, model: str, file_bytes: bytes, result: Dict) -> float:
        """Estima costo de la llamada API"""
        
        # Tamaño del archivo
        file_size_kb = len(file_bytes) / 1024
        
        # Estimación de tokens
        input_tokens = 1500 if file_size_kb > 100 else 1000
        output_text = str(result)
        output_tokens = len(output_text) / 4
        
        # Costos por millón de tokens (SOLO 2 MODELOS)
        costs = {
            "gpt4o_mini": {"input": 0.15, "output": 0.60},
            "haiku": {"input": 0.80, "output": 4.00}
        }
        
        if model in costs:
            rates = costs[model]
            cost = (
                (input_tokens / 1_000_000) * rates["input"] +
                (output_tokens / 1_000_000) * rates["output"]
            )
            return round(cost, 4)
        
        return 0.0