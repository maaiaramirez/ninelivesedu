import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel

from ..database import exec_all, exec_one, run
from ..auth import hash_password
from ..user_auth import require_role

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


SAFE_EXT_BY_MIME = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


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


import random


def _generar_pin() -> str:
    """PIN numérico de 6 dígitos para el hardware (terminal ESP32 de esa sesión)."""
    return f"{random.randint(0, 999999):06d}"


def _cerrar_sesion_y_generar_pin(sesion_id: str) -> str:
    """Marca la sesión como cerrada y le asigna un PIN único, si no lo tenía ya."""
    sesion = exec_one("SELECT * FROM tutoria_sesiones WHERE id = ?", (sesion_id,))
    if sesion["pin_hardware"]:
        return sesion["pin_hardware"]  # ya se había cerrado antes, no generamos otro

    pin = _generar_pin()
    now = datetime.now(timezone.utc).isoformat()
    run(
        "UPDATE tutoria_sesiones SET estado = 'cerrada', pin_hardware = ?, pin_generado_at = ? WHERE id = ?",
        (pin, now, sesion_id),
    )
    return pin


class ReservaIn(BaseModel):
    fecha: str
    modalidad: str = "online"


@router.post("/{tutor_id}/reservas", status_code=201)
def crear_reserva(tutor_id: str, body: ReservaIn, user=Depends(require_role("student"))):
    tutor = exec_one("SELECT * FROM tutores WHERE id = ?", (tutor_id,))
    if not tutor:
        raise HTTPException(404, "Tutor no encontrado")

    # Buscamos una sesión abierta para ese tutor/fecha/modalidad, o creamos una nueva
    sesion = exec_one(
        """SELECT * FROM tutoria_sesiones
           WHERE tutor_id = ? AND fecha = ? AND modalidad = ? AND estado = 'abierta'""",
        (tutor_id, body.fecha, body.modalidad),
    )
    now = datetime.now(timezone.utc).isoformat()

    if not sesion:
        sesion_id = f"sesion-{uuid.uuid4()}"
        run(
            """INSERT INTO tutoria_sesiones (id, tutor_id, fecha, modalidad, cupo_maximo, estado, created_at)
               VALUES (?, ?, ?, ?, ?, 'abierta', ?)""",
            (sesion_id, tutor_id, body.fecha, body.modalidad, tutor["cupo_maximo"], now),
        )
    else:
        sesion_id = sesion["id"]
        # Evitamos que el mismo alumno se anote dos veces a la misma sesión
        ya_anotado = exec_one(
            "SELECT id FROM reservas WHERE sesion_id = ? AND student_user_id = ? AND estado != 'rejected'",
            (sesion_id, user["id"]),
        )
        if ya_anotado:
            raise HTTPException(409, "Ya tenés una reserva para esa fecha con este tutor.")

    reserva_id = f"reserva-{uuid.uuid4()}"
    run(
        """INSERT INTO reservas (id, sesion_id, tutor_id, student_user_id, estudiante, fecha, modalidad, estado, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (reserva_id, sesion_id, tutor_id, user["id"], user["full_name"], body.fecha, body.modalidad, now),
    )

    return {
        "message": "Reserva solicitada. Queda en estado Pendiente hasta que el tutor la confirme.",
        "reserva": {"id": reserva_id, "sesionId": sesion_id, "tutor": tutor["nombre"],
                     "estado": "pending", "fecha": body.fecha, "modalidad": body.modalidad},
    }


@router.get("/mis-reservas/alumno")
def mis_reservas_alumno(user=Depends(require_role("student"))):
    rows = exec_all(
        """SELECT r.id, r.estado AS estado_reserva, r.fecha, r.modalidad, r.pin_alumno,
                  t.nombre AS tutor_nombre, t.materia,
                  s.id AS sesion_id, s.estado AS estado_sesion, s.cupo_maximo, s.pin_hardware
           FROM reservas r
           JOIN tutores t ON t.id = r.tutor_id
           JOIN tutoria_sesiones s ON s.id = r.sesion_id
           WHERE r.student_user_id = ?
           ORDER BY r.created_at DESC""",
        (user["id"],),
    )
    return {"reservas": rows}


@router.get("/mis-sesiones/tutor")
def mis_sesiones_tutor(user=Depends(require_role("teacher"))):
    """Sesiones de las tutorías listadas a nombre de este tutor, vinculadas
    de forma inequívoca por user_id (no por nombre)."""
    tutor = exec_one("SELECT * FROM tutores WHERE user_id = ?", (user["id"],))
    if not tutor:
        return {"sesiones": [], "aviso": "Todavía no tenés un perfil de tutor vinculado en el marketplace."}

    sesiones = exec_all(
        "SELECT * FROM tutoria_sesiones WHERE tutor_id = ? ORDER BY created_at DESC",
        (tutor["id"],),
    )
    for s in sesiones:
        s["alumnos"] = exec_all(
            "SELECT id, estudiante, estado FROM reservas WHERE sesion_id = ? ORDER BY created_at ASC",
            (s["id"],),
        )
    return {"sesiones": sesiones}


def _verificar_dueno_de_sesion(sesion_id: str, user: dict):
    """Lanza 403 si la sesión no pertenece al tutor logueado.
    Corrige el hueco de seguridad: antes, CUALQUIER tutor podía aprobar,
    rechazar o cerrar la sesión de OTRO tutor, porque solo se chequeaba
    el rol ('teacher') y nunca la propiedad real de la sesión."""
    sesion = exec_one("SELECT * FROM tutoria_sesiones WHERE id = ?", (sesion_id,))
    if not sesion:
        raise HTTPException(404, "Sesión no encontrada")

    tutor = exec_one("SELECT * FROM tutores WHERE id = ?", (sesion["tutor_id"],))
    if not tutor or tutor["user_id"] != user["id"]:
        raise HTTPException(403, "Esta sesión no te pertenece.")

    return sesion


def _generar_pin_alumno() -> str:
    """PIN personal de 6 dígitos para que el alumno haga check-in físico en el
    terminal. Es DISTINTO del pin_hardware de la sesión (ese es compartido y
    solo sirve para desbloquear el terminal cuando se llena el cupo de
    inscripción); este identifica a UN alumno puntual para la asistencia.
    Es GLOBALMENTE único (no solo dentro de la sesión): el terminal físico
    solo tiene teclado numérico, así que no puede mandar un sesionId — el
    backend deduce la sesión a partir de este PIN nomás (ver
    check-in-alumno en asistencia.py)."""
    for _ in range(10):
        pin = _generar_pin()
        choque = exec_one("SELECT id FROM reservas WHERE pin_alumno = ?", (pin,))
        if not choque:
            return pin
    raise HTTPException(500, "No se pudo generar un PIN único para el alumno.")


@router.post("/reservas/{reserva_id}/aprobar")
def aprobar_reserva(reserva_id: str, user=Depends(require_role("teacher"))):
    reserva = exec_one("SELECT * FROM reservas WHERE id = ?", (reserva_id,))
    if not reserva:
        raise HTTPException(404, "Reserva no encontrada")

    _verificar_dueno_de_sesion(reserva["sesion_id"], user)

    pin_alumno = _generar_pin_alumno()
    run(
        "UPDATE reservas SET estado = 'confirmed', pin_alumno = ? WHERE id = ?",
        (pin_alumno, reserva_id),
    )

    sesion = exec_one("SELECT * FROM tutoria_sesiones WHERE id = ?", (reserva["sesion_id"],))
    confirmados = exec_one(
        "SELECT COUNT(*) AS n FROM reservas WHERE sesion_id = ? AND estado = 'confirmed'",
        (sesion["id"],),
    )["n"]

    resultado = {
        "success": True, "message": "Reserva aprobada.", "cupoLleno": False, "pin": None,
        "pinAlumno": pin_alumno,
    }

    if confirmados >= sesion["cupo_maximo"] and sesion["estado"] == "abierta":
        pin = _cerrar_sesion_y_generar_pin(sesion["id"])
        resultado.update({
            "message": "Reserva aprobada. ¡Se llenó el cupo! Se generó el PIN de hardware para esta sesión.",
            "cupoLleno": True, "pin": pin,
        })

    return resultado


@router.post("/reservas/{reserva_id}/rechazar")
def rechazar_reserva(reserva_id: str, user=Depends(require_role("teacher"))):
    reserva = exec_one("SELECT * FROM reservas WHERE id = ?", (reserva_id,))
    if not reserva:
        raise HTTPException(404, "Reserva no encontrada")
    _verificar_dueno_de_sesion(reserva["sesion_id"], user)
    run("UPDATE reservas SET estado = 'rejected' WHERE id = ?", (reserva_id,))
    return {"success": True, "message": "Reserva rechazada."}


@router.post("/sesiones/{sesion_id}/cerrar")
def cerrar_sesion_manual(sesion_id: str, user=Depends(require_role("teacher"))):
    """El tutor cierra la inscripción manualmente, aunque no se haya llenado el cupo."""
    sesion = _verificar_dueno_de_sesion(sesion_id, user)
    if sesion["estado"] == "cerrada":
        return {"success": True, "message": "La sesión ya estaba cerrada.", "pin": sesion["pin_hardware"]}

    pin = _cerrar_sesion_y_generar_pin(sesion_id)
    return {"success": True, "message": "Inscripción cerrada manualmente. PIN de hardware generado.", "pin": pin}


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
    password: str = Form(...),
    materia: str = Form(...),
    titulo: UploadFile = File(...),
):
    email = email.strip().lower()

    existente = exec_one("SELECT id FROM users WHERE email = ?", (email,))
    if existente:
        raise HTTPException(409, "Ya existe una solicitud o cuenta registrada con ese email.")
    if len(password) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres.")

    if titulo.content_type not in ALLOWED_DOC_MIMES:
        raise HTTPException(400, "Formato de archivo no permitido. Usá PDF, Word, o una imagen (JPG/PNG).")

    contenido = await titulo.read()
    if len(contenido) > 8 * 1024 * 1024:
        raise HTTPException(400, "El archivo no puede superar los 8 MB.")

    filename = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}.{SAFE_EXT_BY_MIME[titulo.content_type]}"
    dest = UPLOADS_DIR / filename
    with open(dest, "wb") as f:
        f.write(contenido)
    archivo_path = f"/uploads/{filename}"

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    run(
        """INSERT INTO users (id, email, full_name, password_hash, role, access_level, is_active,
           validation_status, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'teacher', 40, 1, 'pending', ?, ?)""",
        (user_id, email, nombreCompleto.strip(), hash_password(password), now, now),
    )
    run(
        """INSERT INTO teacher_profiles (user_id, credential_document_path, credential_document_status, materia_interes)
           VALUES (?, ?, 'pending', ?)""",
        (user_id, archivo_path, materia.strip()),
    )

    return {
        "success": True,
        "message": "¡Listo! Tu solicitud fue enviada y está en revisión. Una vez aprobada vas a poder iniciar sesión con tu email y contraseña.",
    }
