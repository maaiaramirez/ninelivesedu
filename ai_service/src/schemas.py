from pydantic import BaseModel, Field
from typing import Optional

class VerificationRequest(BaseModel):
    """Lo que Node.js le envía a la IA"""
    user_id: str = Field(..., description="ID anónimo del usuario")
    file_url: str = Field(..., description="URL temporal/firmada del archivo en S3/R2")

class VerificationResponse(BaseModel):
    """Lo que la IA le responde a Node.js"""
    status: str
    confidence: float
    reason: Optional[str] = None


# ─── AGREGAR ESTO AL FINAL PARA EL CHATBOT ───

class ChatRequest(BaseModel):
    """Lo que Node.js le envía a la IA desde el Chatbot"""
    message: str = Field(..., description="Mensaje enviado por el alumno en el chat")

class ChatResponse(BaseModel):
    """Lo que la IA le responde a Node.js para el Chatbot"""
    reply: str = Field(..., description="Respuesta generada por el asistente de IA")
