import os

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["chat"])

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# "openrouter/free" es el auto-router de OpenRouter: elige solo entre los
# modelos gratuitos disponibles, así seguimos funcionando aunque un modelo
# puntual deje de estar gratis (la lista rota seguido).
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")

SYSTEM_PROMPT = (
    "Sos Wawa AI, el asistente de estudio de la plataforma Nine Lives Edu. "
    "Ayudás a estudiantes a encontrar apuntes, tutores, y resolver dudas académicas. "
    "Respondé siempre en español, de forma breve, cálida y clara."
)


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(body: ChatRequest):
    if not body.message or not body.message.strip():
        raise HTTPException(400, "El mensaje no puede estar vacío.")

    if not OPENROUTER_API_KEY:
        raise HTTPException(500, "Falta configurar la variable de entorno OPENROUTER_API_KEY en Render.")

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": body.message},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"].strip()
        return {"success": True, "reply": reply or "No pude generar una respuesta, intentá de nuevo. 🐾"}
    except requests.exceptions.HTTPError as e:
        raise HTTPException(502, f"Error al generar respuesta con OpenRouter: {e.response.text}")
    except Exception as e:
        raise HTTPException(502, f"Error al generar respuesta con OpenRouter: {str(e)}")
