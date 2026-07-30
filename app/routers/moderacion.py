"""
Panel de moderadores — verificación de certificaciones de tutores/profesores.

⚠️ Funcional pero con el análisis en modo stub (ver app/verification.py).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..verification import VerificationGraph

router = APIRouter(prefix="/api/moderacion", tags=["moderacion"])

_graph = VerificationGraph()


class VerificarIn(BaseModel):
    user_id: str
    file_url: str


@router.post("/verificar-certificacion")
def verificar_certificacion(body: VerificarIn):
    try:
        result = _graph.graph.invoke({
            "user_id": body.user_id,
            "file_url": body.file_url,
            "extracted_text": "",
            "is_valid": False,
            "confidence": 0.0,
            "reason": "",
        })
    except Exception as e:
        raise HTTPException(500, f"Error al procesar la verificación: {str(e)}")

    return {
        "user_id": body.user_id,
        "is_valid": result.get("is_valid", False),
        "confidence": result.get("confidence", 0.0),
        "reason": result.get("reason", ""),
    }
