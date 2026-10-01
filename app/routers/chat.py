import os
import re

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import exec_all

router = APIRouter(prefix="/api", tags=["chat"])

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# "openrouter/free" es el auto-router de OpenRouter: elige solo entre los
# modelos gratuitos disponibles, así seguimos funcionando aunque un modelo
# puntual deje de estar gratis (la lista rota seguido).
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")

SYSTEM_PROMPT = (
    "Sos Wawa AI, el asistente de estudio de la plataforma Nine Lives Edu. "
    "Ayudás a estudiantes a encontrar apuntes, tutores, y resolver dudas académicas. "
    "Respondé siempre en español, de forma breve, cálida y clara.\n\n"
    "Vas a recibir, antes de cada mensaje del usuario, un bloque 'DATOS REALES DE LA "
    "PLATAFORMA' con lo que la búsqueda encontró en la base de datos real para esa "
    "consulta. Son las ÚNICAS fuentes que podés citar como existentes en Nine Lives "
    "Edu: nunca inventes ni des por hecho un apunte o un tutor que no esté en ese "
    "bloque. Si el bloque dice que no se encontró nada, decilo con honestidad y "
    "sugerí revisar el catálogo completo en la plataforma, en vez de inventar un "
    "resultado que suene plausible."
)

# Palabras muy comunes que no aportan como término de búsqueda.
_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "y", "o", "a", "en",
    "que", "para", "con", "por", "me", "mi", "tu", "su", "hay", "hola", "como",
    "cómo", "qué", "cuales", "cuáles", "tiene", "tienen", "tenés", "tenes",
    "busco", "quiero", "necesito", "podes", "podés", "puedes", "recomendar",
    "recomendame", "recomendás", "recomendas", "disponible", "disponibles",
    "ahora", "haya", "hubo", "están", "estan", "esta", "estás", "estas",
    # palabras "meta" (describen QUÉ se pide, no de qué tema; matchean casi
    # cualquier fila porque el propio catálogo las usa en sus descripciones)
    "apunte", "apuntes", "tutor", "tutores", "plataforma", "materia", "materias",
}


def _terminos_busqueda(mensaje: str) -> list[str]:
    palabras = re.findall(r"[a-záéíóúñA-ZÁÉÍÓÚÑ]+", mensaje.lower())
    return [p for p in palabras if len(p) >= 4 and p not in _STOPWORDS][:5]


def _buscar_contexto_real(mensaje: str) -> str:
    """Busca en apuntes y tutores reales por los términos del mensaje, y arma
    un bloque de texto con lo encontrado (o la aclaración de que no hubo
    resultados), para que el modelo no tenga que inventar nada."""
    terminos = _terminos_busqueda(mensaje)
    if not terminos:
        return "No se detectaron términos de búsqueda claros en el mensaje."

    condiciones = " OR ".join(["titulo LIKE ? OR materia LIKE ? OR descripcion LIKE ?"] * len(terminos))
    params = []
    for t in terminos:
        like = f"%{t}%"
        params += [like, like, like]
    apuntes = exec_all(
        f"SELECT titulo, materia, nivel, autor FROM apuntes WHERE {condiciones} LIMIT 5",
        tuple(params),
    )

    condiciones_t = " OR ".join(["nombre LIKE ? OR materia LIKE ?"] * len(terminos))
    params_t = []
    for t in terminos:
        like = f"%{t}%"
        params_t += [like, like]
    tutores = exec_all(
        f"SELECT nombre, materia, nivel, rating FROM tutores WHERE {condiciones_t} LIMIT 5",
        tuple(params_t),
    )

    if not apuntes and not tutores:
        return f"Búsqueda por los términos {terminos}: no se encontró ningún apunte ni tutor en la base real de la plataforma que coincida."

    partes = []
    if apuntes:
        lista = "; ".join(f"\"{a['titulo']}\" ({a['materia']}, nivel {a['nivel']}, por {a['autor'] or 'autor no especificado'})" for a in apuntes)
        partes.append(f"Apuntes reales encontrados: {lista}.")
    else:
        partes.append("No se encontraron apuntes reales que coincidan con la búsqueda.")
    if tutores:
        lista = "; ".join(f"{t['nombre']} ({t['materia']}, nivel {t['nivel']}, calificación {t['rating']})" for t in tutores)
        partes.append(f"Tutores reales encontrados: {lista}.")
    else:
        partes.append("No se encontraron tutores reales que coincidan con la búsqueda.")
    return " ".join(partes)


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(body: ChatRequest):
    if not body.message or not body.message.strip():
        raise HTTPException(400, "El mensaje no puede estar vacío.")

    if not OPENROUTER_API_KEY:
        raise HTTPException(500, "Falta configurar la variable de entorno OPENROUTER_API_KEY en Render.")

    contexto = _buscar_contexto_real(body.message)
    mensaje_con_contexto = f"DATOS REALES DE LA PLATAFORMA (para esta consulta): {contexto}\n\nMensaje del usuario: {body.message}"

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
                    {"role": "user", "content": mensaje_con_contexto},
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
