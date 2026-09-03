import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from ..database import exec_all, exec_one, run

router = APIRouter(prefix="/api/tutores", tags=["tutores"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "storage" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_DOC_MIMES = {
    "application/pdf", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png", "image/jpeg", "image/webp",
}


def clean_filename(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9._-]", "-", name)
    return re.sub(r"-+", "-", name)


def safe_parse(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def normalize(row: dict) -> dict:
    return {
        "id": row["id"], "nombre": row["nombre"], "materia": row["materia"], "nivel": row["nivel"],
        "precio": float(row["precio"]), "rating": float(row["rating"]), "experiencia": row["experiencia"],
        "foto": row["foto"], "biografia": row["biografia"],
        "materias": safe_parse(row["materias_json"], []),
        "disponibilidad": safe_parse(row["disponibilidad_json"], {}),
        "idiomas": safe_parse(row["idiomas_json"], []),
        "reseñas": safe_parse(row["resenas_json"], []),
    }


@router.get("")
def listar_tutores():
    rows = exec_all("SELECT * FROM tutores ORDER BY nombre ASC")
    return [normalize(r) for r in rows]


@router.get("/{tutor_id}")
def obtener_tutor(tutor_id: str):
    row = exec_one("SELECT * FROM tutores WHERE id = ?", (tutor_id,))
    if not row:
        raise HTTPException(404, "Tutor no encontrado")
    return normalize(row)


class ReservaIn(BaseModel):
    estudiante: str
    fecha: str
    modalidad: str = "online"


@router.post("/{tutor_id}/reservas", status_code=201)
def crear_reserva(tutor_id: str, body: ReservaIn):
    row = exec_one("SELECT * FROM tutores WHERE id = ?", (tutor_id,))
    if not row:
        raise HTTPException(404, "Tutor no encontrado")

    reserva_id = f"reserva-{uuid.uuid4()}"
    created_at = datetime.now(timezone.utc).isoformat()
    run(
        """INSERT INTO reservas (id, tutor_id, estudiante, fecha, modalidad, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (reserva_id, tutor_id, body.estudiante, body.fecha, body.modalidad, created_at),
    )
    return {
        "message": "Reserva solicitada. El tutor confirmará la disponibilidad.",
        "reserva": {"id": reserva_id, "tutor": row["nombre"], "estudiante": body.estudiante,
                     "fecha": body.fecha, "modalidad": body.modalidad},
    }


class IntercambioIn(BaseModel):
    nombre: str
    materiaOfreces: str
    materiaSolicitas: str
    descripcion: str = None


@router.post("/intercambios", status_code=201)
def crear_intercambio(body: IntercambioIn):
    solicitud_id = f"swap-{uuid.uuid4()}"
    fecha = datetime.now(timezone.utc).isoformat()
    run(
        """INSERT INTO swap_requests (id, nombre, materia_ofreces, materia_solicitas, descripcion, fecha)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (solicitud_id, body.nombre, body.materiaOfreces, body.materiaSolicitas,
         body.descripcion or "Sin descripción adicional", fecha),
    )
    return {
        "message": "Solicitud de intercambio registrada. Te notificaremos cuando encontremos un match.",
        "solicitud": {"id": solicitud_id, "nombre": body.nombre, "materia_ofreces": body.materiaOfreces,
                       "materia_solicitas": body.materiaSolicitas, "fecha": fecha},
    }


# ─────────────────────────────────────────────
# POSTULACIÓN COMO TUTOR (con subida de título/certificación)
#
# Crea un usuario con role='teacher' y validation_status='pending', más un
# registro en teacher_profiles con el documento subido, a la espera de que
# un moderador lo apruebe o rechace desde /moderadores.html.
# ─────────────────────────────────────────────
@router.post("/postularse", status_code=201)
async def postularse_como_tutor(
    nombreCompleto: str = Form(...),
    email: str = Form(...),
    materia: str = Form(...),
    titulo: UploadFile = File(...),
):
    email = email.strip().lower()

    existente = exec_one("SELECT id FROM users WHERE email = ?", (email,))
    if existente:
        raise HTTPException(409, "Ya existe una solicitud o cuenta registrada con ese email.")

    if titulo.content_type not in ALLOWED_DOC_MIMES:
        raise HTTPException(400, "Formato de archivo no permitido. Usá PDF, Word, o una imagen (JPG/PNG).")

    contenido = await titulo.read()
    if len(contenido) > 8 * 1024 * 1024:
        raise HTTPException(400, "El archivo no puede superar los 8 MB.")

    filename = f"{int(time.time() * 1000)}-{clean_filename(titulo.filename)}"
    dest = UPLOADS_DIR / filename
    with open(dest, "wb") as f:
        f.write(contenido)
    archivo_path = f"/uploads/{filename}"

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    run(
        """INSERT INTO users (id, email, full_name, role, access_level, is_active,
           validation_status, created_at, updated_at)
           VALUES (?, ?, ?, 'teacher', 40, 1, 'pending', ?, ?)""",
        (user_id, email, nombreCompleto.strip(), now, now),
    )
    run(
        """INSERT INTO teacher_profiles (user_id, credential_document_path, credential_document_status, materia_interes)
           VALUES (?, ?, 'pending', ?)""",
        (user_id, archivo_path, materia.strip()),
    )

    return {
        "success": True,
        "message": "¡Listo! Tu solicitud fue enviada y está en revisión. Te vamos a contactar por email apenas la validemos.",
    }
