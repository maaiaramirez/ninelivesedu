import uuid
from datetime import datetime, timezone

from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..database import exec_all, exec_one, run, hash_pin, registrar_auditoria
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
def aprobar_certificacion(user_id: str, actor=Depends(require_moderator)):
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

    registrar_auditoria(actor["id"], actor["full_name"], "aprobar_certificacion", "usuario", user_id,
                         f"Aprobó a {user['full_name']}" + (" (generó PIN nuevo)" if pin_generado else ""))
    return {"success": True, "message": mensaje, "pinDocente": pin_generado}


@router.post("/usuarios/{user_id}/regenerar-pin-docente")
def regenerar_pin_docente(user_id: str, actor=Depends(require_moderator)):
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
    user = exec_one("SELECT full_name FROM users WHERE id = ?", (user_id,))
    nombre = user["full_name"] if user else "(usuario no encontrado)"
    registrar_auditoria(actor["id"], actor["full_name"], "regenerar_pin", "usuario", user_id, f"Regeneró el PIN de {nombre}")
    return {
        "success": True,
        "message": f"Nuevo PIN de {nombre}: {pin_generado} — el anterior (si tenía) dejó de funcionar.",
        "pinDocente": pin_generado,
        "nombreDocente": nombre,
    }


class RechazarIn(BaseModel):
    motivo: str = ""


@router.post("/certificaciones/{user_id}/rechazar")
def rechazar_certificacion(user_id: str, body: RechazarIn = RechazarIn(), actor=Depends(require_moderator)):
    user = exec_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    now = datetime.now(timezone.utc).isoformat()
    motivo = body.motivo.strip() or None
    run("UPDATE teacher_profiles SET credential_document_status = 'rejected', rejection_reason = ? WHERE user_id = ?",
        (motivo, user_id))
    run("UPDATE users SET validation_status = 'rejected', updated_at = ? WHERE id = ?", (now, user_id))
    registrar_auditoria(actor["id"], actor["full_name"], "rechazar_certificacion", "usuario", user_id,
                         f"Rechazó a {user['full_name']}" + (f" — motivo: {motivo}" if motivo else " (sin motivo)"))
    return {"success": True, "message": f"{user['full_name']} fue rechazado/a."}


@router.post("/certificaciones/{user_id}/revocar")
def revocar_certificacion(user_id: str, body: RechazarIn = RechazarIn(), actor=Depends(require_moderator)):
    """Para dar de baja a un tutor que YA estaba aprobado (a diferencia de
    /rechazar, que es para postulaciones todavía pendientes). Le saca la
    aprobación y le anula el PIN: deja de poder operar como tutor y su PIN
    deja de abrir sesiones en el terminal físico de inmediato."""
    user = exec_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user or user["role"] != "teacher":
        raise HTTPException(404, "No se encontró un profesor con ese id.")
    if user["validation_status"] != "approved":
        raise HTTPException(400, "Este profesor no está aprobado actualmente.")

    now = datetime.now(timezone.utc).isoformat()
    motivo = body.motivo.strip() or None
    run("UPDATE users SET validation_status = 'rejected', updated_at = ? WHERE id = ?", (now, user_id))
    run("""UPDATE teacher_profiles
           SET credential_document_status = 'rejected', unique_pin_ciphertext = NULL,
               pin_issued_at = NULL, rejection_reason = ?
           WHERE user_id = ?""", (motivo, user_id))
    registrar_auditoria(actor["id"], actor["full_name"], "revocar_aprobacion", "usuario", user_id,
                         f"Revocó la aprobación de {user['full_name']}" + (f" — motivo: {motivo}" if motivo else ""))
    return {"success": True, "message": f"Se revocó la aprobación de {user['full_name']}. Su PIN ya no funciona."}


# ─────────────────────────────────────────
# USUARIOS
# ─────────────────────────────────────────
@router.get("/usuarios")
def listar_usuarios(q: str = "", role: str = "", status: str = "", page: int = 1, page_size: int = 20):
    """Lista usuarios. Filtros opcionales:
    - q: busca por nombre o email (coincidencia parcial)
    - role: student | tutor | teacher | admin
    - status: pending | approved | rejected
    - page / page_size: paginación (page arranca en 1)
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    sql = """SELECT id, email, full_name, role, access_level, is_active,
                    validation_status, created_at
             FROM users WHERE 1=1"""
    sql_count = "SELECT COUNT(*) AS n FROM users WHERE 1=1"
    params = []

    if q:
        sql += " AND (full_name LIKE ? OR email LIKE ?)"
        sql_count += " AND (full_name LIKE ? OR email LIKE ?)"
        like = f"%{q.strip()}%"
        params += [like, like]
    if role:
        sql += " AND role = ?"
        sql_count += " AND role = ?"
        params.append(role)
    if status:
        sql += " AND validation_status = ?"
        sql_count += " AND validation_status = ?"
        params.append(status)

    total = exec_one(sql_count, tuple(params))["n"]
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    rows = exec_all(sql, tuple(params) + (page_size, (page - 1) * page_size))
    return {"total": total, "page": page, "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size, "usuarios": rows}


@router.post("/usuarios/{user_id}/activar")
def activar_usuario(user_id: str, actor=Depends(require_moderator)):
    user = exec_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    now = datetime.now(timezone.utc).isoformat()
    run("UPDATE users SET is_active = 1, updated_at = ? WHERE id = ?", (now, user_id))
    registrar_auditoria(actor["id"], actor["full_name"], "activar_usuario", "usuario", user_id, user["full_name"])
    return {"success": True}


@router.post("/usuarios/{user_id}/desactivar")
def desactivar_usuario(user_id: str, actor=Depends(require_moderator)):
    user = exec_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    now = datetime.now(timezone.utc).isoformat()
    run("UPDATE users SET is_active = 0, updated_at = ? WHERE id = ?", (now, user_id))
    registrar_auditoria(actor["id"], actor["full_name"], "desactivar_usuario", "usuario", user_id, user["full_name"])
    return {"success": True}


# ─────────────────────────────────────────
# AUDITORÍA (solo lectura)
# ─────────────────────────────────────────
@router.get("/auditoria")
def listar_auditoria(page: int = 1, page_size: int = 30):
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    total = exec_one("SELECT COUNT(*) AS n FROM auditoria")["n"]
    rows = exec_all(
        "SELECT * FROM auditoria ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (page_size, (page - 1) * page_size),
    )
    return {"total": total, "page": page, "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size, "registros": rows}


# ─────────────────────────────────────────
# MÉTRICAS DE ASISTENCIA Y ENCUESTAS
# ─────────────────────────────────────────
@router.get("/metricas/encuestas")
def metricas_encuestas():
    """Promedio de puntaje y cantidad de respuestas por tutor, más la
    asistencia (check-ins de alumnos) agrupada por sesión reciente."""
    por_tutor = exec_all(
        """SELECT t.id AS tutor_id, t.nombre AS tutor_nombre,
                  COUNT(e.id) AS respuestas,
                  ROUND(AVG(e.puntaje), 2) AS promedio
           FROM tutores t
           LEFT JOIN encuestas_satisfaccion e ON e.tutor_id = t.id
           GROUP BY t.id
           HAVING COUNT(e.id) > 0
           ORDER BY promedio DESC"""
    )
    asistencia_por_sesion = exec_all(
        """SELECT s.id AS sesion_id, s.fecha, t.nombre AS tutor_nombre,
                  (SELECT COUNT(*) FROM asistencia_alumnos a WHERE a.sesion_id = s.id) AS asistieron,
                  af.estado AS estado_fisico
           FROM tutoria_sesiones s
           JOIN tutores t ON t.id = s.tutor_id
           LEFT JOIN asistencia_fisica af ON af.sesion_id = s.id
           WHERE af.estado IS NOT NULL
           ORDER BY s.fecha DESC LIMIT 50"""
    )
    comentarios_recientes = exec_all(
        """SELECT e.puntaje, e.comentario, e.created_at, t.nombre AS tutor_nombre
           FROM encuestas_satisfaccion e
           JOIN tutores t ON t.id = e.tutor_id
           WHERE e.comentario IS NOT NULL AND e.comentario != ''
           ORDER BY e.created_at DESC LIMIT 20"""
    )
    return {
        "porTutor": por_tutor,
        "asistenciaPorSesion": asistencia_por_sesion,
        "comentariosRecientes": comentarios_recientes,
    }


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
    rol: str = "moderador"


def _requerir_rol_admin(actor):
    """Solo las cuentas con rol 'admin' pueden gestionar otras cuentas de
    moderador. Las cuentas creadas antes de este cambio (vía la migración
    de columnas) ya quedan como 'admin' por el valor por defecto, así que
    nadie se queda afuera de golpe."""
    if actor.get("rol") != "admin":
        raise HTTPException(403, "Solo una cuenta con rol de administrador puede gestionar otras cuentas de moderador.")


@router.get("/administradores")
def listar_administradores():
    rows = exec_all(
        "SELECT id, email, full_name, rol, created_at FROM moderators ORDER BY created_at ASC"
    )
    return {"total": len(rows), "administradores": rows}


@router.post("/administradores")
def crear_administrador(body: NuevoAdminIn, actor=Depends(require_moderator)):
    _requerir_rol_admin(actor)
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Ingresá un email válido.")
    if len(body.password) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres.")
    if not body.full_name.strip():
        raise HTTPException(400, "Ingresá un nombre.")
    rol = body.rol if body.rol in ("admin", "moderador") else "moderador"

    if exec_one("SELECT id FROM moderators WHERE email = ?", (email,)):
        raise HTTPException(409, "Ya existe una cuenta de administrador con ese email.")

    now = datetime.now(timezone.utc).isoformat()
    new_id = str(uuid.uuid4())
    run(
        """INSERT INTO moderators (id, email, password_hash, full_name, created_at, rol)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (new_id, email, hash_password(body.password), body.full_name.strip(), now, rol),
    )
    registrar_auditoria(actor["id"], actor["full_name"], "crear_administrador", "moderador", new_id,
                         f"Creó la cuenta {email} (rol: {rol})")
    return {"success": True, "id": new_id, "email": email, "rol": rol}


@router.delete("/administradores/{admin_id}")
def eliminar_administrador(admin_id: str, actor=Depends(require_moderator)):
    _requerir_rol_admin(actor)
    if admin_id == actor["id"]:
        raise HTTPException(400, "No podés eliminar tu propia cuenta mientras estás conectado con ella.")

    target = exec_one("SELECT id, email FROM moderators WHERE id = ?", (admin_id,))
    if not target:
        raise HTTPException(404, "Cuenta de administrador no encontrada.")

    total = exec_one("SELECT COUNT(*) AS n FROM moderators")["n"]
    if total <= 1:
        raise HTTPException(400, "No podés eliminar la única cuenta de administrador que existe.")

    run("DELETE FROM moderators WHERE id = ?", (admin_id,))
    registrar_auditoria(actor["id"], actor["full_name"], "eliminar_administrador", "moderador", admin_id, target["email"])
    return {"success": True}
