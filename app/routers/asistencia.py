import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..database import exec_all, exec_one, run, hash_pin

router = APIRouter(prefix="/api/asistencia", tags=["asistencia"])

# Router SIN prefijo: expone /ws/aula/{aula_id} tal cual lo espera el firmware
# del ESP32 (mismo path que en el ejemplo de referencia), pero ya conectado
# a la base de datos real y con validación de PIN.
ws_router = APIRouter(tags=["asistencia-ws"])

ESP32_API_KEY = os.environ.get("ESP32_API_KEY", "esp32-local-key")

# Suscriptores para Server-Sent Events (el frontend de asistencia.html sigue
# funcionando igual, sin cambios — recibe las mismas actualizaciones).
_subscribers: set[asyncio.Queue] = set()

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
        await q.put(payload)


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
                payload = await queue.get()
                yield f"event: attendance\ndata: {payload}\n\n"
        finally:
            _subscribers.discard(queue)

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
