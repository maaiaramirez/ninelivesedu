"""
Autenticación de usuarios regulares (alumnos y tutores).
Reusa el mismo hashing que app/auth.py (PBKDF2), pero con su propia tabla
de sesiones y cookie — así un moderador y un alumno pueden tener sesiones
independientes, incluso en el mismo navegador.
"""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request, HTTPException

from .database import exec_one, run
from .auth import hash_password, verify_password  # reusa el mismo hashing

USER_SESSION_COOKIE = "nle_user_session"
SESSION_DURATION_HOURS = 24 * 7  # una semana


def create_user_session(user_id: str) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=SESSION_DURATION_HOURS)
    run(
        "INSERT INTO user_sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, now.isoformat(), expires.isoformat()),
    )
    return token, expires


def get_user_by_session(token: str):
    if not token:
        return None
    session = exec_one("SELECT * FROM user_sessions WHERE token = ?", (token,))
    if not session:
        return None

    expires_at = datetime.fromisoformat(session["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        run("DELETE FROM user_sessions WHERE token = ?", (token,))
        return None

    return exec_one(
        "SELECT id, email, full_name, role, is_active, validation_status FROM users WHERE id = ?",
        (session["user_id"],),
    )


def delete_user_session(token: str):
    if token:
        run("DELETE FROM user_sessions WHERE token = ?", (token,))


def require_user(request: Request):
    """Dependency: 401 si no hay sesión válida de alumno/tutor."""
    token = request.cookies.get(USER_SESSION_COOKIE)
    user = get_user_by_session(token)
    if not user:
        raise HTTPException(401, "Necesitás iniciar sesión para hacer esto.")
    if not user["is_active"]:
        raise HTTPException(403, "Tu cuenta está desactivada. Contactá a un moderador.")
    return user


def require_role(*roles: str):
    """Dependency factory: 403 si el usuario logueado no tiene uno de estos roles.
    Uso: Depends(require_role("teacher"))"""
    def dependency(request: Request):
        user = require_user(request)
        if user["role"] not in roles:
            raise HTTPException(403, f"Esta acción requiere el rol: {', '.join(roles)}.")
        return user
    return dependency
