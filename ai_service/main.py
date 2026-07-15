"""
Ninelives AI — Microservicio FastAPI
Expone el endpoint de chat (Gemini) que antes hacía de puente ai_service/node/server.js.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

# ─────────────────────────────────────────────
# Schemas (definidos acá directamente para evitar
# problemas de resolución de módulos en el deploy)
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str

# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "Falta la variable de entorno GEMINI_API_KEY. "
        "Configurala en tu .env local o en Render (Environment)."
    )

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Instrucción de sistema para que el bot se comporte como "Wawa AI"
SYSTEM_PROMPT = (
    "Sos Wawa AI, el asistente de estudio de la plataforma Nine Lives Edu. "
    "Ayudás a estudiantes a encontrar apuntes, tutores, y resolver dudas académicas. "
    "Respondé siempre en español, de forma breve, cálida y clara."
)

app = FastAPI(title="Ninelives AI Service")

# CORS: permití el dominio de tu frontend en producción y en local
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ninelivesedu-1.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    try:
        response = model.generate_content(
            [SYSTEM_PROMPT, payload.message]
        )
        reply_text = response.text.strip() if response.text else (
            "No pude generar una respuesta, intentá de nuevo. 🐾"
        )
        return ChatResponse(reply=reply_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar respuesta con Gemini: {str(e)}"
        )
