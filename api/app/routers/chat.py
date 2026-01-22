"""
Chat Router - AI Assistant for regulation questions
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from openai import OpenAI

from app.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    response: str
    example_questions: List[str]


# System prompt for the AI assistant
SYSTEM_PROMPT = """Eres un experto en regulaciones de construccion de Puerto Rico.

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

Contexto sobre distritos de zonificacion del Reglamento Conjunto 2020:
- R-B: Residencial Baja Densidad
- R-I: Residencial Intermedio
- R-U: Residencial Urbano
- R-C: Residencial Comercial
- C-L: Comercial Liviano
- C-I: Comercial Intermedio
- C-C: Comercial Central
- I-L: Industrial Liviano
- I-P: Industrial Pesado
- A-G: Agricola General
- D-G: Dotacional General

Municipios con POT propio (Plan de Ordenamiento Territorial):
Barceloneta, Caguas, Carolina, Corozal, Guaynabo, Juncos, Lajas, Ponce, Rincon, San Juan, Santa Isabel, Vieques
"""

EXAMPLE_QUESTIONS = [
    "Que es una exclusion categorica?",
    "Cual es la diferencia entre permiso ministerial y discrecional?",
    "Que usos estan permitidos en zona R-I?",
    "Cuando necesito un Profesional Autorizado?",
    "Que documentos necesito para un permiso de construccion?",
    "Que es el proceso de OGPe?",
    "Como funciona la zonificacion en Puerto Rico?",
    "Que es el Tomo 6 del Reglamento Conjunto?",
]


@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Ask a question to the AI assistant about PR construction regulations
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured",
        )

    try:
        client = OpenAI(api_key=openai_api_key)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history if provided
        if request.history:
            for msg in request.history[-6:]:  # Keep last 6 messages
                messages.append({"role": msg.role, "content": msg.content})

        # Add current question
        messages.append({"role": "user", "content": request.message})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,
            temperature=0.3,
        )

        ai_response = response.choices[0].message.content

        return ChatResponse(
            response=ai_response,
            example_questions=EXAMPLE_QUESTIONS,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando el asistente: {str(e)}",
        )


@router.get("/examples", response_model=List[str])
async def get_example_questions():
    """
    Get example questions for the chatbot
    """
    return EXAMPLE_QUESTIONS
