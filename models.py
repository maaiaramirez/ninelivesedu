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

# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class RolUsuario(str, enum.Enum):
    ALUMNO = "alumno"
    TUTOR = "tutor"
    ADMIN = "admin"

class EstadoTutoria(str, enum.Enum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    CERRADA = "cerrada"
    CANCELADA = "cancelada"

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    rol = Column(Enum(RolUsuario), default=RolUsuario.ALUMNO, nullable=False)
    kyc_verificado = Column(Boolean, default=False)  # relevante para tutores
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    tutorias_dictadas = relationship("Tutoria", back_populates="tutor", foreign_keys="Tutoria.tutor_id")
    inscripciones = relationship("Inscripcion", back_populates="alumno")
    apuntes_subidos = relationship("Apunte", back_populates="autor")

class Tutoria(Base):
    __tablename__ = "tutorias"
    id = Column(Integer, primary_key=True, index=True)
    tutor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    materia = Column(String, nullable=False)
    descripcion = Column(Text)
    cupo_maximo = Column(Integer, nullable=False)
    fecha_hora = Column(DateTime(timezone=True), nullable=False)
    estado = Column(Enum(EstadoTutoria), default=EstadoTutoria.PENDIENTE)
    pin_acceso = Column(String(6), nullable=True, unique=True)  # se genera al cerrar inscripción
    pin_usado = Column(Boolean, default=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    tutor = relationship("Usuario", back_populates="tutorias_dictadas", foreign_keys=[tutor_id])
    inscripciones = relationship("Inscripcion", back_populates="tutoria")

class Inscripcion(Base):
    __tablename__ = "inscripciones"
    id = Column(Integer, primary_key=True, index=True)
    tutoria_id = Column(Integer, ForeignKey("tutorias.id"), nullable=False)
    alumno_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    estado = Column(Enum(EstadoTutoria), default=EstadoTutoria.PENDIENTE)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    tutoria = relationship("Tutoria", back_populates="inscripciones")
    alumno = relationship("Usuario", back_populates="inscripciones")

class Apunte(Base):
    __tablename__ = "apuntes"
    id = Column(Integer, primary_key=True, index=True)
    autor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    titulo = Column(String, nullable=False)
    materia = Column(String, nullable=False)
    descripcion = Column(Text)
    precio = Column(Numeric(10, 2), default=0)  # 0 = gratis/intercambio
    archivo_url = Column(String, nullable=False)  # referencia a storage, no el binario
    disponible = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    autor = relationship("Usuario", back_populates="apuntes_subidos")
    transacciones = relationship("Transaccion", back_populates="apunte")

class EstadoTransaccion(str, enum.Enum):
    PENDIENTE = "pendiente"
    COMPLETADA = "completada"
    FALLIDA = "fallida"

class Transaccion(Base):
    __tablename__ = "transacciones"
    id = Column(Integer, primary_key=True, index=True)
    apunte_id = Column(Integer, ForeignKey("apuntes.id"), nullable=False)
    comprador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    estado = Column(Enum(EstadoTransaccion), default=EstadoTransaccion.PENDIENTE)
    referencia_pago = Column(String, nullable=True)  # id de MercadoPago/Stripe
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    apunte = relationship("Apunte", back_populates="transacciones")

class Comentario(Base):
    __tablename__ = "comentarios"
    id = Column(Integer, primary_key=True, index=True)
    foro_id = Column(Integer, ForeignKey("foros.id"), nullable=False)
    autor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    contenido = Column(Text, nullable=False)
    fue_filtrado = Column(Boolean, default=False)
    oculto_por_mod = Column(Boolean, default=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

class Foro(Base):
    __tablename__ = "foros"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    materia = Column(String)
    creado_por = Column(Integer, ForeignKey("usuarios.id"))
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
