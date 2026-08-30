"""
auth.py
=======
Todo lo relacionado a "probar que sos quien decís que sos":
- Hasheo de contraseñas (nunca guardamos la contraseña real en la DB).
- Creación y verificación de tokens JWT (lo que usa el frontend para
  demostrar, en cada request, que ya inició sesión).
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
import models

# En Render, seteá esta variable de entorno con un valor largo y random
# (por ejemplo: openssl rand -hex 32). Este default SOLO es para que el
# proyecto arranque en desarrollo local sin configurar nada.
SECRET_KEY = os.environ.get("JWT_SECRET", "cambiar-esto-en-produccion-por-favor")
ALGORITHM = "HS256"
MINUTOS_EXPIRACION = 60 * 24  # el token dura 1 día

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Le dice a FastAPI/Swagger que el login vive en /auth/login, y de ahí
# los clientes tienen que sacar el token para mandarlo en cada request
# como header: "Authorization: Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hashear_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(password_plano: str, password_hash: str) -> bool:
    return pwd_context.verify(password_plano, password_hash)


def crear_token(datos: dict) -> str:
    """Genera un JWT firmado, con la expiración ya incluida adentro."""
    datos_a_codificar = datos.copy()
    expira = datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_EXPIRACION)
    datos_a_codificar.update({"exp": expira})
    return jwt.encode(datos_a_codificar, SECRET_KEY, algorithm=ALGORITHM)


def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """
    Dependencia para usar en cualquier endpoint que requiera login:

        @app.get("/algo-protegido")
        def algo(usuario: models.Usuario = Depends(obtener_usuario_actual)):
            ...

    Lee el token del header Authorization, lo valida, y devuelve el
    Usuario correspondiente. Si el token no existe, expiró, o el
    usuario ya no está en la base, corta con un 401.
    """
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesión",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("sub")
        if usuario_id is None:
            raise credenciales_invalidas
    except JWTError:
        raise credenciales_invalidas

    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    if usuario is None:
        raise credenciales_invalidas

    return usuario
  def requiere_rol(*roles: "models.RolUsuario"):
    """
    Dependencia parametrizable para restringir un endpoint a ciertos roles:
        @router.post("/tutorias")
        def crear_tutoria(usuario: models.Usuario = Depends(requiere_rol(models.RolUsuario.TUTOR, models.RolUsuario.ADMIN))):
            ...
    Reusa obtener_usuario_actual (así ya valida el token) y encima
    chequea que el rol del usuario esté en la lista permitida.
    """
    def verificador(usuario: models.Usuario = Depends(obtener_usuario_actual)) -> models.Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para realizar esta acción",
            )
        return usuario
    return verificador
