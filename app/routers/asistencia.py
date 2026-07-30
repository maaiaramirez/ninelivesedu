import asyncio
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..database import exec_all, exec_one, run, hash_pin

router = APIRouter(prefix="/api/asistencia", tags=["asistencia"])

ESP32_API_KEY = os.environ.get("ESP32_API_KEY", "esp32-local-key")

# Suscriptores para Server-Sent Events (reemplaza services/attendanceRealtime.js)
_subscribers: set[asyncio.Queue] = set()


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


class CheckIn(BaseModel):
    pin: str
    terminalId: str


@router.post("/esp32/check-in")
async def check_in(body: CheckIn, request: Request):
    if request.headers.get("x-esp32-key") != ESP32_API_KEY:
        raise HTTPException(401, "Dispositivo no autorizado")

    teacher = _find_teacher_by_pin(body.pin)
    if not teacher:
        raise HTTPException(404, "PIN inválido")

    run(
        """INSERT INTO teacher_attendance (teacher_user_id, terminal_id, is_available, last_seen_at, updated_at)
           VALUES (?, ?, 1, datetime('now'), datetime('now'))
           ON CONFLICT(teacher_user_id) DO UPDATE SET
             terminal_id = excluded.terminal_id, is_available = 1,
             last_seen_at = datetime('now'), updated_at = datetime('now')""",
        (teacher["userId"], body.terminalId),
    )
    await _publish(_list_available_teachers())
    return {"message": "Asistencia activada",
            "teacher": {"id": teacher["userId"], "nombre": teacher["fullName"]}, "terminalId": body.terminalId}


class CheckOut(BaseModel):
    pin: str


@router.post("/esp32/check-out")
async def check_out(body: CheckOut, request: Request):
    if request.headers.get("x-esp32-key") != ESP32_API_KEY:
        raise HTTPException(401, "Dispositivo no autorizado")

    teacher = _find_teacher_by_pin(body.pin)
    if not teacher:
        raise HTTPException(404, "PIN inválido")

    run(
        "UPDATE teacher_attendance SET is_available = 0, updated_at = datetime('now') WHERE teacher_user_id = ?",
        (teacher["userId"],),
    )
    await _publish(_list_available_teachers())
    return {"message": "Asistencia finalizada", "teacher": {"id": teacher["userId"], "nombre": teacher["fullName"]}}
