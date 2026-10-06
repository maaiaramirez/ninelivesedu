import json
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..database import exec_all, exec_one, run, registrar_auditoria
from ..content_moderation import exigir_contenido_apropiado, revisar_contenido
from ..user_auth import require_user

router = APIRouter(prefix="/api/foros", tags=["foros"])


def safe_parse(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def hydrate(row: dict) -> dict:
    responses = exec_all(
        "SELECT id, autor, fecha, texto FROM post_responses WHERE post_id = ? ORDER BY date(fecha) ASC, rowid ASC",
        (row["id"],),
    )
    return {
        "id": row["id"], "titulo": row["titulo"], "contenido": row["contenido"], "autor": row["autor"],
        "fecha": row["fecha"], "nivel": row["nivel"], "materia": row["materia"], "tipo": row["tipo"],
        "tags": safe_parse(row["tags_json"], []),
        "votos": int(row["votos"] or 0), "respuestas": int(row["respuestas"] or len(responses)),
        "vistas": int(row["vistas"] or 0), "resuelto": bool(row["resuelto"]), "responses": responses,
    }


@router.get("")
def listar_posts():
    # Solo lo que ya está aprobado es público -- lo "pendiente" (retenido
    # por el análisis automático) no aparece acá, solo en la cola de
    # revisión del panel de moderadores.
    rows = exec_all("SELECT * FROM posts WHERE estado_moderacion = 'aprobado' ORDER BY date(fecha) DESC")
    return [hydrate(r) for r in rows]


@router.get("/{post_id}")
def obtener_post(post_id: str):
    row = exec_one("SELECT * FROM posts WHERE id = ? AND estado_moderacion = 'aprobado'", (post_id,))
    if not row:
        raise HTTPException(404, "Post no encontrado")
    return hydrate(row)


class PostIn(BaseModel):
    titulo: str
    contenido: str
    autor: str
    nivel: str = "universidad"
    materia: str = "general"
    tipo: str = "pregunta"
    tags: Optional[List[str]] = None


def _revisar_o_auditar(texto: str, user, tipo_objetivo: str, objetivo_id: str = None):
    """Igual que exigir_contenido_apropiado, pero además deja constancia en
    auditoría cuando algo se rechaza -- así un moderador puede ver después
    qué se bloqueó y por qué, no solo el usuario que lo escribió."""
    try:
        exigir_contenido_apropiado(texto)
    except HTTPException as e:
        registrar_auditoria(None, user["full_name"] if user else "(desconocido)",
                             "contenido_rechazado_automaticamente", tipo_objetivo, objetivo_id,
                             f"{e.detail}  ·  texto: {texto[:200]}")
        raise


@router.post("", status_code=201)
def crear_post(body: PostIn, user=Depends(require_user)):
    """Si el análisis automático no detecta nada raro, el post se publica
    al toque (estado 'aprobado'). Si sospecha algo (spam, insultos), el
    post NO se pierde ni se publica solo: queda 'pendiente', invisible
    para el público, esperando que un moderador lo revise y decida —
    igual que una postulación de tutor."""
    texto = f"{body.titulo}\n\n{body.contenido}"
    revision = revisar_contenido(texto)
    aprobado = bool(revision.get("apropiado", True))
    estado = "aprobado" if aprobado else "pendiente"

    post_id = f"post-{uuid.uuid4()}"
    fecha = date.today().isoformat()
    tags = body.tags or []
    run(
        """INSERT INTO posts (id, titulo, contenido, autor, fecha, nivel, materia, tipo,
           tags_json, votos, respuestas, vistas, resuelto, autor_user_id,
           estado_moderacion, ai_confidence, ai_reason)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?, ?, ?, ?)""",
        (post_id, body.titulo, body.contenido, body.autor, fecha, body.nivel, body.materia,
         body.tipo, json.dumps(tags), user["id"], estado, None, revision.get("motivo") or None),
    )

    if not aprobado:
        registrar_auditoria(None, user["full_name"], "post_retenido_para_revision", "post", post_id,
                             f"Motivo: {revision.get('motivo', '')}  ·  texto: {texto[:200]}")
        return {
            "id": post_id, "pendiente": True,
            "message": "Tu publicación quedó retenida para revisión de un moderador antes de aparecer en el foro.",
        }

    return {
        "id": post_id, "titulo": body.titulo, "contenido": body.contenido, "autor": body.autor,
        "fecha": fecha, "nivel": body.nivel, "materia": body.materia, "tipo": body.tipo,
        "tags": tags, "votos": 0, "respuestas": 0, "vistas": 0, "resuelto": False, "responses": [],
    }


@router.post("/{post_id}/vote")
def votar_post(post_id: str, user=Depends(require_user)):
    post = exec_one("SELECT id, votos FROM posts WHERE id = ?", (post_id,))
    if not post:
        raise HTTPException(404, "Post no encontrado")
    run("UPDATE posts SET votos = votos + 1 WHERE id = ?", (post_id,))
    return {"votos": int(post["votos"]) + 1}


class RespuestaIn(BaseModel):
    autor: str
    texto: str


@router.post("/{post_id}/respuestas", status_code=201)
def agregar_respuesta(post_id: str, body: RespuestaIn, user=Depends(require_user)):
    post = exec_one("SELECT id FROM posts WHERE id = ?", (post_id,))
    if not post:
        raise HTTPException(404, "Post no encontrado")

    _revisar_o_auditar(body.texto, user, "respuesta", post_id)

    respuesta_id = f"resp-{uuid.uuid4()}"
    fecha = date.today().isoformat()
    run(
        "INSERT INTO post_responses (id, post_id, autor, fecha, texto) VALUES (?, ?, ?, ?, ?)",
        (respuesta_id, post_id, body.autor, fecha, body.texto),
    )
    run("UPDATE posts SET respuestas = respuestas + 1 WHERE id = ?", (post_id,))
    return {"id": respuesta_id, "autor": body.autor, "fecha": fecha, "texto": body.texto}
