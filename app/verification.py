"""
Flujo de verificación automática de certificaciones de tutores/profesores.

⚠️ ESTADO: stub pendiente. El nodo `analyze_content` todavía no está conectado
a un modelo de IA real — usa una heurística simple como placeholder
(ver comentario abajo). Reemplazar por una llamada real a Gemini cuando
se implemente el panel de moderadores.
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END
from .document_processor import extract_text_from_url


class AgentState(TypedDict):
    user_id: str
    file_url: str
    extracted_text: str
    is_valid: bool
    confidence: float
    reason: str


class VerificationGraph:
    def __init__(self):
        builder = StateGraph(AgentState)
        builder.add_node("extract", self.extract_docs)
        builder.add_node("analyze", self.analyze_content)
        builder.set_entry_point("extract")
        builder.add_edge("extract", "analyze")
        builder.add_edge("analyze", END)
        self.graph = builder.compile()

    def extract_docs(self, state: AgentState):
        try:
            text = extract_text_from_url(state["file_url"])
            return {"extracted_text": text}
        except Exception as e:
            return {
                "extracted_text": "",
                "is_valid": False,
                "reason": f"Error al leer archivo: {str(e)}",
                "confidence": 0.0,
            }

    def analyze_content(self, state: AgentState):
        if not state.get("extracted_text"):
            return state

        texto = state["extracted_text"]

        # TODO: reemplazar por una llamada real a Gemini (ver app/routers/chat.py
        # para el patrón de conexión). Por ahora, heurística simple de placeholder:
        is_valid = len(texto) > 100 and "universidad" in texto.lower()

        return {
            "is_valid": is_valid,
            "confidence": 0.92 if is_valid else 0.15,
            "reason": "Documento cumple los requisitos académicos." if is_valid
                       else "Documento insuficiente o no académico.",
        }
