from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel
import os

from ..database import exec_one
from ..auth import (
    verify_password, create_session, delete_session,
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
