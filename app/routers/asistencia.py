import asyncio
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..database import exec_all, exec_one, run, hash_pin
from ..user_auth import require_role

router = APIRouter(prefix="/api/asistencia", tags=["asistencia"])

# Router SIN prefijo: expone /ws/aula/{aula_id} tal cual lo espera el firmware
# del ESP32 (mismo path que en el ejemplo de referencia), pero ya conectado
# a la base de datos real y con validación de PIN.
ws_router = APIRouter(tags=["asistencia-ws"])

ESP32_API_KEY = os.environ.get("ESP32_API_KEY", "esp32-local-key")

# Suscriptores para Server-Sent Events del jardín de profesores
# (asistencia.html). Cada item en la cola es (nombre_evento, payload_json);
# el generador de /stream simplemente los reenvía tal cual, así que agregar
# nuevos tipos de evento (ej. "aforo") no rompe a quien solo escucha
# "attendance" como hacía antes.
_subscribers: set[asyncio.Queue] = set()

# Suscriptores para SSE del dashboard del ALUMNO (mi-cuenta.html), uno por
# usuario logueado — así la encuesta de satisfacción solo le llega a los
# alumnos que realmente estuvieron en esa sesión, no a todo el mundo.
_alumno_subscribers: Dict[str, set[asyncio.Queue]] = {}

# Conexiones WebSocket activas por aula/terminal: hardware y navegadores
# comparten el mismo canal, igual que en el ejemplo de referencia.
_connections_by_aula: Dict[str, List[WebSocket]] = {}
_last_estado_by_aula: Dict[str, dict] = {}


def _list_available_teachers():
    rows = exec_all(
        """SELECT u.id AS user_id, u.full_name, u.email, ta.terminal_id, ta.last_seen_at, ta.updated_at
           FROM teacher_attendance ta
           INNER JOIN users u ON u.id = ta.teacher_user_id
           WHERE u.role = 'teacher' AND u.validation_status = 'approved' AND ta.is_available = 1
           ORDER BY u.full_name ASC"""
    )
    return [
        {"userId": r["user_id"], "fullName": r["full_name"], "email": r["email"],
         "terminalId": r["terminal_id"], "lastSeenAt": r["last_seen_at"], "updatedAt": r["updated_at"]}
        for r in rows
    ]


def _find_teacher_by_pin(pin: str):
    pin_hash = hash_pin(pin)
    return exec_one(
        """SELECT u.id AS userId, u.full_name AS fullName
           FROM teacher_profiles tp
           INNER JOIN users u ON u.id = tp.user_id
           WHERE u.role = 'teacher' AND u.validation_status = 'approved' AND tp.unique_pin_ciphertext = ?""",
        (pin_hash,),
    )


async def _publish(teachers):
    payload = json.dumps({
        "type": "attendance:update",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "teachers": teachers,
    })
    for q in list(_subscribers):
        await q.put(("attendance", payload))


async def _publish_aforo(sesion_id: str, cupo_actual: int, cupo_maximo: int):
    """Notifica en vivo el aforo de una sesión (para paneles de moderación o
    la propia pantalla del terminal). Va en un evento SSE separado
    ('aforo') para no interferir con quien solo escucha 'attendance'."""
    payload = json.dumps({
        "type": "aforo:update", "sesionId": sesion_id,
        "cupoActual": cupo_actual, "cupoMaximo": cupo_maximo,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    for q in list(_subscribers):
        await q.put(("aforo", payload))


async def _publish_a_alumno(student_user_id: str, payload: dict):
    """Empuja un evento SSE únicamente a las pestañas abiertas de ESE alumno
    (dashboard en mi-cuenta.html). Si no tiene ninguna conexión abierta en
    este momento, el evento simplemente no se entrega en vivo; el estado
    'encuesta pendiente' queda igual en la base para cuando vuelva a entrar."""
    data = json.dumps(payload)
    for q in list(_alumno_subscribers.get(student_user_id, set())):
        await q.put(("encuesta", data))


async def _broadcast_ws(aula_id: str, mensaje: dict, excluir: WebSocket = None):
    """Reenvía un mensaje a todos los clientes WebSocket conectados a esa aula/terminal."""
    for conexion in list(_connections_by_aula.get(aula_id, [])):
        if conexion is excluir:
            continue
        try:
            await conexion.send_json(mensaje)
        except Exception:
            pass


def _hacer_checkin(pin: str, terminal_id: str):
    teacher = _find_teacher_by_pin(pin)
    if not teacher:
        return None
    run(
        """INSERT INTO teacher_attendance (teacher_user_id, terminal_id, is_available, last_seen_at, updated_at)
           VALUES (?, ?, 1, datetime('now'), datetime('now'))
           ON CONFLICT(teacher_user_id) DO UPDATE SET
             terminal_id = excluded.terminal_id, is_available = 1,
             last_seen_at = datetime('now'), updated_at = datetime('now')""",
        (teacher["userId"], terminal_id),
    )
    return teacher


def _hacer_checkout(pin: str):
    teacher = _find_teacher_by_pin(pin)
    if not teacher:
        return None
    run(
        "UPDATE teacher_attendance SET is_available = 0, updated_at = datetime('now') WHERE teacher_user_id = ?",
        (teacher["userId"],),
    )
    return teacher


@router.get("/profesores-disponibles")
def profesores_disponibles():
    teachers = _list_available_teachers()
    return {"total": len(teachers), "teachers": teachers}


@router.get("/stream")
async def stream(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.add(queue)

    async def event_generator():
        try:
            yield 'event: connected\ndata: {"status":"ok"}\n\n'
            await _publish(_list_available_teachers())
            while True:
                if await request.is_disconnected():
                    break
                evento, payload = await queue.get()
                yield f"event: {evento}\ndata: {payload}\n\n"
        finally:
            _subscribers.discard(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/stream/alumno")
async def stream_alumno(request: Request, user=Depends(require_role("student"))):
    """SSE privado del alumno logueado: es lo que escucha mi-cuenta.html
    para disparar el modal de encuesta apenas el tutor hace check-out."""
    queue: asyncio.Queue = asyncio.Queue()
    _alumno_subscribers.setdefault(user["id"], set()).add(queue)

    async def event_generator():
        try:
            yield 'event: connected\ndata: {"status":"ok"}\n\n'
            while True:
                if await request.is_disconnected():
                    break
                evento, payload = await queue.get()
                yield f"event: {evento}\ndata: {payload}\n\n"
        finally:
            _alumno_subscribers.get(user["id"], set()).discard(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ─────────────────────────────────────────────
# WEBSOCKET — canal en vivo para el hardware (ESP32) y navegadores
#
# El ESP32 se conecta a:  wss://tu-dominio.onrender.com/ws/aula/{aula_id}
# (usá el mismo {aula_id} como identificador de esa terminal física)
#
# Mensajes que el firmware puede enviar (JSON, uno por línea):
#   {"tipo": "checkin",  "pin": "123456", "terminalId": "terminal-aula-1"}
#   {"tipo": "checkout", "pin": "123456"}
#   {"tipo": "estado", ...}   → cualquier otro dato (ej. sensores), se
#                               reenvía tal cual a los demás conectados
#                               en esa misma aula, sin tocar la base.
# ─────────────────────────────────────────────
@ws_router.websocket("/ws/aula/{aula_id}")
async def websocket_aula(websocket: WebSocket, aula_id: str):
    await websocket.accept()
    _connections_by_aula.setdefault(aula_id, []).append(websocket)

    if aula_id in _last_estado_by_aula:
        await websocket.send_json(_last_estado_by_aula[aula_id])

    try:
        while True:
            data = await websocket.receive_text()

            try:
                mensaje = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"tipo": "error", "detalle": "JSON inválido"})
                continue

            tipo = mensaje.get("tipo")

            if tipo == "checkin":
                teacher = _hacer_checkin(mensaje.get("pin", ""), mensaje.get("terminalId", aula_id))
                if not teacher:
                    await websocket.send_json({"tipo": "error", "detalle": "PIN inválido"})
                    continue
                estado = {
                    "tipo": "estado", "evento": "checkin", "aulaId": aula_id,
                    "profesor": {"id": teacher["userId"], "nombre": teacher["fullName"]},
                    "disponible": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                _last_estado_by_aula[aula_id] = estado
                await websocket.send_json(estado)  # confirmación al propio hardware
                await _broadcast_ws(aula_id, estado, excluir=websocket)
                await _publish(_list_available_teachers())  # también notifica a quienes usan SSE

            elif tipo == "checkout":
                teacher = _hacer_checkout(mensaje.get("pin", ""))
                if not teacher:
                    await websocket.send_json({"tipo": "error", "detalle": "PIN inválido"})
                    continue
                estado = {
                    "tipo": "estado", "evento": "checkout", "aulaId": aula_id,
                    "profesor": {"id": teacher["userId"], "nombre": teacher["fullName"]},
                    "disponible": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                _last_estado_by_aula[aula_id] = estado
                await websocket.send_json(estado)
                await _broadcast_ws(aula_id, estado, excluir=websocket)
                await _publish(_list_available_teachers())

            elif tipo == "estado":
                # Paso libre para telemetría adicional del hardware (sensores, etc.)
                _last_estado_by_aula[aula_id] = mensaje
                await _broadcast_ws(aula_id, mensaje, excluir=websocket)

            else:
                await websocket.send_json({"tipo": "error", "detalle": f"Tipo de mensaje desconocido: {tipo}"})

    except WebSocketDisconnect:
        if websocket in _connections_by_aula.get(aula_id, []):
            _connections_by_aula[aula_id].remove(websocket)


class CheckIn(BaseModel):
    pin: str
    terminalId: str


@router.post("/esp32/check-in")
async def check_in(body: CheckIn, request: Request):
    if request.headers.get("x-esp32-key") != ESP32_API_KEY:
        raise HTTPException(401, "Dispositivo no autorizado")

    teacher = _hacer_checkin(body.pin, body.terminalId)
    if not teacher:
        raise HTTPException(404, "PIN inválido")

    await _publish(_list_available_teachers())
    return {"message": "Asistencia activada",
            "teacher": {"id": teacher["userId"], "nombre": teacher["fullName"]}, "terminalId": body.terminalId}


class CheckOut(BaseModel):
    pin: str


@router.post("/esp32/check-out")
async def check_out(body: CheckOut, request: Request):
    if request.headers.get("x-esp32-key") != ESP32_API_KEY:
        raise HTTPException(401, "Dispositivo no autorizado")

    teacher = _hacer_checkout(body.pin)
    if not teacher:
        raise HTTPException(404, "PIN inválido")

    await _publish(_list_available_teachers())
    return {"message": "Asistencia finalizada", "teacher": {"id": teacher["userId"], "nombre": teacher["fullName"]}}


# ═════════════════════════════════════════════════════════════════════════
# ASISTENCIA DUAL POR SESIÓN — Propuesta técnica
#
# Máquina de estados por sesión (tabla asistencia_fisica.estado):
#
#   bloqueada  --check-in-tutor-->  activa  --check-out-tutor-->  completada
#                                     |
#                                     '--check-in-alumno (repetible, con
#                                         control de aforo transaccional)
#
# El check-in de alumnos SOLO se acepta mientras la sesión está 'activa',
# es decir, después de que el profesor abrió el terminal con su PIN.
# ═════════════════════════════════════════════════════════════════════════

def _get_sesion_o_404(sesion_id: str) -> dict:
    sesion = exec_one("SELECT * FROM tutoria_sesiones WHERE id = ?", (sesion_id,))
    if not sesion:
        raise HTTPException(404, "Sesión no encontrada.")
    return sesion


def _estado_fisico(sesion_id: str) -> str:
    row = exec_one("SELECT estado FROM asistencia_fisica WHERE sesion_id = ?", (sesion_id,))
    return row["estado"] if row else "bloqueada"


def _requerir_esp32(request: Request):
    """Mismo esquema de autenticación de dispositivo que ya usaban
    /esp32/check-in y /esp32/check-out: el terminal manda x-esp32-key y
    tiene que matchear ESP32_API_KEY. Sin esto, cualquiera con la URL del
    backend podría hacer check-in/out sin tener el hardware físico."""
    if request.headers.get("x-esp32-key") != ESP32_API_KEY:
        raise HTTPException(401, "Dispositivo no autorizado")


def _resolver_sesion_para_tutor(tutor_id: str) -> dict | None:
    """El teclado del terminal solo tiene números y *, # — no hay forma
    práctica de que el profesor tipee un sesionId ahí. Por eso el backend
    resuelve solo CUÁL sesión corresponde:
      1) si ya hay una sesión 'activa' de este tutor, esa (para el checkout);
      2) si no, la sesión de HOY (por fecha) que todavía no esté 'completada'.
    Esto asume el supuesto típico de un terminal fijo por aula/tutor con una
    sola tutoría por día; si un tutor da dos tutorías el mismo día, hay que
    pasar sesionId explícito (el frontend web sigue pudiendo hacerlo)."""
    activa = exec_one(
        """SELECT s.* FROM tutoria_sesiones s
           JOIN asistencia_fisica af ON af.sesion_id = s.id
           WHERE s.tutor_id = ? AND af.estado = 'activa'
           ORDER BY s.created_at DESC LIMIT 1""",
        (tutor_id,),
    )
    if activa:
        return activa

    hoy = datetime.now(timezone.utc).date().isoformat()
    return exec_one(
        """SELECT s.* FROM tutoria_sesiones s
           LEFT JOIN asistencia_fisica af ON af.sesion_id = s.id
           WHERE s.tutor_id = ? AND s.fecha = ?
             AND (af.estado IS NULL OR af.estado != 'completada')
           ORDER BY s.created_at DESC LIMIT 1""",
        (tutor_id, hoy),
    )


class CheckInTutorIn(BaseModel):
    pin: str
    terminalId: str = "terminal-esp32"
    sesionId: str | None = None  # opcional: solo lo manda el frontend web, no el teclado físico


@router.post("/check-in-tutor")
async def check_in_tutor(body: CheckInTutorIn, request: Request):
    """El profesor abre el terminal con su PIN personal. Desbloquea la
    sesión para que, a partir de acá, el mismo terminal acepte los PIN de
    los alumnos. Idempotente: si ya estaba activa, no rompe nada."""
    _requerir_esp32(request)

    teacher = _find_teacher_by_pin(body.pin)
    if not teacher:
        raise HTTPException(404, "PIN de docente inválido.")

    tutor = exec_one("SELECT * FROM tutores WHERE user_id = ?", (teacher["userId"],))
    if not tutor:
        raise HTTPException(404, "Este profesor no tiene un perfil de tutor vinculado en el marketplace.")

    if body.sesionId:
        sesion = _get_sesion_o_404(body.sesionId)
        if sesion["tutor_id"] != tutor["id"]:
            raise HTTPException(403, "Esta sesión no pertenece a este profesor.")
    else:
        sesion = _resolver_sesion_para_tutor(tutor["id"])
        if not sesion:
            raise HTTPException(404, "No se encontró una sesión de hoy para este profesor.")

    estado_actual = _estado_fisico(sesion["id"])
    if estado_actual == "completada":
        raise HTTPException(409, "Esta sesión ya fue cerrada (check-out ya realizado).")

    if estado_actual == "bloqueada":
        now = datetime.now(timezone.utc).isoformat()
        run(
            """INSERT INTO asistencia_fisica (sesion_id, estado, tutor_checkin_at)
               VALUES (?, 'activa', ?)
               ON CONFLICT(sesion_id) DO UPDATE SET
                 estado = 'activa', tutor_checkin_at = excluded.tutor_checkin_at""",
            (sesion["id"], now),
        )

    # Mantiene también el "jardín de profesores disponibles" que ya usaba asistencia.html
    _hacer_checkin(body.pin, body.terminalId)
    await _publish(_list_available_teachers())

    return {
        "message": "Check-in del tutor confirmado. La sesión queda activa para recibir alumnos.",
        "profesor": {"id": teacher["userId"], "nombre": teacher["fullName"]},
        "sesionId": sesion["id"],
        "estadoSesion": "activa",
    }


class CheckInAlumnoIn(BaseModel):
    pin: str
    terminalId: str = "terminal-esp32"


@router.post("/check-in-alumno")
async def check_in_alumno(body: CheckInAlumnoIn, request: Request):
    """Check-in físico del alumno. El PIN del alumno es personal y GLOBALMENTE
    único (se genera al aprobar la reserva — ver tutores.py), así que el
    terminal no necesita decirle al backend a qué sesión pertenece: se
    deduce de la propia reserva. Valida, en este orden:
       1) que el PIN corresponda a una reserva CONFIRMADA (o sea, que el
          alumno haya contratado y le hayan aprobado esa tutoría antes),
       2) que el profesor de ESA sesión ya la haya abierto en el terminal,
       3) que todavía haya cupo — el COUNT y el INSERT posterior corren
          dentro de la misma transacción de get_conn(), y el
          UNIQUE(sesion_id, student_user_id) evita que una carrera de dos
          pedidos casi simultáneos duplique el check-in del mismo alumno."""
    _requerir_esp32(request)

    reserva = exec_one(
        """SELECT r.*, u.full_name AS student_full_name
           FROM reservas r
           JOIN users u ON u.id = r.student_user_id
           WHERE r.pin_alumno = ? AND r.estado = 'confirmed'""",
        (body.pin,),
    )
    if not reserva:
        raise HTTPException(404, "PIN inválido, o todavía no tenés esta tutoría contratada y confirmada.")

    sesion = _get_sesion_o_404(reserva["sesion_id"])

    if _estado_fisico(sesion["id"]) != "activa":
        raise HTTPException(403, "El profesor todavía no inició la sesión en el terminal.")

    cupo_actual = exec_one(
        "SELECT COUNT(*) AS n FROM asistencia_alumnos WHERE sesion_id = ?", (sesion["id"],)
    )["n"]
    if cupo_actual >= sesion["cupo_maximo"]:
        # El ESP32 intercepta este 409 y muestra "Cupo lleno" en el LCD.
        raise HTTPException(409, "Cupo lleno para esta sesión.")

    now = datetime.now(timezone.utc).isoformat()
    try:
        run(
            """INSERT INTO asistencia_alumnos (id, sesion_id, student_user_id, reserva_id, checkin_at)
               VALUES (?, ?, ?, ?, ?)""",
            (f"asist-{uuid.uuid4()}", sesion["id"], reserva["student_user_id"], reserva["id"], now),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Este alumno ya había registrado su asistencia en esta sesión.")

    cupo_actual += 1
    await _publish_aforo(sesion["id"], cupo_actual, sesion["cupo_maximo"])

    return {
        "message": "Asistencia del alumno registrada.",
        "alumno": {"id": reserva["student_user_id"], "nombre": reserva["student_full_name"]},
        "cupoActual": cupo_actual,
        "cupoMaximo": sesion["cupo_maximo"],
    }


async def _disparar_encuestas(sesion_id: str):
    """Background Task: se ejecuta DESPUÉS de responder el check-out del
    profesor (no bloquea al terminal ESP32 esperando esto). Por cada
    alumno que hizo check-in y todavía no completó la encuesta, empuja un
    evento SSE a SU dashboard para que aparezca el formulario."""
    sesion = exec_one("SELECT * FROM tutoria_sesiones WHERE id = ?", (sesion_id,))
    if not sesion:
        return
    tutor = exec_one("SELECT * FROM tutores WHERE id = ?", (sesion["tutor_id"],))

    alumnos = exec_all(
        """SELECT student_user_id FROM asistencia_alumnos
           WHERE sesion_id = ? AND encuesta_completada = 0""",
        (sesion_id,),
    )
    for a in alumnos:
        await _publish_a_alumno(a["student_user_id"], {
            "type": "encuesta:disponible",
            "sesionId": sesion_id,
            "tutorId": sesion["tutor_id"],
            "tutorNombre": tutor["nombre"] if tutor else None,
            "materia": tutor["materia"] if tutor else None,
        })


class CheckOutTutorIn(BaseModel):
    pin: str
    terminalId: str = "terminal-esp32"
    sesionId: str | None = None


@router.post("/check-out-tutor")
async def check_out_tutor(body: CheckOutTutorIn, background_tasks: BackgroundTasks, request: Request):
    """Cierre de la clase por parte del profesor. Marca la sesión como
    'completada' y delega el disparo de las encuestas a un Background Task
    de FastAPI/Uvicorn, para que el terminal reciba su confirmación al
    instante sin esperar a que se notifique a cada alumno por SSE."""
    _requerir_esp32(request)

    teacher = _find_teacher_by_pin(body.pin)
    if not teacher:
        raise HTTPException(404, "PIN de docente inválido.")

    tutor = exec_one("SELECT * FROM tutores WHERE user_id = ?", (teacher["userId"],))
    if not tutor:
        raise HTTPException(404, "Este profesor no tiene un perfil de tutor vinculado en el marketplace.")

    if body.sesionId:
        sesion = _get_sesion_o_404(body.sesionId)
        if sesion["tutor_id"] != tutor["id"]:
            raise HTTPException(403, "Esta sesión no pertenece a este profesor.")
    else:
        sesion = _resolver_sesion_para_tutor(tutor["id"])
        if not sesion:
            raise HTTPException(404, "Este profesor no tiene ninguna sesión activa para cerrar.")

    if _estado_fisico(sesion["id"]) != "activa":
        raise HTTPException(409, "La sesión no está activa (no se hizo check-in, o ya se cerró).")

    now = datetime.now(timezone.utc).isoformat()
    run(
        "UPDATE asistencia_fisica SET estado = 'completada', tutor_checkout_at = ? WHERE sesion_id = ?",
        (now, sesion["id"]),
    )
    _hacer_checkout(body.pin)
    await _publish(_list_available_teachers())

    background_tasks.add_task(_disparar_encuestas, sesion["id"])

    total_alumnos = exec_one(
        "SELECT COUNT(*) AS n FROM asistencia_alumnos WHERE sesion_id = ?", (sesion["id"],)
    )["n"]

    return {
        "message": "Check-out del tutor confirmado. Sesión cerrada, encuestas en camino.",
        "sesionId": sesion["id"],
        "estadoSesion": "completada",
        "alumnosAsistieron": total_alumnos,
    }


class EncuestaIn(BaseModel):
    sesionId: str
    puntaje: int = Field(..., ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=500)


@router.post("/encuestas")
def enviar_encuesta(body: EncuestaIn, user=Depends(require_role("student"))):
    """El alumno envía la encuesta de satisfacción disparada por SSE. Pydantic
    ya validó/saneó puntaje (1-5) y el largo del comentario antes de llegar
    acá; solo falta comprobar que la asistencia sea real y no esté duplicada."""
    asistencia = exec_one(
        "SELECT * FROM asistencia_alumnos WHERE sesion_id = ? AND student_user_id = ?",
        (body.sesionId, user["id"]),
    )
    if not asistencia:
        raise HTTPException(404, "No se encontró un check-in tuyo para esta sesión.")
    if asistencia["encuesta_completada"]:
        raise HTTPException(409, "Ya enviaste la encuesta de esta sesión.")

    sesion = _get_sesion_o_404(body.sesionId)
    now = datetime.now(timezone.utc).isoformat()

    run(
        """INSERT INTO encuestas_satisfaccion (id, sesion_id, student_user_id, tutor_id, puntaje, comentario, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (f"encuesta-{uuid.uuid4()}", body.sesionId, user["id"], sesion["tutor_id"],
         body.puntaje, body.comentario, now),
    )
    run(
        "UPDATE asistencia_alumnos SET encuesta_completada = 1 WHERE sesion_id = ? AND student_user_id = ?",
        (body.sesionId, user["id"]),
    )

    return {"message": "¡Gracias por tu respuesta!"}
