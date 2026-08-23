"""
database.py
===========
Configura la conexion a la base de datos. No define tablas ni logica de
negocio, solo la "caneria" para que el resto del backend hable con la
base de datos sin repetir esta configuracion en cada archivo.

Usamos PostgreSQL (la variable de entorno DATABASE_URL, que en Render
te da el servicio de PostgreSQL que crees aparte). Para poder programar
y probar en tu PC sin instalar Postgres, si esa variable no esta
seteada, cae automaticamente a un archivo SQLite local.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./nine_lives_edu.db")

# Render entrega la URL con el prefijo "postgres://", pero SQLAlchemy 1.4+
# y 2.x exigen "postgresql://". Lo corregimos automaticamente para no
# tener que acordarnos de hacerlo a mano cada vez.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# connect_args solo hace falta para SQLite (permite usarlo desde varios
# threads a la vez, algo que FastAPI necesita y SQLite no habilita solo).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# SessionLocal es una "fabrica" de sesiones. Cada request a la API pide
# su propia sesion nueva (ver get_db() mas abajo) y la cierra al
# terminar, para no dejar conexiones abiertas colgadas.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base es la clase de la que heredan todos los modelos de tabla
# (ver models.py). SQLAlchemy usa esto para saber que clases representan
# tablas y poder generarlas automaticamente.
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: abre una sesion de DB y la cierra sola al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
