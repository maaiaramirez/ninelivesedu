"""
Base de datos: SQLite local por defecto, o Turso (libSQL remoto) en
producción si están seteadas TURSO_DATABASE_URL y TURSO_AUTH_TOKEN.

Por qué: en el plan free de Render el sistema de archivos no persiste —
se reinicia con cada redeploy y cada vez que el servicio "duerme" por
inactividad (15 min sin tráfico), así que un archivo SQLite local pierde
todos los datos constantemente. Turso resuelve esto sirviendo la misma
base por HTTP desde un servicio externo que sí persiste, sin cambiar el
SQL de ninguna consulta del proyecto (libSQL es un fork de SQLite,
compatible a nivel de sintaxis).

Sin esas dos variables de entorno, se sigue usando el archivo local
de siempre — así el desarrollo y las pruebas no dependen de tener una
cuenta de Turso.
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

TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

PIN_HASH_SECRET = os.environ.get("PIN_HASH_SECRET", "nine-lives-edu-pin-secret")


def hash_pin(pin: str) -> str:
    return hashlib.sha256(f"{PIN_HASH_SECRET}:{pin}".encode()).hexdigest()


@contextmanager
def get_conn():
    if TURSO_DATABASE_URL:
        import libsql  # se importa acá, no arriba, para no exigir el paquete cuando no se usa Turso
        conn = libsql.connect(database=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN or "")
    else:
        conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def exec_all(sql, params=()):
    with get_conn() as conn:
        cursor = conn.execute(sql, params)
        columnas = [col[0] for col in cursor.description] if cursor.description else []
        filas = cursor.fetchall()
        return [dict(zip(columnas, fila)) for fila in filas]


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
    created_at TEXT NOT NULL,
    FOREIGN KEY (tutor_id) REFERENCES tutores(id),
    FOREIGN KEY (sesion_id) REFERENCES tutoria_sesiones(id),
    FOREIGN KEY (student_user_id) REFERENCES users(id)
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
    with get_conn() as conn:
        conn.executescript(SCHEMA)

    _migrar_columnas_faltantes()
    seed_teacher_demo()
    seed_pending_examples()
    seed_moderator()
    seed_if_empty()


def _migrar_columnas_faltantes():
    """SQLite no agrega columnas nuevas a una tabla que ya existe solo con
    CREATE TABLE IF NOT EXISTS — si la base viene de antes de que existieran
    estas columnas, hay que sumarlas a mano. ALTER TABLE ADD COLUMN falla si
    la columna ya está, así que lo ignoramos: SQLite lanza
    sqlite3.OperationalError para esto, pero libSQL/Turso lanza ValueError
    con el mismo motivo — hay que atrapar los dos."""
    columnas_nuevas = {
        "teacher_profiles": [
            ("ai_is_valid", "INTEGER"),
            ("ai_confidence", "REAL"),
            ("ai_reason", "TEXT"),
            ("ai_reviewed_at", "TEXT"),
        ],
    }
    with get_conn() as conn:
        for tabla, columnas in columnas_nuevas.items():
            for nombre, tipo in columnas:
                try:
                    conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}")
                except (sqlite3.OperationalError, ValueError):
                    pass  # ya existía


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
