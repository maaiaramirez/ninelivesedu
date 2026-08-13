import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..database import exec_all, exec_one, run
from ..auth import require_moderator, hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_moderator)])


# ─────────────────────────────────────────
# CERTIFICACIONES DE TUTORES / PROFESORES
# ─────────────────────────────────────────
@router.get("/certificaciones/pendientes")
def certificaciones_pendientes():
    rows = exec_all(
        """SELECT u.id AS user_id, u.email, u.full_name, u.role, u.created_at,
                  tp.credential_document_path, tp.credential_document_status
           FROM users u
           JOIN teacher_profiles tp ON tp.user_id = u.id
           WHERE tp.credential_document_status = 'pending'
           ORDER BY u.created_at ASC"""
    )
    return {"total": len(rows), "pendientes": rows}


@router.post("/certificaciones/{user_id}/aprobar")
def aprobar_certificacion(user_id: str):
    user = exec_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    now = datetime.now(timezone.utc).isoformat()
    run("UPDATE teacher_profiles SET credential_document_status = 'approved' WHERE user_id = ?", (user_id,))
    run("UPDATE users SET validation_status = 'approved', updated_at = ? WHERE id = ?", (now, user_id))
    return {"success": True, "message": f"{user['full_name']} fue aprobado/a."}


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
