"""
Moderacion automatica de contenido para los foros.

Metodo principal: se le manda el texto a un modelo de lenguaje via OpenRouter
(la misma integracion que ya usan chat.py y ai_verification.py) y se le pide
que juzgue si el texto falta el respeto a otra persona (insultos, acoso,
discurso de odio, amenazas). Si esa llamada falla por cualquier motivo -sin
red, tiempo de espera agotado, respuesta mal formada- se usa un filtro por
palabras clave como respaldo, para que la moderacion nunca quede sin
funcionar del todo aunque OpenRouter no responda.

El resultado siempre se usa para RECHAZAR la publicacion antes de guardarla
en la base: si el contenido no pasa la revision, nunca llega a existir.
"""
import json
import os
import re
import unicodedata

import requests
from fastapi import HTTPException

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")

SYSTEM_PROMPT = (
    "Sos un moderador de un foro academico para estudiantes de nivel secundario "
    "y universitario. Evaluas si un mensaje falta el respeto a otra persona: "
    "insultos, acoso, discriminacion, amenazas o lenguaje de odio. Un debate "
    "firme, una critica dura a una idea, o lenguaje informal NO cuentan como "
    "falta de respeto por si solos. Respondes UNICAMENTE con un JSON, sin texto "
    "extra, con esta forma exacta: "
    '{"apropiado": true o false, "motivo": "una oracion breve en espanol"}'
)

# Respaldo si OpenRouter no responde. Lista corta e imperfecta a proposito:
# es la ultima linea de defensa, no el metodo principal.
PALABRAS_PROHIBIDAS = [
    "boludo de mierda", "hijo de puta", "hija de puta", "la concha de tu madre",
    "andate a la puta", "sos un pelotudo", "sos una pelotuda", "puto de mierda",
    "puta de mierda", "negro de mierda", "negra de mierda", "muerete", "matate",
    "te voy a matar", "te voy a cagar a palos", "sos un retrasado", "sos una retrasada",
    "subnormal", "cancer", "villero de mierda", "sidoso", "sidosa",
]


def _normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_acentos.lower()


def _revisar_por_palabras_clave(texto: str) -> dict:
    normalizado = _normalizar(texto)
    for frase in PALABRAS_PROHIBIDAS:
        if _normalizar(frase) in normalizado:
            return {
                "apropiado": False,
                "motivo": "El texto contiene lenguaje irrespetuoso detectado por el filtro de respaldo.",
                "metodo": "palabras_clave",
            }
    return {"apropiado": True, "motivo": "", "metodo": "palabras_clave"}


def _revisar_con_ia(texto: str) -> dict:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY no configurada")

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
                {"role": "user", "content": texto},
            ],
        },
        timeout=10,
    )
    response.raise_for_status()
    crudo = response.json()["choices"][0]["message"]["content"].strip()
    limpio = re.sub(r"^```(json)?|```$", "", crudo, flags=re.MULTILINE).strip()
    data = json.loads(limpio)
    return {
        "apropiado": bool(data.get("apropiado", True)),
        "motivo": str(data.get("motivo", "")).strip(),
        "metodo": "ia",
    }


def revisar_contenido(texto: str) -> dict:
    """Devuelve {"apropiado", "motivo", "metodo"}. Intenta primero con IA;
    ante cualquier falla, cae al filtro de palabras clave, que nunca falla
    porque no depende de red."""
    try:
        return _revisar_con_ia(texto)
    except Exception:
        return _revisar_por_palabras_clave(texto)


def exigir_contenido_apropiado(texto: str) -> None:
    """Lanza HTTPException 422 si el texto no pasa la revision. Se llama
    ANTES de guardar cualquier post o respuesta en la base."""
    resultado = revisar_contenido(texto)
    if not resultado["apropiado"]:
        motivo = resultado["motivo"] or "El contenido no cumple con las normas de respeto del foro."
        raise HTTPException(422, f"Publicacion rechazada por el moderador automatico: {motivo}")
