from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel
import os
from datetime import datetime, timezone

from ..database import exec_one, run
from ..auth import (
    verify_password, hash_password, create_session, delete_session,
    require_moderator, SESSION_COOKIE_NAME,
)
from ..rate_limit import check_login_rate_limit, reset_login_rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])

# En Render (producción) el sitio siempre es HTTPS, así que la cookie debe ir
# marcada "secure". Para probar en local (http://127.0.0.1) se desactiva con
# COOKIE_SECURE=false en el entorno.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    rate_key = f"{request.client.host}:{body.email.strip().lower()}"
    check_login_rate_limit(rate_key)

    moderator = exec_one("SELECT * FROM moderators WHERE email = ?", (body.email.strip().lower(),))
    if not moderator or not verify_password(body.password, moderator["password_hash"]):
        raise HTTPException(401, "Email o contraseña incorrectos.")

    reset_login_rate_limit(rate_key)
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
def cambiar_password(body: CambiarPasswordIn, request: Request, moderator=Depends(require_moderator)):
    full = exec_one("SELECT * FROM moderators WHERE id = ?", (moderator["id"],))
    if not verify_password(body.currentPassword, full["password_hash"]):
        raise HTTPException(401, "La contraseña actual no es correcta.")
    if len(body.newPassword) < 8:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 8 caracteres.")

    run(
        "UPDATE moderators SET password_hash = ? WHERE id = ?",
        (hash_password(body.newPassword), moderator["id"]),
    )

    # Si alguien más tenía una sesión robada, la matamos acá. Dejamos viva
    # solo la sesión desde la que se hizo el cambio.
    current_token = request.cookies.get(SESSION_COOKIE_NAME)
    run(
        "DELETE FROM moderator_sessions WHERE moderator_id = ? AND token != ?",
        (moderator["id"], current_token),
    )

    return {"success": True, "message": "Contraseña actualizada. Se cerraron todas tus otras sesiones activas."}
