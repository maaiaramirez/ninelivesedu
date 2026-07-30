import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import exec_all, exec_one, run

router = APIRouter(prefix="/api/tutores", tags=["tutores"])


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
