"""
Verificación de certificaciones de tutores, asistida por IA.

Reemplaza al viejo stub de app/verification.py (langgraph + unstructured):
en vez de extraer texto y aplicar una heurística, le mandamos el documento
directamente a un modelo con visión a través de OpenRouter — la MISMA
integración que ya usa app/routers/chat.py, sin dependencias nuevas.

Esto NO reemplaza al moderador humano: solo le da una opinión (¿parece
válido?, ¿cuánta confianza?, ¿por qué?) para ayudarlo a decidir más rápido.
La aprobación/rechazo final sigue siendo un clic del moderador, igual que
antes.
"""
import base64
import json
import os
import re
from pathlib import Path

import requests
from fastapi import HTTPException

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# Mismo router automático que chat.py: entre sus modelos gratuitos filtra
# solo los que soportan imágenes cuando el pedido las necesita.
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")

# Qué tipos de archivo puede "mirar" un modelo de visión. doc/docx quedan
# afuera a propósito — no hay forma liviana de renderizarlos sin agregar
# LibreOffice o similar, así que esos siguen 100% a revisión manual.
MIME_POR_EXT = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}

SYSTEM_PROMPT = (
    "Sos un asistente que ayuda a un moderador humano a revisar títulos y "
    "certificaciones académicas subidos por personas que se postulan como "
    "tutores en una plataforma educativa. Mirá el documento adjunto y evaluá "
    "si PARECE un título, diploma, certificado o constancia de estudios "
    "legítimo, relacionado con la materia declarada. No estás dando la "
    "aprobación final, el moderador humano decide con tu opinión como una "
    "ayuda más. Respondé ÚNICAMENTE con un JSON, sin texto extra, con esta "
    "forma exacta: "
    '{"is_valid": true o false, "confidence": número entre 0.0 y 1.0, '
    '"reason": "una oración breve en español explicando tu evaluación"}'
)


def tipo_soportado(filename: str) -> bool:
    ext = Path(filename).suffix.lstrip(".").lower()
    return ext in MIME_POR_EXT


def analizar_documento(file_path: Path, materia_declarada: str = "") -> dict:
    """Le manda el documento a un modelo con visión y devuelve
    {is_valid, confidence, reason}. Lanza HTTPException en errores de
    configuración/red — el llamador decide qué hacer con eso."""
    if not OPENROUTER_API_KEY:
        raise HTTPException(
            500, "Falta configurar OPENROUTER_API_KEY en Render para poder usar el análisis con IA."
        )
    if not file_path.exists():
        raise HTTPException(404, "El archivo no está en el almacenamiento.")

    ext = file_path.suffix.lstrip(".").lower()
    mime = MIME_POR_EXT.get(ext)
    if not mime:
        return {
            "is_valid": None,
            "confidence": 0.0,
            "reason": f"Los archivos .{ext} no se pueden analizar automáticamente todavía — revisalo a mano.",
        }

    data_url = f"data:{mime};base64,{base64.b64encode(file_path.read_bytes()).decode()}"
    texto_pedido = f"Materia declarada por quien se postula: {materia_declarada or 'no especificada'}."

    if mime == "application/pdf":
        contenido_usuario = [
            {"type": "text", "text": texto_pedido},
            {"type": "file", "file": {"filename": file_path.name, "file_data": data_url}},
        ]
    else:
        contenido_usuario = [
            {"type": "text", "text": texto_pedido},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]

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
                    {"role": "user", "content": contenido_usuario},
                ],
            },
            timeout=45,
        )
        response.raise_for_status()
        crudo = response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError as e:
        raise HTTPException(502, f"Error al analizar el documento con OpenRouter: {e.response.text}")
    except Exception as e:
        raise HTTPException(502, f"Error al analizar el documento con OpenRouter: {str(e)}")

    return _parsear_respuesta_ia(crudo)


def _parsear_respuesta_ia(crudo: str) -> dict:
    # El modelo a veces envuelve el JSON en ```json ... ``` pese a la
    # instrucción de no hacerlo — lo limpiamos antes de parsear.
    limpio = re.sub(r"^```(json)?|```$", "", crudo.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(limpio)
        confianza = float(data.get("confidence", 0.0))
        return {
            "is_valid": bool(data.get("is_valid", False)),
            "confidence": max(0.0, min(1.0, confianza)),
            "reason": str(data.get("reason", "")).strip() or "Sin motivo detallado.",
        }
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return {
            "is_valid": None,
            "confidence": 0.0,
            "reason": f"No se pudo interpretar la respuesta de la IA: {crudo[:200]}",
        }
