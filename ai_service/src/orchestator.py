from typing import TypedDict
from langgraph.graph import StateGraph, END
from .processor import extract_text_from_url

class AgentState(TypedDict):
    """Memoria temporal durante la ejecución del grafo"""
    user_id: str
    file_url: str
    extracted_text: str
    is_valid: bool
    confidence: float
    reason: str

class VerificationGraph:
    def __init__(self):
        builder = StateGraph(AgentState)
        
        # Nodos
        builder.add_node("extract", self.extract_docs)
        builder.add_node("analyze", self.analyze_content)
        
        # Flujo
        builder.set_entry_point("extract")
        builder.add_edge("extract", "analyze")
        builder.add_edge("analyze", END)
        
        self.graph = builder.compile()

    def extract_docs(self, state: AgentState):
        """Nodo 1: Descarga y extrae texto."""
        print(f"--- [Nodo] Extrayendo doc para usuario {state['user_id']} ---")
        try:
            text = extract_text_from_url(state["file_url"])
            return {"extracted_text": text}
        except Exception as e:
            return {
                "extracted_text": "", 
                "is_valid": False, 
                "reason": f"Error al leer archivo: {str(e)}", 
                "confidence": 0.0
            }

    def analyze_content(self, state: AgentState):
        """Nodo 2: Análisis del contenido."""
        print("--- [Nodo] Analizando contenido ---")
        if not state.get("extracted_text"):
            return state # Si falló la extracción, termina.
        
        texto = state["extracted_text"]
        
        # AQUI SE CONECTA TU MODELO LLM (OpenAI, Llama, etc.)
        # Por ahora, ponemos una lógica de simulación robusta:
        is_valid = len(texto) > 100 and "universidad" in texto.lower()
        
        return {
            "is_valid": is_valid,
            "confidence": 0.92 if is_valid else 0.15,
            "reason": "Documento cumple los requisitos académicos." if is_valid else "Documento insuficiente o no académico."
        }