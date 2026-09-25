"""
Base de datos. Por defecto usa SQLite local (módulo estándar sqlite3, sin
dependencias externas) -- útil para desarrollo local. Si está configurada
la variable de entorno TURSO_DATABASE_URL, usa en cambio Turso (libSQL)
como base remota persistente, que es lo que corre en producción: el disco
del plan gratis de Render es efímero (se borra en cada deploy y cada vez
que el servicio se duerme por inactividad), así que sin una base externa
como Turso, todo lo que se crea en la app desaparece solo.

TODA la app (routers incluidos) sigue llamando exec_one/exec_all/run
exactamente igual que antes -- este archivo es el único que sabe si por
detrás hay un archivo .sqlite local o una base Turso remota.
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

TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

_turso_client = None
if TURSO_DATABASE_URL:
    import libsql_client
    # libsql_client habla HTTP (más simple y más robusto en un servicio web
    # de un solo proceso que websockets persistentes) -- la URL que da Turso
    # viene como "libsql://...", que esta librería traduciría a "wss://" por
    # defecto; se fuerza "https://" en su lugar a propósito.
    _turso_http_url = TURSO_DATABASE_URL.replace("libsql://", "https://", 1)
    _turso_client = libsql_client.create_client_sync(
        url=_turso_http_url, auth_token=TURSO_AUTH_TOKEN
    )


def hash_pin(pin: str) -> str:
    return hashlib.sha256(f"{PIN_HASH_SECRET}:{pin}".encode()).hexdigest()


@contextmanager
def get_conn():
    """Solo se usa en el modo SQLite local (sin Turso configurado)."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def exec_all(sql, params=()):
    if _turso_client:
        rs = _turso_client.execute(sql, list(params))
        return [r.asdict() for r in rs.rows]
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def exec_one(sql, params=()):
    rows = exec_all(sql, params)
    return rows[0] if rows else None


def run(sql, params=()):
    if _turso_client:
        _turso_client.execute(sql, list(params))
        return
    with get_conn() as conn:
        conn.execute(sql, params)


def _statements_del_schema(sql_multiple):
    """Turso/libsql_client ejecuta UNA sentencia por vez (a diferencia de
    sqlite3.executescript, que corre un script completo de un saque) --
    separa el SCHEMA en sentencias individuales para poder mandarlas todas
    juntas con _turso_client.batch()."""
    statements = []
    for chunk in sql_multiple.split(";"):
        sin_comentarios = "\n".join(
            linea for linea in chunk.splitlines() if not linea.strip().startswith("--")
        ).strip()
        if sin_comentarios:
            statements.append(sin_comentarios)
    return statements


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT,
    role TEXT NOT NULL CHECK (role IN ('student','tutor','teacher','admin')),
    access_level INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    validation_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS teacher_profiles (
    user_id TEXT PRIMARY KEY,
    credential_document_path TEXT,
    credential_document_status TEXT DEFAULT 'pending',
    materia_interes TEXT,
    unique_pin_ciphertext TEXT UNIQUE,
    pin_issued_at TEXT,
    hardware_terminal_alias TEXT,
    ai_is_valid INTEGER,
    ai_confidence REAL,
    ai_reason TEXT,
    ai_reviewed_at TEXT,
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
    user_id TEXT,
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
    resenas_json TEXT,
    cupo_maximo INTEGER NOT NULL DEFAULT 4,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Una sesión agrupa a todos los alumnos que contratan al mismo tutor,
-- misma fecha y misma modalidad. El cupo y el PIN de hardware viven acá,
-- no en cada reserva individual.
CREATE TABLE IF NOT EXISTS tutoria_sesiones (
    id TEXT PRIMARY KEY,
    tutor_id TEXT NOT NULL,
    fecha TEXT NOT NULL,
    modalidad TEXT DEFAULT 'online',
    cupo_maximo INTEGER NOT NULL,
    estado TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta','cerrada')),
    pin_hardware TEXT,
    pin_generado_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tutor_id) REFERENCES tutores(id)
);

CREATE TABLE IF NOT EXISTS reservas (
    id TEXT PRIMARY KEY,
    sesion_id TEXT NOT NULL,
    tutor_id TEXT NOT NULL,
    student_user_id TEXT,
    estudiante TEXT NOT NULL,
    fecha TEXT NOT NULL,
    modalidad TEXT DEFAULT 'online',
    estado TEXT NOT NULL DEFAULT 'pending' CHECK (estado IN ('pending','confirmed','rejected')),
    pin_alumno TEXT UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tutor_id) REFERENCES tutores(id),
    FOREIGN KEY (sesion_id) REFERENCES tutoria_sesiones(id),
    FOREIGN KEY (student_user_id) REFERENCES users(id)
);

-- Máquina de estados de la asistencia FÍSICA de la sesión (terminal ESP32):
-- bloqueada -> activa (check-in del tutor) -> completada (check-out del tutor).
-- Es independiente del estado de INSCRIPCIÓN (tutoria_sesiones.estado), que
-- sigue rigiendo cupo de reservas/PIN de hardware compartido como antes.
CREATE TABLE IF NOT EXISTS asistencia_fisica (
    sesion_id TEXT PRIMARY KEY,
    estado TEXT NOT NULL DEFAULT 'bloqueada' CHECK (estado IN ('bloqueada','activa','completada')),
    tutor_checkin_at TEXT,
    tutor_checkout_at TEXT,
    FOREIGN KEY (sesion_id) REFERENCES tutoria_sesiones(id)
);

-- Registro de presencia física de cada alumno en una sesión. El UNIQUE
-- evita doble check-in y, junto al COUNT(*) por sesion_id, es la fuente
-- de verdad del aforo en tiempo real.
CREATE TABLE IF NOT EXISTS asistencia_alumnos (
    id TEXT PRIMARY KEY,
    sesion_id TEXT NOT NULL,
    student_user_id TEXT NOT NULL,
    reserva_id TEXT NOT NULL,
    checkin_at TEXT NOT NULL,
    encuesta_completada INTEGER NOT NULL DEFAULT 0,
    UNIQUE (sesion_id, student_user_id),
    FOREIGN KEY (sesion_id) REFERENCES tutoria_sesiones(id),
    FOREIGN KEY (student_user_id) REFERENCES users(id),
    FOREIGN KEY (reserva_id) REFERENCES reservas(id)
);

CREATE TABLE IF NOT EXISTS encuestas_satisfaccion (
    id TEXT PRIMARY KEY,
    sesion_id TEXT NOT NULL,
    student_user_id TEXT NOT NULL,
    tutor_id TEXT NOT NULL,
    puntaje INTEGER NOT NULL CHECK (puntaje BETWEEN 1 AND 5),
    comentario TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (sesion_id, student_user_id),
    FOREIGN KEY (sesion_id) REFERENCES tutoria_sesiones(id),
    FOREIGN KEY (student_user_id) REFERENCES users(id),
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

CREATE TABLE IF NOT EXISTS moderators (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS moderator_sessions (
    token TEXT PRIMARY KEY,
    moderator_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (moderator_id) REFERENCES moderators(id) ON DELETE CASCADE
);
"""


def init_database():
    if _turso_client:
        _turso_client.batch(_statements_del_schema(SCHEMA))
    else:
        with get_conn() as conn:
            conn.executescript(SCHEMA)

    _migrar_columnas_faltantes()
    seed_teacher_demo()
    seed_pending_examples()
    seed_moderator()
    seed_if_empty()


def _migrar_columnas_faltantes():
    """SQLite no agrega columnas nuevas a una tabla que ya existe solo con
    CREATE TABLE IF NOT EXISTS — si el archivo .sqlite viene de antes de
    que existieran estas columnas, hay que sumarlas a mano. ALTER TABLE
    ADD COLUMN falla si la columna ya está, así que lo ignoramos."""
    columnas_nuevas = {
        "teacher_profiles": [
            ("ai_is_valid", "INTEGER"),
            ("ai_confidence", "REAL"),
            ("ai_reason", "TEXT"),
            ("ai_reviewed_at", "TEXT"),
        ],
        "reservas": [
            ("pin_alumno", "TEXT"),
        ],
    }
    for tabla, columnas in columnas_nuevas.items():
        for nombre, tipo in columnas:
            try:
                run(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}")
            except Exception:
                pass  # ya existía (sqlite3.OperationalError en local, LibsqlError en Turso)


def seed_moderator():
    """
    Crea el moderador inicial si no existe ninguno todavía.
    Usa las variables de entorno MODERATOR_EMAIL / MODERATOR_PASSWORD si están
    definidas; si no, cae en credenciales de ejemplo que hay que cambiar.
    """
    from datetime import datetime, timezone
    import uuid
    from .auth import hash_password

    if exec_one("SELECT id FROM moderators LIMIT 1"):
        return

    email = os.environ.get("MODERATOR_EMAIL", "admin@ninelivesedu.org")
    password = os.environ.get("MODERATOR_PASSWORD", "changeme123")
    now = datetime.now(timezone.utc).isoformat()

    run(
        """INSERT INTO moderators (id, email, password_hash, full_name, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), email, hash_password(password), "Moderador Principal", now),
    )


def seed_pending_examples():
    """Un par de solicitudes de ejemplo, para que el panel de moderadores tenga
    algo que mostrar de entrada."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    ejemplos = [
        ("teacher-pending-1", "laura.gimenez@example.com", "Laura Giménez", "/docs/laura-titulo.pdf"),
        ("teacher-pending-2", "martin.suarez@example.com", "Martín Suárez", "/docs/martin-titulo.pdf"),
    ]
    for uid, email, name, doc in ejemplos:
        if exec_one("SELECT id FROM users WHERE id = ?", (uid,)):
            continue
        run(
            """INSERT INTO users (id, email, full_name, role, access_level, is_active,
               validation_status, created_at, updated_at)
               VALUES (?, ?, ?, 'teacher', 60, 1, 'pending', ?, ?)""",
            (uid, email, name, now, now),
        )
        run(
            """INSERT INTO teacher_profiles (user_id, credential_document_path, credential_document_status)
               VALUES (?, ?, 'pending')""",
            (uid, doc),
        )


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
