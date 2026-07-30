"""
Base de datos SQLite (usa el módulo estándar sqlite3, sin dependencias externas).
Reemplaza a src/db/database.js (Node + sql.js).
"""
import sqlite3
import hashlib
import os
import json
from pathlib import Path
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "storage" / "ninelivesedu.sqlite"
DB_FILE.parent.mkdir(parents=True, exist_ok=True)

PIN_HASH_SECRET = os.environ.get("PIN_HASH_SECRET", "nine-lives-edu-pin-secret")


def hash_pin(pin: str) -> str:
    return hashlib.sha256(f"{PIN_HASH_SECRET}:{pin}".encode()).hexdigest()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def exec_all(sql, params=()):
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def exec_one(sql, params=()):
    rows = exec_all(sql, params)
    return rows[0] if rows else None


def run(sql, params=()):
    with get_conn() as conn:
        conn.execute(sql, params)


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student','tutor','teacher','admin')),
    access_level INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    validation_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teacher_profiles (
    user_id TEXT PRIMARY KEY,
    credential_document_path TEXT,
    credential_document_status TEXT DEFAULT 'pending',
    unique_pin_ciphertext TEXT UNIQUE,
    pin_issued_at TEXT,
    hardware_terminal_alias TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS teacher_attendance (
    teacher_user_id TEXT PRIMARY KEY,
    terminal_id TEXT NOT NULL,
    is_available INTEGER NOT NULL DEFAULT 0,
    last_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (teacher_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS apuntes (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    materia TEXT NOT NULL,
    nivel TEXT NOT NULL,
    autor TEXT,
    fecha TEXT NOT NULL,
    descripcion TEXT,
    tipo TEXT,
    rating REAL DEFAULT 0,
    descargas INTEGER DEFAULT 0,
    icono TEXT,
    archivo TEXT
);

CREATE TABLE IF NOT EXISTS tutores (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    materia TEXT NOT NULL,
    nivel TEXT NOT NULL,
    precio REAL NOT NULL,
    rating REAL DEFAULT 0,
    experiencia TEXT,
    foto TEXT,
    biografia TEXT,
    materias_json TEXT,
    disponibilidad_json TEXT,
    idiomas_json TEXT,
    resenas_json TEXT
);

CREATE TABLE IF NOT EXISTS reservas (
    id TEXT PRIMARY KEY,
    tutor_id TEXT NOT NULL,
    estudiante TEXT NOT NULL,
    fecha TEXT NOT NULL,
    modalidad TEXT DEFAULT 'online',
    created_at TEXT NOT NULL,
    FOREIGN KEY (tutor_id) REFERENCES tutores(id)
);

CREATE TABLE IF NOT EXISTS swap_requests (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    materia_ofreces TEXT NOT NULL,
    materia_solicitas TEXT NOT NULL,
    descripcion TEXT,
    fecha TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    contenido TEXT NOT NULL,
    autor TEXT NOT NULL,
    fecha TEXT NOT NULL,
    nivel TEXT,
    materia TEXT,
    tipo TEXT,
    tags_json TEXT,
    votos INTEGER DEFAULT 0,
    respuestas INTEGER DEFAULT 0,
    vistas INTEGER DEFAULT 0,
    resuelto INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS post_responses (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    autor TEXT NOT NULL,
    fecha TEXT NOT NULL,
    texto TEXT NOT NULL,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);
"""


def init_database():
    with get_conn() as conn:
        conn.executescript(SCHEMA)

    seed_teacher_demo()
    seed_if_empty()


def seed_teacher_demo():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    teacher_id = "teacher-demo-1"

    if not exec_one("SELECT id FROM users WHERE id = ?", (teacher_id,)):
        run(
            """INSERT INTO users (id, email, full_name, role, access_level, is_active,
               validation_status, created_at, updated_at)
               VALUES (?, ?, ?, 'teacher', 80, 1, 'approved', ?, ?)""",
            (teacher_id, "profesor.demo@ninelivesedu.org", "Profesor Demo", now, now),
        )
        run(
            """INSERT INTO teacher_profiles (user_id, credential_document_path,
               credential_document_status, unique_pin_ciphertext, pin_issued_at, hardware_terminal_alias)
               VALUES (?, '/docs/profesor-demo.pdf', 'approved', ?, ?, 'terminal-demo-1')""",
            (teacher_id, hash_pin("123456"), now),
        )


def seed_if_empty():
    from .data_seed import APUNTES, TUTORES, POSTS

    if not exec_one("SELECT id FROM apuntes LIMIT 1"):
        for a in APUNTES:
            run(
                """INSERT INTO apuntes (id, titulo, materia, nivel, autor, fecha,
                   descripcion, tipo, rating, descargas, icono, archivo)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (a["id"], a["titulo"], a["materia"], a["nivel"], a["autor"], a["fecha"],
                 a["descripcion"], a["tipo"], a["rating"], a["descargas"], a["icono"], a["archivo"]),
            )

    if not exec_one("SELECT id FROM tutores LIMIT 1"):
        for t in TUTORES:
            run(
                """INSERT INTO tutores (id, nombre, materia, nivel, precio, rating, experiencia,
                   foto, biografia, materias_json, disponibilidad_json, idiomas_json, resenas_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (t["id"], t["nombre"], t["materia"], t["nivel"], t["precio"], t["rating"],
                 t["experiencia"], t["foto"], t["biografia"],
                 json.dumps(t["materias"]), json.dumps(t["disponibilidad"]),
                 json.dumps(t["idiomas"]), json.dumps(t["resenas"])),
            )

    if not exec_one("SELECT id FROM posts LIMIT 1"):
        for p in POSTS:
            run(
                """INSERT INTO posts (id, titulo, contenido, autor, fecha, nivel, materia, tipo,
                   tags_json, votos, respuestas, vistas, resuelto)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (p["id"], p["titulo"], p["contenido"], p["autor"], p["fecha"], p["nivel"],
                 p["materia"], p["tipo"], json.dumps(p["tags"]), p["votos"], p["respuestas"],
                 p["vistas"], 1 if p["resuelto"] else 0),
            )
            for r in p.get("responses", []):
                run(
                    """INSERT INTO post_responses (id, post_id, autor, fecha, texto)
                       VALUES (?, ?, ?, ?, ?)""",
                    (r["id"], p["id"], r["autor"], r["fecha"], r["texto"]),
                )
