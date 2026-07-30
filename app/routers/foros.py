import json
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import exec_all, exec_one, run

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
    rows = exec_all("SELECT * FROM posts ORDER BY date(fecha) DESC")
    return [hydrate(r) for r in rows]


@router.get("/{post_id}")
def obtener_post(post_id: str):
    row = exec_one("SELECT * FROM posts WHERE id = ?", (post_id,))
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


@router.post("", status_code=201)
def crear_post(body: PostIn):
    post_id = f"post-{uuid.uuid4()}"
    fecha = date.today().isoformat()
    tags = body.tags or []
    run(
        """INSERT INTO posts (id, titulo, contenido, autor, fecha, nivel, materia, tipo,
           tags_json, votos, respuestas, vistas, resuelto)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)""",
        (post_id, body.titulo, body.contenido, body.autor, fecha, body.nivel, body.materia,
         body.tipo, json.dumps(tags)),
    )
    return {
        "id": post_id, "titulo": body.titulo, "contenido": body.contenido, "autor": body.autor,
        "fecha": fecha, "nivel": body.nivel, "materia": body.materia, "tipo": body.tipo,
        "tags": tags, "votos": 0, "respuestas": 0, "vistas": 0, "resuelto": False, "responses": [],
    }


@router.post("/{post_id}/vote")
def votar_post(post_id: str):
    post = exec_one("SELECT id, votos FROM posts WHERE id = ?", (post_id,))
    if not post:
        raise HTTPException(404, "Post no encontrado")
    run("UPDATE posts SET votos = votos + 1 WHERE id = ?", (post_id,))
    return {"votos": int(post["votos"]) + 1}


class RespuestaIn(BaseModel):
    autor: str
    texto: str


@router.post("/{post_id}/respuestas", status_code=201)
def agregar_respuesta(post_id: str, body: RespuestaIn):
    post = exec_one("SELECT id FROM posts WHERE id = ?", (post_id,))
    if not post:
        raise HTTPException(404, "Post no encontrado")

    respuesta_id = f"resp-{uuid.uuid4()}"
    fecha = date.today().isoformat()
    run(
        "INSERT INTO post_responses (id, post_id, autor, fecha, texto) VALUES (?, ?, ?, ?, ?)",
        (respuesta_id, post_id, body.autor, fecha, body.texto),
    )
    run("UPDATE posts SET respuestas = respuestas + 1 WHERE id = ?", (post_id,))
    return {"id": respuesta_id, "autor": body.autor, "fecha": fecha, "texto": body.texto}
