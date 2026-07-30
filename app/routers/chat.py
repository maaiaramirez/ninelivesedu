import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai

router = APIRouter(prefix="/api", tags=["chat"])

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
_model = None

SYSTEM_PROMPT = (
    "Sos Wawa AI, el asistente de estudio de la plataforma Nine Lives Edu. "
    "Ayudás a estudiantes a encontrar apuntes, tutores, y resolver dudas académicas. "
    "Respondé siempre en español, de forma breve, cálida y clara."
)


def _get_model():
    global _model
    if _model is None:
        if not GEMINI_API_KEY:
            raise HTTPException(500, "Falta configurar la variable de entorno GEMINI_API_KEY en Render.")
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-2.0-flash")
    return _model


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(body: ChatRequest):
    if not body.message or not body.message.strip():
        raise HTTPException(400, "El mensaje no puede estar vacío.")

    try:
        model = _get_model()
        response = model.generate_content([SYSTEM_PROMPT, body.message])
        reply = response.text.strip() if response.text else "No pude generar una respuesta, intentá de nuevo. 🐾"
        return {"success": True, "reply": reply}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Error al generar respuesta con Gemini: {str(e)}")
