from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from ..database import exec_all, exec_one, run
from ..auth import require_moderator

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
def listar_usuarios():
    rows = exec_all(
        """SELECT id, email, full_name, role, access_level, is_active,
                  validation_status, created_at
           FROM users ORDER BY created_at DESC"""
    )
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
