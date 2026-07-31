# Nine Lives Edu

Plataforma educativa colaborativa: apuntes, tutores, foros de estudio, asistencia de profesores en tiempo real, y un chatbot de estudio (Wawa AI).

## Arquitectura

Un solo servicio backend en **FastAPI (Python)**, que sirve tanto la API como el frontend estático. Sin Node.js, sin microservicios separados, sin proxies entre servicios.

```
main.py                    → arranca la app, sirve el frontend + monta las rutas de la API
app/
  database.py                → SQLite (stdlib sqlite3), schema y datos semilla
  data_seed.py                 → datos de ejemplo (apuntes, tutores, posts)
  document_processor.py        → extracción de texto de documentos (para verificación de tutores)
  verification.py              → flujo de verificación de certificaciones (LangGraph) — pendiente de conectar
  routers/
    apuntes.py                   → listar, crear, descargar apuntes
    tutores.py                   → listar tutores, reservas, intercambios
    foros.py                     → posts, votos, respuestas
    asistencia.py                → asistencia de profesores en vivo (Server-Sent Events) + check-in/out ESP32
    chat.py                      → chatbot Wawa AI (OpenRouter)
    moderacion.py                → verificación de certificaciones (desactivado por defecto, ver abajo)
codigos pagina/             → frontend estático (HTML/CSS/JS)
storage/
  ninelivesedu.sqlite         → base de datos (se crea sola al arrancar)
  uploads/                     → archivos subidos por los usuarios
```

## Cómo correrlo en local

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Abrí `http://127.0.0.1:8000` en el navegador.

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `OPENROUTER_API_KEY` | Sí | Clave de [openrouter.ai](https://openrouter.ai) (gratis, sin tarjeta) para el chatbot |
| `OPENROUTER_MODEL` | No | Modelo a usar. Por defecto `openrouter/free` (auto-router entre modelos gratis) |
| `ESP32_API_KEY` | No | Clave para autenticar los dispositivos ESP32 de check-in de asistencia |
| `PIN_HASH_SECRET` | No | Secreto para hashear los PIN de profesores |

## Despliegue en Render

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Root Directory**: vacío (raíz del repo)
- La versión de Python queda fijada por `runtime.txt`; si Render la ignora, usar la variable de entorno `PYTHON_VERSION` como alternativa.

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio |
| GET/POST | `/api/apuntes` | Listar / crear apuntes |
| POST | `/api/apuntes/{id}/descargas` | Sumar una descarga |
| GET | `/api/tutores` | Listar tutores |
| POST | `/api/tutores/{id}/reservas` | Reservar sesión con un tutor |
| GET/POST | `/api/foros` | Listar / crear posts del foro |
| POST | `/api/foros/{id}/vote` | Votar un post |
| GET | `/api/asistencia/profesores-disponibles` | Profesores conectados ahora |
| GET | `/api/asistencia/stream` | Stream en tiempo real (SSE) |
| POST | `/api/chat` | Chatbot Wawa AI |

## Pendiente / roadmap

- **Panel de moderadores**: no existe todavía interfaz ni lógica de aprobación — solo el endpoint de verificación de certificaciones (`app/routers/moderacion.py`), desactivado por defecto porque sus dependencias (`langgraph`, `unstructured`) son pesadas. Para activarlo: descomentar el import en `main.py` y las 3 líneas correspondientes en `requirements.txt`.
- El análisis de certificaciones en `app/verification.py` es un **stub** (heurística simple, no usa IA real todavía).
- Unificar/limpiar los datos semilla si se pasa a una base de datos persistente distinta de SQLite.
