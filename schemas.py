"""
schemas.py
==========
Define la "forma" de los datos que entran y salen de la API (JSON),
usando Pydantic. Esto es DISTINTO de models.py (que define las tablas):
separar ambas cosas permite, por ejemplo, no exponer el password_hash
por accidente en una respuesta, o pedir campos distintos a los que
se guardan en la tabla.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr

from models import RolUsuario, EstadoAula


# ---------- Autenticacion ----------

class UsuarioRegistro(BaseModel):
    """Lo que se manda al crear una cuenta nueva."""
    nombre: str
    email: EmailStr
    password: str
    rol: RolUsuario = RolUsuario.estudiante
    especialidad: str | None = None    # solo se usa si rol == "tutor"
    codigo_acceso: str | None = None   # solo se usa si rol == "tutor"


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    """Lo que devolvemos de un usuario (nunca el password_hash)."""
    id: int
    nombre: str
    email: EmailStr
    rol: RolUsuario
    fecha_registro: datetime

    class Config:
        from_attributes = True  # permite construir esto directo desde un objeto SQLAlchemy


# ---------- Aulas / Historial ----------

class TutorResumen(BaseModel):
    """Version resumida de un tutor, para mostrar dentro de AulaOut."""
    id: int
    nombre: str
    especialidad: str | None = None

    class Config:
        from_attributes = True


class AulaOut(BaseModel):
    id: int
    identificador: str
    nombre: str
    estado_actual: EstadoAula
    tutor_actual: TutorResumen | None = None

    class Config:
        from_attributes = True


class HistorialOut(BaseModel):
    estado: EstadoAula
    codigo_usado: str | None = None
    timestamp: datetime
    tutor: TutorResumen | None = None

    class Config:
        from_attributes = True
