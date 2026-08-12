"""
Autenticación de moderadores.
Contraseñas: PBKDF2-HMAC-SHA256 (módulo estándar hashlib, sin dependencias).
Sesiones: token opaco aleatorio guardado en SQLite, enviado como cookie httpOnly.
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request, HTTPException

from .database import exec_one, run

SESSION_COOKIE_NAME = "nle_session"
SESSION_DURATION_HOURS = 12
PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, digest_hex = stored_hash.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_session(moderator_id: str) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=SESSION_DURATION_HOURS)
    run(
        "INSERT INTO moderator_sessions (token, moderator_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, moderator_id, now.isoformat(), expires.isoformat()),
    )
    return token, expires


def get_moderator_by_session(token: str):
    if not token:
        return None
    session = exec_one("SELECT * FROM moderator_sessions WHERE token = ?", (token,))
    if not session:
        return None

    expires_at = datetime.fromisoformat(session["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        run("DELETE FROM moderator_sessions WHERE token = ?", (token,))
        return None

    return exec_one(
        "SELECT id, email, full_name FROM moderators WHERE id = ?",
        (session["moderator_id"],),
    )


def delete_session(token: str):
    if token:
        run("DELETE FROM moderator_sessions WHERE token = ?", (token,))


def require_moderator(request: Request):
    """Dependency de FastAPI: 401 si no hay una sesión de moderador válida."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    moderator = get_moderator_by_session(token)
    if not moderator:
        raise HTTPException(status_code=401, detail="No autenticado. Iniciá sesión como moderador.")
    return moderator
