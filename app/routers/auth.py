from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel
import os
import uuid
from datetime import datetime, timezone

from ..database import exec_one, run
from ..auth import (
    verify_password, hash_password, create_session, delete_session,
    require_moderator, SESSION_COOKIE_NAME,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# En Render (producción) el sitio siempre es HTTPS, así que la cookie debe ir
# marcada "secure". Para probar en local (http://127.0.0.1) se desactiva con
# COOKIE_SECURE=false en el entorno.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginIn, response: Response):
    moderator = exec_one("SELECT * FROM moderators WHERE email = ?", (body.email.strip().lower(),))
    if not moderator or not verify_password(body.password, moderator["password_hash"]):
        raise HTTPException(401, "Email o contraseña incorrectos.")

    token, expires = create_session(moderator["id"])
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        expires=int(expires.timestamp()),
        path="/",
    )
    return {
        "success": True,
        "moderator": {"id": moderator["id"], "email": moderator["email"], "fullName": moderator["full_name"]},
    }


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    delete_session(token)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"success": True}


@router.get("/me")
def me(moderator=Depends(require_moderator)):
    return {"id": moderator["id"], "email": moderator["email"], "fullName": moderator["full_name"]}


class CambiarPasswordIn(BaseModel):
    currentPassword: str
    newPassword: str


@router.post("/cambiar-password")
def cambiar_password(body: CambiarPasswordIn, moderator=Depends(require_moderator)):
    full = exec_one("SELECT * FROM moderators WHERE id = ?", (moderator["id"],))
    if not verify_password(body.currentPassword, full["password_hash"]):
        raise HTTPException(401, "La contraseña actual no es correcta.")
    if len(body.newPassword) < 8:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 8 caracteres.")

    run(
        "UPDATE moderators SET password_hash = ? WHERE id = ?",
        (hash_password(body.newPassword), moderator["id"]),
    )
    return {"success": True, "message": "Contraseña actualizada."}


class NuevoModeradorIn(BaseModel):
    email: str
    password: str
    fullName: str


@router.post("/moderadores")
def crear_moderador(body: NuevoModeradorIn, moderator=Depends(require_moderator)):
    """Solo un moderador ya logueado puede dar de alta a otro."""
    email = body.email.strip().lower()
    if exec_one("SELECT id FROM moderators WHERE email = ?", (email,)):
        raise HTTPException(409, "Ya existe un moderador con ese email.")
    if len(body.password) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres.")

    now = datetime.now(timezone.utc).isoformat()
    run(
        "INSERT INTO moderators (id, email, password_hash, full_name, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), email, hash_password(body.password), body.fullName.strip(), now),
    )
    return {"success": True, "message": f"Moderador {body.fullName} creado."}
