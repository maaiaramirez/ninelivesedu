"""
Límite de intentos de login — en memoria, alcanza y sobra para un solo
proceso de Render (que es como corre este proyecto hoy). Si en algún
momento escalan a más de una instancia del servicio, esto habría que
moverlo a algo compartido (Redis, la propia base, etc.) porque cada
proceso tendría su propio contador.
"""
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException

WINDOW_SECONDS = 15 * 60  # ventana de 15 minutos
MAX_ATTEMPTS = 5          # intentos permitidos por clave dentro de la ventana

_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def check_login_rate_limit(key: str) -> None:
    """Lanza HTTPException 429 si `key` ya superó el límite de intentos
    en la ventana de tiempo. Se llama ANTES de verificar la contraseña,
    para no gastar tiempo/CPU validando un intento que ya está bloqueado.
    Si no está bloqueado, este intento queda registrado."""
    now = time.time()
    with _lock:
        attempts = _attempts[key]
        attempts[:] = [t for t in attempts if now - t < WINDOW_SECONDS]
        if len(attempts) >= MAX_ATTEMPTS:
            espera_min = max(1, int((WINDOW_SECONDS - (now - attempts[0])) // 60) + 1)
            raise HTTPException(
                429,
                f"Demasiados intentos fallidos. Probá de nuevo en {espera_min} minuto(s).",
            )
        attempts.append(now)


def reset_login_rate_limit(key: str) -> None:
    """Limpia el contador de `key` después de un login exitoso, para que
    un usuario legítimo no quede limitado por errores de tipeo previos."""
    with _lock:
        _attempts.pop(key, None)
