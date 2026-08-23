"""
models.py
=========
Define las tablas de la base de datos usando SQLAlchemy ORM. Cada clase
de aca abajo se traduce en una tabla real de PostgreSQL.

Hay 4 tablas, con responsabilidades bien separadas:

1) Usuario         -> login: cualquier persona (estudiante, tutor o admin)
2) Tutor           -> datos extra de un Usuario con rol "tutor" (1 a 1)
3) Aula            -> el ESTADO ACTUAL de cada aula/terminal fisico
4) HistorialEstado -> el historial completo e inalterable de cambios

Por que Usuario y Tutor son tablas separadas en vez de una sola: no
todos los usuarios son tutores (hay estudiantes y admins tambien), y un
tutor tiene datos que un estudiante no necesita (especialidad, codigo
de acceso al hardware). Separarlas evita columnas vacias/sin sentido
para la mayoria de los usuarios.
"""

import enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class RolUsuario(str, enum.Enum):
    estudiante = "estudiante"
    tutor = "tutor"
    admin = "admin"


class EstadoAula(str, enum.Enum):
    INAC = "INAC"
    DISP = "DISP"
    OCUP = "OCUP"


class Usuario(Base):
    """Cualquier persona que puede loguearse: estudiante, tutor o admin."""
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # nunca se guarda la contraseña en texto plano
    rol = Column(Enum(RolUsuario), default=RolUsuario.estudiante, nullable=False)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())

    # Relacion 1 a 1: si este usuario es tutor, aca esta el resto de sus datos.
    tutor = relationship("Tutor", back_populates="usuario", uselist=False)


class Tutor(Base):
    """
    Datos adicionales de un Usuario con rol='tutor'. El campo clave es
    codigo_acceso: es EL MISMO codigo que el tutor tipea en el teclado
    del terminal fisico (ver el aviso de sincronizacion en el README).
    """
    __tablename__ = "tutores"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    especialidad = Column(String(120), nullable=True)          # "Matematica", "Programacion", etc
    codigo_acceso = Column(String(20), unique=True, nullable=False)

    usuario = relationship("Usuario", back_populates="tutor")
    historial = relationship("HistorialEstado", back_populates="tutor")

    @property
    def nombre(self):
        """Atajo para no tener que navegar tutor.usuario.nombre en cada schema."""
        return self.usuario.nombre if self.usuario else None


class Aula(Base):
    """Una fila por cada aula/terminal fisico instalado. Guarda el estado ACTUAL."""
    __tablename__ = "aulas"

    id = Column(Integer, primary_key=True, index=True)
    # Identificador legible que coincide con AULA_ID en el firmware (.ino), ej "A1".
    identificador = Column(String(20), unique=True, nullable=False, index=True)
    nombre = Column(String(120), nullable=False)                 # "Aula de Matematica"
    estado_actual = Column(Enum(EstadoAula), default=EstadoAula.INAC, nullable=False)
    tutor_actual_id = Column(Integer, ForeignKey("tutores.id"), nullable=True)

    tutor_actual = relationship("Tutor")
    historial = relationship(
        "HistorialEstado",
        back_populates="aula",
        order_by="desc(HistorialEstado.timestamp)",
    )


class HistorialEstado(Base):
    """
    Una fila por cada cambio de estado que ocurrio en el tiempo. Nunca se
    actualiza ni se borra una fila existente: siempre se agrega una fila
    nueva. Asi queda un historial completo e inalterado.
    """
    __tablename__ = "historial_estados"

    id = Column(Integer, primary_key=True, index=True)
    aula_id = Column(Integer, ForeignKey("aulas.id"), nullable=False, index=True)
    tutor_id = Column(Integer, ForeignKey("tutores.id"), nullable=True)

    estado = Column(Enum(EstadoAula), nullable=False)
    codigo_usado = Column(String(20), nullable=True)  # el codigo tipeado, o "sync"/"forzado_desde_panel"
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    aula = relationship("Aula", back_populates="historial")
    tutor = relationship("Tutor", back_populates="historial")
