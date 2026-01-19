import os
from typing import List, Dict, Optional


class RegulationChatbot:
    """AI chatbot for Puerto Rico construction regulations"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Load regulation context
        self.regulation_context = self._load_regulation_context()

    def _load_regulation_context(self) -> str:
        """Load regulation text from local files if available"""

        context_parts = []

        # Try to load local regulation summaries
        try:
            from pathlib import Path

            data_dir = Path(__file__).parent.parent.parent / "data" / "regulations"

            # Load tomo6 rules
            tomo6_path = data_dir / "tomo6_rules.json"
            if tomo6_path.exists():
                import json
                with open(tomo6_path, 'r', encoding='utf-8') as f:
                    tomo6 = json.load(f)
                    context_parts.append("TOMO 6 - REGLAMENTO DE ZONIFICACION:")
                    context_parts.append(str(tomo6.get('tomo6_rules', {}))[:2000])

            # Load zoning districts
            zoning_path = data_dir / "zoning_districts.json"
            if zoning_path.exists():
                import json
                with open(zoning_path, 'r', encoding='utf-8') as f:
                    zoning = json.load(f)
                    context_parts.append("\nDISTRITOS DE ZONIFICACION:")
                    districts_text = []
                    for d in zoning.get('zoning_districts', [])[:15]:
                        districts_text.append(f"- {d.get('code')}: {d.get('name_es', d.get('name', ''))}")
                    context_parts.append("\n".join(districts_text))

            # Load use classifications
            use_path = data_dir / "use_classifications.json"
            if use_path.exists():
                import json
                with open(use_path, 'r', encoding='utf-8') as f:
                    uses = json.load(f)
                    context_parts.append("\nCLASIFICACIONES DE USO:")
                    uses_text = []
                    for u in uses.get('use_types', [])[:15]:
                        uses_text.append(f"- {u.get('code')}: {u.get('name_es', u.get('name_en', ''))}")
                    context_parts.append("\n".join(uses_text))

        except Exception as e:
            context_parts.append(f"[Error loading local context: {e}]")

        return "\n\n".join(context_parts)

    def ask(self, question: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Ask a question about PR construction regulations

        Args:
            question: User's question
            conversation_history: Previous messages [{"role": "user", "content": "..."}, ...]

        Returns:
            AI response
        """

        system_prompt = f"""Eres un experto en regulaciones de construccion de Puerto Rico.

Tienes conocimiento sobre:
1. Reglamento Conjunto 2023 (especialmente Tomo 6 - zonificacion)
2. Reglamento 2025-10 (Exclusiones Categoricas)
3. Proceso de permisos de construccion en Puerto Rico
4. OGPe (Oficina de Gerencia de Permisos)
5. Junta de Planificacion

Instrucciones:
- Responde en espanol
- Cita articulos especificos cuando sea posible
- Si no estas seguro, di "No tengo informacion suficiente sobre esto"
- Se conciso pero preciso
- Usa ejemplos practicos cuando ayuden
- Siempre menciona si una respuesta requiere verificacion con un profesional autorizado

Contexto disponible de regulaciones:
{self.regulation_context[:4000]}
"""

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-6:])  # Keep last 6 messages for context

        # Add current question
        messages.append({"role": "user", "content": question})

        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=600,
                temperature=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error consultando el asistente: {str(e)}"

    def get_example_questions(self) -> List[str]:
        """Get example questions for the chatbot"""

        return [
            "Que es una exclusion categorica?",
            "Cual es la diferencia entre permiso ministerial y discrecional?",
            "Que usos estan permitidos en zona R-2?",
            "Cuando necesito un Profesional Autorizado?",
            "Que documentos necesito para un permiso de construccion?",
            "Que es el proceso de OGPe?",
            "Como funciona la zonificacion en Puerto Rico?",
            "Que es el Tomo 6 del Reglamento Conjunto?"
        ]
