import re
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from ..database import exec_all, exec_one, run

router = APIRouter(prefix="/api/apuntes", tags=["apuntes"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "storage" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIMES = {
    "application/pdf", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "image/png", "image/jpeg", "image/webp",
}

ICONS = {
    "matematicas": "fas fa-calculator", "fisica": "fas fa-atom", "quimica": "fas fa-flask",
    "biologia": "fas fa-microscope", "historia": "fas fa-landmark", "literatura": "fas fa-book",
    "ingles": "fas fa-language", "filosofia": "fas fa-brain",
}


def clean_filename(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9._-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name


@router.get("")
def listar_apuntes():
    return exec_all("SELECT * FROM apuntes ORDER BY date(fecha) DESC")


@router.get("/{apunte_id}")
def obtener_apunte(apunte_id: str):
    apunte = exec_one("SELECT * FROM apuntes WHERE id = ?", (apunte_id,))
    if not apunte:
        raise HTTPException(404, "Apunte no encontrado")
    return apunte


@router.post("", status_code=201)
async def crear_apunte(
    titulo: str = Form(...),
    materia: str = Form(...),
    nivel: str = Form(...),
    autor: str = Form(None),
    descripcion: str = Form(None),
    tipo: str = Form(None),
    archivo: UploadFile = File(None),
):
    archivo_path = None
    if archivo is not None:
        if archivo.content_type not in ALLOWED_MIMES:
            raise HTTPException(400, "Tipo de archivo no permitido.")
        import time
        filename = f"{int(time.time() * 1000)}-{clean_filename(archivo.filename)}"
        dest = UPLOADS_DIR / filename
        with open(dest, "wb") as f:
            f.write(await archivo.read())
        archivo_path = f"/uploads/{filename}"

    apunte_id = f"apunte-{uuid.uuid4()}"
    fecha = date.today().isoformat()
    ext = (archivo.filename.split(".")[-1].lower() if archivo and "." in archivo.filename else "pdf")

    nuevo = {
        "id": apunte_id, "titulo": titulo, "materia": materia, "nivel": nivel,
        "autor": autor or "Autor anónimo", "fecha": fecha,
        "descripcion": descripcion or "Apunte recién agregado por la comunidad.",
        "tipo": tipo or ext, "rating": 4.5, "descargas": 0,
        "icono": ICONS.get(materia, "fas fa-book-open"),
        "archivo": archivo_path or f"{titulo.lower().replace(' ', '_')}.pdf",
    }
    run(
        """INSERT INTO apuntes (id, titulo, materia, nivel, autor, fecha, descripcion, tipo, rating, descargas, icono, archivo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        tuple(nuevo.values()),
    )
    return nuevo


@router.get("/{apunte_id}/descargar")
def descargar_apunte(apunte_id: str):
    apunte = exec_one("SELECT * FROM apuntes WHERE id = ?", (apunte_id,))
    if not apunte:
        raise HTTPException(404, "Apunte no encontrado")
    if not apunte["archivo"] or not apunte["archivo"].startswith("/uploads/"):
        raise HTTPException(400, "Este apunte no tiene archivo físico asociado.")
    absolute_path = UPLOADS_DIR / Path(apunte["archivo"]).name
    if not absolute_path.exists():
        raise HTTPException(404, "Archivo no encontrado en almacenamiento.")
    return FileResponse(absolute_path)


@router.post("/{apunte_id}/descargas")
def sumar_descarga(apunte_id: str):
    apunte = exec_one("SELECT * FROM apuntes WHERE id = ?", (apunte_id,))
    if not apunte:
        raise HTTPException(404, "Apunte no encontrado")
    run("UPDATE apuntes SET descargas = descargas + 1 WHERE id = ?", (apunte_id,))
    apunte["descargas"] += 1
    return apunte
