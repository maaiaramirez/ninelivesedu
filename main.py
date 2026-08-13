"""
Nine Lives Edu — Backend unificado en FastAPI.
Reemplaza al Servidor Central (Node/Express) y al Motor de IA separado:
un solo servicio, un solo deploy en Render, sin proxies entre servicios.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.database import init_database
from app.routers import apuntes, tutores, foros, asistencia, chat, auth, admin
# from app.routers import moderacion  # activar cuando se instalen sus dependencias (ver requirements.txt)

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "codigos pagina"
UPLOADS_DIR = BASE_DIR / "storage" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Nine Lives Edu API")

# ─────────────────────────────────────────────
# Rutas de la API (equivalentes a src/routes/*.js)
# ─────────────────────────────────────────────
app.include_router(apuntes.router)
app.include_router(tutores.router)
app.include_router(foros.router)
app.include_router(asistencia.router)
app.include_router(chat.router)  # expone POST /api/chat
app.include_router(auth.router)   # login/logout/sesión de administradores
app.include_router(admin.router)  # panel de administración (oculto, sin link en el nav)
# app.include_router(moderacion.router)  # activar junto con el import de arriba


@app.get("/health")
def health():
    return {"status": "ok"}


# Archivos subidos por los usuarios (apuntes)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Frontend estático — se sirve DESPUÉS de las rutas /api para que nunca las tape
if PUBLIC_DIR.exists():
    app.mount("/static-assets", StaticFiles(directory=str(PUBLIC_DIR)), name="assets")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    # Si es un pedido a /api/... que no matcheó ninguna ruta: 404 en JSON
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=404, content={"message": "Recurso no encontrado"})

    # Si es un GET normal de navegador, servimos el index.html (SPA fallback)
    if request.method == "GET" and PUBLIC_DIR.exists():
        index_file = PUBLIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

    return JSONResponse(status_code=404, content={"message": "No encontrado"})


@app.on_event("startup")
def on_startup():
    init_database()


# Servir archivos estáticos sueltos del frontend (css, js, imágenes) en la raíz,
# para no romper rutas relativas tipo /components.js, /styles.css, etc.
if PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="frontend")
