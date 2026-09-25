import uuid
from datetime import datetime, timezone

from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..database import exec_all, exec_one, run, hash_pin
from ..auth import require_moderator, hash_password
from ..ai_verification import analizar_documento, tipo_soportado
import random

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_moderator)])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "storage" / "uploads"


# ─────────────────────────────────────────
# CERTIFICACIONES DE TUTORES / PROFESORES
# ─────────────────────────────────────────
@router.get("/certificaciones/pendientes")
def certificaciones_pendientes():
    rows = exec_all(
        """SELECT u.id AS user_id, u.email, u.full_name, u.role, u.created_at,
                  tp.credential_document_path, tp.credential_document_status, tp.materia_interes,
                  tp.ai_is_valid, tp.ai_confidence, tp.ai_reason, tp.ai_reviewed_at
           FROM users u
           JOIN teacher_profiles tp ON tp.user_id = u.id
           WHERE tp.credential_document_status = 'pending'
           ORDER BY u.created_at ASC"""
    )
    return {"total": len(rows), "pendientes": rows}


@router.post("/certificaciones/{user_id}/analizar-ia")
def analizar_certificacion_con_ia(user_id: str):
    """Le pide a un modelo con visión (vía OpenRouter) que mire el documento
    y opine si parece un título/certificado válido. Guarda el resultado en
    teacher_profiles para no tener que volver a pagar la llamada cada vez
    que el moderador reabre la lista. NO aprueba ni rechaza nada solo —
    el moderador sigue decidiendo con los botones de siempre."""
    perfil = exec_one(
        "SELECT credential_document_path FROM teacher_profiles WHERE user_id = ?",
        (user_id,),
    )
    if not perfil or not perfil["credential_document_path"]:
        raise HTTPException(404, "Este usuario no tiene un documento de certificación cargado.")

    filename = Path(perfil["credential_document_path"]).name
    absolute_path = UPLOADS_DIR / filename

    if not tipo_soportado(filename):
        ext = Path(filename).suffix.lstrip(".")
        raise HTTPException(400, f"Los archivos .{ext} todavía no se pueden analizar con IA — revisalo a mano.")

    solicitante = exec_one("SELECT materia_interes FROM teacher_profiles WHERE user_id = ?", (user_id,))
    materia = solicitante["materia_interes"] if solicitante else ""

    resultado = analizar_documento(absolute_path, materia)

    now = datetime.now(timezone.utc).isoformat()
    run(
        """UPDATE teacher_profiles
           SET ai_is_valid = ?, ai_confidence = ?, ai_reason = ?, ai_reviewed_at = ?
           WHERE user_id = ?""",
        (resultado["is_valid"], resultado["confidence"], resultado["reason"], now, user_id),
    )

    return resultado


@router.get("/certificaciones/{user_id}/documento")
def descargar_documento_certificacion(user_id: str):
    """Sirve el título/documento subido por el tutor al postularse.
    Antes esto se servía como archivo estático público en /uploads — cualquiera
    que adivinara o encontrara la URL podía verlo. Ahora pasa por acá, que
    hereda el require_moderator del router: solo un moderador logueado
    puede pedirlo."""
    perfil = exec_one(
        "SELECT credential_document_path FROM teacher_profiles WHERE user_id = ?",
        (user_id,),
    )
    if not perfil or not perfil["credential_document_path"]:
        raise HTTPException(404, "Este usuario no tiene un documento de certificación cargado.")

    filename = Path(perfil["credential_document_path"]).name  # descarta cualquier ../ por las dudas
    absolute_path = UPLOADS_DIR / filename
    if not absolute_path.exists():
        raise HTTPException(404, "Archivo no encontrado en almacenamiento.")
    return FileResponse(absolute_path)


def _generar_pin_docente_unico() -> str:
    for _ in range(10):
        candidato = f"{random.randint(0, 999999):06d}"
        choque = exec_one(
            "SELECT user_id FROM teacher_profiles WHERE unique_pin_ciphertext = ?",
            (hash_pin(candidato),),
        )
        if not choque:
            return candidato
    raise HTTPException(500, "No se pudo generar un PIN único para el profesor.")


@router.post("/certificaciones/{user_id}/aprobar")
def aprobar_certificacion(user_id: str):
    user = exec_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    now = datetime.now(timezone.utc).isoformat()
    run("UPDATE teacher_profiles SET credential_document_status = 'approved' WHERE user_id = ?", (user_id,))
    run("UPDATE users SET validation_status = 'approved', updated_at = ? WHERE id = ?", (now, user_id))

    # Le creamos su ficha real en el marketplace, vinculada por user_id (no por
    # nombre — así "aprobar_reserva" puede verificar dueño sin ambigüedad).
    ya_tiene_ficha = exec_one("SELECT id FROM tutores WHERE user_id = ?", (user_id,))
    if not ya_tiene_ficha:
        perfil = exec_one("SELECT materia_interes FROM teacher_profiles WHERE user_id = ?", (user_id,))
        tutor_id = f"tutor-{uuid.uuid4()}"
        run(
            """INSERT INTO tutores (id, user_id, nombre, materia, nivel, precio, rating, cupo_maximo)
               VALUES (?, ?, ?, ?, 'universidad', 0, 0, 4)""",
            (tutor_id, user_id, user["full_name"], (perfil["materia_interes"] if perfil else "general") or "general"),
        )

    # PIN personal para el terminal físico (check-in-tutor / check-out-tutor
    # en asistencia.py). Se genera UNA sola vez acá, en la aprobación — de ahí
    # en más solo se guarda su hash (unique_pin_ciphertext), así que este es
    # el único momento en que el backend conoce el PIN en texto plano. Si el
    # profesor ya tenía uno asignado (por ej. una re-aprobación), no se pisa
    # — para eso está /regenerar-pin más abajo, explícito.
    ya_tiene_pin = exec_one(
        "SELECT unique_pin_ciphertext FROM teacher_profiles WHERE user_id = ?", (user_id,)
    )
    pin_generado = None
    if ya_tiene_pin and not ya_tiene_pin["unique_pin_ciphertext"]:
        pin_generado = _generar_pin_docente_unico()
        run(
            "UPDATE teacher_profiles SET unique_pin_ciphertext = ?, pin_issued_at = ? WHERE user_id = ?",
            (hash_pin(pin_generado), now, user_id),
        )

    mensaje = f"{user['full_name']} fue aprobado/a y ya tiene su ficha de tutor activa."
    if pin_generado:
        mensaje += f" Su PIN para el terminal físico es {pin_generado} — comunicáselo, no se puede volver a mostrar."

    return {"success": True, "message": mensaje, "pinDocente": pin_generado}


@router.post("/usuarios/{user_id}/regenerar-pin-docente")
def regenerar_pin_docente(user_id: str):
    """Para cuando el PIN generado en la aprobación se perdió, se anotó mal,
    o hay que rotarlo por seguridad. Pisa el que tenía (si tenía) con uno
    nuevo — el viejo deja de servir para el terminal apenas se guarda este."""
    perfil = exec_one("SELECT * FROM teacher_profiles WHERE user_id = ?", (user_id,))
    if not perfil:
        raise HTTPException(404, "Este usuario no tiene un perfil de profesor.")

    pin_generado = _generar_pin_docente_unico()
    now = datetime.now(timezone.utc).isoformat()
    run(
        "UPDATE teacher_profiles SET unique_pin_ciphertext = ?, pin_issued_at = ? WHERE user_id = ?",
        (hash_pin(pin_generado), now, user_id),
    )
    return {
        "success": True,
        "message": f"Nuevo PIN generado: {pin_generado} — el anterior (si tenía) dejó de funcionar.",
        "pinDocente": pin_generado,
    }


@router.post("/certificaciones/{user_id}/rechazar")
def rechazar_certificacion(user_id: str):
    user = exec_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    now = datetime.now(timezone.utc).isoformat()
    run("UPDATE teacher_profiles SET credential_document_status = 'rejected' WHERE user_id = ?", (user_id,))
    run("UPDATE users SET validation_status = 'rejected', updated_at = ? WHERE id = ?", (now, user_id))
    return {"success": True, "message": f"{user['full_name']} fue rechazado/a."}


# ─────────────────────────────────────────
# USUARIOS
# ─────────────────────────────────────────
@router.get("/usuarios")
def listar_usuarios(q: str = "", role: str = "", status: str = ""):
    """Lista usuarios. Filtros opcionales:
    - q: busca por nombre o email (coincidencia parcial)
    - role: student | tutor | teacher | admin
    - status: pending | approved | rejected
    """
    sql = """SELECT id, email, full_name, role, access_level, is_active,
                    validation_status, created_at
             FROM users WHERE 1=1"""
    params = []

    if q:
        sql += " AND (full_name LIKE ? OR email LIKE ?)"
        like = f"%{q.strip()}%"
        params += [like, like]
    if role:
        sql += " AND role = ?"
        params.append(role)
    if status:
        sql += " AND validation_status = ?"
        params.append(status)

    sql += " ORDER BY created_at DESC"
    rows = exec_all(sql, tuple(params))
    return {"total": len(rows), "usuarios": rows}


@router.post("/usuarios/{user_id}/activar")
def activar_usuario(user_id: str):
    user = exec_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    now = datetime.now(timezone.utc).isoformat()
    run("UPDATE users SET is_active = 1, updated_at = ? WHERE id = ?", (now, user_id))
    return {"success": True}


@router.post("/usuarios/{user_id}/desactivar")
def desactivar_usuario(user_id: str):
    user = exec_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    now = datetime.now(timezone.utc).isoformat()
    run("UPDATE users SET is_active = 0, updated_at = ? WHERE id = ?", (now, user_id))
    return {"success": True}


# ─────────────────────────────────────────
# MÉTRICAS GENERALES
# ─────────────────────────────────────────
@router.get("/metricas")
def metricas():
    def count(sql, params=()):
        row = exec_one(sql, params)
        return list(row.values())[0] if row else 0

    return {
        "apuntes": count("SELECT COUNT(*) AS n FROM apuntes"),
        "descargas_totales": count("SELECT COALESCE(SUM(descargas), 0) AS n FROM apuntes"),
        "tutores": count("SELECT COUNT(*) AS n FROM tutores"),
        "reservas": count("SELECT COUNT(*) AS n FROM reservas"),
        "posts_foro": count("SELECT COUNT(*) AS n FROM posts"),
        "respuestas_foro": count("SELECT COUNT(*) AS n FROM post_responses"),
        "usuarios_totales": count("SELECT COUNT(*) AS n FROM users"),
        "usuarios_activos": count("SELECT COUNT(*) AS n FROM users WHERE is_active = 1"),
        "certificaciones_pendientes": count(
            "SELECT COUNT(*) AS n FROM teacher_profiles WHERE credential_document_status = 'pending'"
        ),
        "profesores_en_linea_ahora": count(
            "SELECT COUNT(*) AS n FROM teacher_attendance WHERE is_available = 1"
        ),
    }


# ─────────────────────────────────────────
# CUENTAS DE ADMINISTRADOR (moderators)
# Solo un administrador ya logueado puede ver/crear/borrar otras cuentas.
# ─────────────────────────────────────────
class NuevoAdminIn(BaseModel):
    email: str
    password: str
    full_name: str


@router.get("/administradores")
def listar_administradores():
    rows = exec_all(
        "SELECT id, email, full_name, created_at FROM moderators ORDER BY created_at ASC"
    )
    return {"total": len(rows), "administradores": rows}


@router.post("/administradores")
def crear_administrador(body: NuevoAdminIn):
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Ingresá un email válido.")
    if len(body.password) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres.")
    if not body.full_name.strip():
        raise HTTPException(400, "Ingresá un nombre.")

    if exec_one("SELECT id FROM moderators WHERE email = ?", (email,)):
        raise HTTPException(409, "Ya existe una cuenta de administrador con ese email.")

    now = datetime.now(timezone.utc).isoformat()
    new_id = str(uuid.uuid4())
    run(
        """INSERT INTO moderators (id, email, password_hash, full_name, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (new_id, email, hash_password(body.password), body.full_name.strip(), now),
    )
    return {"success": True, "id": new_id, "email": email}


@router.delete("/administradores/{admin_id}")
def eliminar_administrador(admin_id: str, actor=Depends(require_moderator)):
    if admin_id == actor["id"]:
        raise HTTPException(400, "No podés eliminar tu propia cuenta mientras estás conectado con ella.")

    target = exec_one("SELECT id FROM moderators WHERE id = ?", (admin_id,))
    if not target:
        raise HTTPException(404, "Cuenta de administrador no encontrada.")

    total = exec_one("SELECT COUNT(*) AS n FROM moderators")["n"]
    if total <= 1:
        raise HTTPException(400, "No podés eliminar la única cuenta de administrador que existe.")

    run("DELETE FROM moderators WHERE id = ?", (admin_id,))
    return {"success": True}
