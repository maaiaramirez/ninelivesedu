import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel

from ..database import exec_one, run
from ..auth import hash_password, verify_password
from ..user_auth import (
    create_user_session, delete_user_session, require_user, require_role,
    USER_SESSION_COOKIE,
)

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"


# ─────────────────────────────────────────────
# REGISTRO (por ahora solo alumnos — los tutores se dan de alta
# vía /api/tutores/postularse y quedan pendientes de aprobación)
# ─────────────────────────────────────────────
class RegistroIn(BaseModel):
    fullName: str
    email: str
    password: str


@router.post("/registro", status_code=201)
def registro(body: RegistroIn, response: Response):
    email = body.email.strip().lower()
    if exec_one("SELECT id FROM users WHERE email = ?", (email,)):
        raise HTTPException(409, "Ya existe una cuenta con ese email.")
    if len(body.password) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres.")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    run(
        """INSERT INTO users (id, email, full_name, password_hash, role, access_level,
           is_active, validation_status, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'student', 10, 1, 'approved', ?, ?)""",
        (user_id, email, body.fullName.strip(), hash_password(body.password), now, now),
    )

    token, expires = create_user_session(user_id)
    response.set_cookie(USER_SESSION_COOKIE, token, httponly=True, samesite="lax",
                         secure=COOKIE_SECURE, expires=int(expires.timestamp()), path="/")
    return {"success": True, "user": {"id": user_id, "email": email, "fullName": body.fullName, "role": "student"}}


# ─────────────────────────────────────────────
# LOGIN — sirve tanto para alumnos como para tutores ya aprobados
# ─────────────────────────────────────────────
class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginIn, response: Response):
    user = exec_one("SELECT * FROM users WHERE email = ?", (body.email.strip().lower(),))
    if not user or not user["password_hash"] or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Email o contraseña incorrectos.")
    if not user["is_active"]:
        raise HTTPException(403, "Tu cuenta está desactivada.")
    if user["role"] == "teacher" and user["validation_status"] != "approved":
        raise HTTPException(403, "Tu perfil de tutor todavía está en revisión por un moderador.")

    token, expires = create_user_session(user["id"])
    response.set_cookie(USER_SESSION_COOKIE, token, httponly=True, samesite="lax",
                         secure=COOKIE_SECURE, expires=int(expires.timestamp()), path="/")
    return {
        "success": True,
        "user": {"id": user["id"], "email": user["email"], "fullName": user["full_name"], "role": user["role"]},
    }


@router.post("/logout")
def logout(request: Request, response: Response):
    delete_user_session(request.cookies.get(USER_SESSION_COOKIE))
    response.delete_cookie(USER_SESSION_COOKIE, path="/")
    return {"success": True}


@router.get("/me")
def me(user=Depends(require_user)):
    return {"id": user["id"], "email": user["email"], "fullName": user["full_name"], "role": user["role"]}


# ─────────────────────────────────────────────
# EJEMPLOS de rutas protegidas por rol (patrón a reusar en el resto
# de los endpoints reales cuando lleguemos a las otras partes)
# ─────────────────────────────────────────────
@router.get("/panel/alumno")
def panel_alumno(user=Depends(require_role("student"))):
    return {"mensaje": f"Bienvenido, {user['full_name']}. Esta vista es solo para alumnos."}


@router.get("/panel/tutor")
def panel_tutor(user=Depends(require_role("teacher"))):
    return {"mensaje": f"Bienvenido, {user['full_name']}. Esta vista es solo para tutores."}
