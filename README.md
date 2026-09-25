# Nine Lives Edu

Plataforma educativa colaborativa: apuntes, tutores, foros de estudio, asistencia dual profesor+alumno con terminal físico (ESP32), panel de moderadores, y un chatbot de estudio (Wawa AI).

## Arquitectura

Un solo servicio backend en **FastAPI (Python)**, que sirve tanto la API como el frontend estático. Sin Node.js, sin microservicios separados, sin proxies entre servicios.

```
main.py                    → arranca la app, sirve el frontend + monta las rutas de la API
app/
  database.py                → SQLite (stdlib sqlite3), schema y datos semilla
  data_seed.py                 → datos de ejemplo (apuntes, tutores, posts)
  document_processor.py        → extracción de texto de documentos (para verificación de tutores)
  verification.py              → flujo de verificación de certificaciones (LangGraph) — pendiente de conectar
  user_auth.py                  → sesiones de alumnos/tutores (cookie nle_user_session)
  auth.py                       → sesiones de moderadores (cookie separada, ver moderators/moderator_sessions)
  routers/
    apuntes.py                   → listar, crear, descargar apuntes
    tutores.py                   → tutores, reservas, sesiones de tutoría, postulación como tutor
    foros.py                     → posts, votos, respuestas
    asistencia.py                → asistencia FÍSICA dual (tutor+alumno) vía terminal ESP32 + SSE, ver abajo
    admin.py                     → panel de moderadores: aprobar/rechazar certificaciones, gestión de usuarios, PIN de docentes
    auth.py                      → login/logout/me/cambiar-password de moderadores
    usuarios.py                   → registro/login de alumnos y tutores + rutas protegidas por rol
    chat.py                      → chatbot Wawa AI (OpenRouter)
    moderacion.py                → verificación de certificaciones con IA (desactivado por defecto, ver abajo)
codigos pagina/             → frontend estático (HTML/CSS/JS) — fuente de verdad
  atlas.js                       → header, login/registro, modal "Unirse como tutor"
  mi-cuenta.html                 → dashboard de alumno y de tutor (según rol)
  moderadores.html                → panel de moderadores (certificaciones, usuarios, PIN)
  asistencia.html                  → "Jardín de Profesores" (disponibilidad en vivo, SSE)
www/                         → copia sincronizada de "codigos pagina/" para la app móvil — correr
                                scripts/sync-www.sh después de tocar algo en "codigos pagina/"
storage/
  ninelivesedu.sqlite         → base de datos (se crea sola al arrancar — ver aviso de Render abajo)
  uploads/                     → archivos subidos por los usuarios
```

El firmware del terminal físico (`terminal_aula_esp32.ino`, ESP32 + teclado matricial + LCD I2C) no forma parte del build de Python — no lo trae este repo todavía. Se recomienda guardarlo en una carpeta `hardware/` en la raíz para tenerlo versionado junto con el resto.

## Cómo correrlo en local

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Abrí `http://127.0.0.1:8000` en el navegador. Si vas a probar el terminal ESP32 contra tu backend local, acordate de que el `.ino` usa HTTPS (`WiFiClientSecure`) — local sin certificado no le va a andar; probalo contra el deploy de Render.

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `OPENROUTER_API_KEY` | Sí | Clave de [openrouter.ai](https://openrouter.ai) (gratis, sin tarjeta) para el chatbot |
| `OPENROUTER_MODEL` | No | Modelo a usar. Por defecto `openrouter/free` (auto-router entre modelos gratis) |
| `ESP32_API_KEY` | No | Clave que el terminal manda en el header `x-esp32-key` para autenticarse contra `/api/asistencia/check-in-tutor`, `check-in-alumno` y `check-out-tutor`. Por defecto `esp32-local-key` — tiene que coincidir EXACTO con `ESP32_API_KEY` en el `.ino` |
| `PIN_HASH_SECRET` | No | Secreto para hashear los PIN (de profesores y de alumnos) antes de guardarlos |
| `MODERATOR_EMAIL` / `MODERATOR_PASSWORD` | No | Credenciales del moderador inicial, creado solo si no existe ninguno. Por defecto `admin@ninelivesedu.org` / `changeme123` — **cambiarlas en producción** |
| `COOKIE_SECURE` | No | `true` por defecto (cookies `Secure`, para HTTPS real en Render). Poner `false` solo para probar en `http://127.0.0.1` local |
| `TURSO_DATABASE_URL` | No | URL de la base Turso (`libsql://...`). Si está configurada, la app usa Turso en vez del archivo SQLite local — ver "Persistencia con Turso" abajo |
| `TURSO_AUTH_TOKEN` | Solo si se usa Turso | Token de autenticación de la base Turso (`turso db tokens create <nombre-db>`) |

## Despliegue en Render

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Root Directory**: vacío (raíz del repo)
- La versión de Python queda fijada por `runtime.txt`; si Render la ignora, usar la variable de entorno `PYTHON_VERSION` como alternativa.

### Persistencia con Turso (recomendado en producción)

Configurando `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN` como variables de
entorno en Render, la app usa automáticamente una base [Turso](https://turso.tech)
(libSQL, compatible con SQLite) en vez del archivo local — sin cambiar
nada en el resto del código: todos los routers siguen llamando
`exec_one`/`exec_all`/`run` exactamente igual. Esto resuelve por completo
el problema del disco efímero descripto abajo, porque la base ya no vive
en el disco del contenedor.

Pasos para activarlo:
1. Crear la base: `turso db create nine-lives-edu` (o usar una ya creada).
2. Obtener la URL: `turso db show nine-lives-edu --url` (empieza con `libsql://`).
3. Generar un token: `turso db tokens create nine-lives-edu`.
4. Cargar ambos valores como variables de entorno en Render (o en `.env`
   local). Al arrancar, `init_database()` crea el esquema solo si no
   existe (igual que en modo local).

Sin `TURSO_DATABASE_URL` configurada, la app sigue funcionando en modo
SQLite local como siempre — es un agregado, no un reemplazo obligatorio.

### ⚠️ El disco es efímero en el plan gratis (si NO se usa Turso)

`storage/ninelivesedu.sqlite` vive en el disco del propio contenedor. En el plan **gratis** de Render, ese disco **se resetea en cada deploy y cada vez que el servicio "duerme" por inactividad** (~15 min sin tráfico) y vuelve a arrancar. Eso borra TODOS los usuarios, tutores, reservas y PIN generados — no es un bug de la app, es cómo funciona el plan gratis.

Implicancias prácticas:
- Después de cada deploy, hay que rehacer el setup de prueba (postularse como tutor → aprobar → reservar → aprobar reserva) **de una sola sentada**, sin dejar pasar 15+ minutos entre pasos.
- Para que los datos sobrevivan entre deploys de verdad (uso real, no solo demo), hace falta un [Disco persistente de Render](https://render.com/docs/disks) (no disponible en el plan gratis) o migrar a una base de datos alojada aparte (ej. Render Postgres).

## Asistencia física dual (terminal ESP32)

Sistema de "Prueba de Presencia Física": el profesor abre la sesión con su PIN personal en el terminal, y recién ahí el terminal acepta los PIN de los alumnos — con control de aforo en tiempo real y disparo automático de encuesta al cerrar.

**Dos PIN, dos orígenes distintos:**
- **PIN del profesor** (`teacher_profiles.unique_pin_ciphertext`): se genera UNA vez, cuando un moderador aprueba su postulación en `moderadores.html` (o se regenera manualmente desde la pestaña "Usuarios" si se perdió). Es personal e identifica al profesor sin importar la sesión.
- **PIN del alumno** (`reservas.pin_alumno`): se genera cuando el TUTOR aprueba la reserva de ese alumno (`mi-cuenta.html`, vista de tutor). Es personal, globalmente único, y vincula al alumno con esa reserva puntual — el terminal lo usa para deducir sola a qué sesión pertenece, sin que el teclado tenga que mandar un `sesionId`.

**Máquina de estados por sesión** (tabla `asistencia_fisica`, independiente del `estado` de inscripción de `tutoria_sesiones`):

```
bloqueada --check-in-tutor--> activa --check-out-tutor--> completada
                                 |
                                 '-- check-in-alumno (repetible, con
                                     control de aforo transaccional)
```

- `POST /api/asistencia/check-in-tutor` — PIN del profesor. Si no manda `sesionId`, el backend busca sola la sesión de HOY de ese profesor (o la que ya esté activa, para el check-out). Devuelve 404 si el PIN no existe, 403 si la sesión es de otro profesor, 409 si ya estaba cerrada.
- `POST /api/asistencia/check-in-alumno` — PIN del alumno (global, no hace falta `sesionId`). 403 si el profesor todavía no abrió la sesión, 404 si el PIN no corresponde a una reserva confirmada, **409 si el cupo está lleno** (el ESP32 lo muestra como "Cupo Lleno" en el LCD).
- `POST /api/asistencia/check-out-tutor` — cierra la sesión y dispara, en un `BackgroundTask`, un evento SSE (`/api/asistencia/stream/alumno`, privado por usuario) a cada alumno que asistió, para que le aparezca el formulario de encuesta en su dashboard.
- `POST /api/asistencia/encuestas` — el alumno envía la encuesta (`puntaje` 1-5, comentario opcional), validada con Pydantic.

Los tres primeros requieren el header `x-esp32-key` (ver `ESP32_API_KEY` arriba) — es la autenticación del dispositivo, no de un usuario logueado.

El firmware (`terminal_aula_esp32.ino`) corre en un ESP32 con teclado matricial 4x3 (cableado internamente 3 filas × 4 columnas, no 4x3 — ver comentarios en el propio archivo) y LCD I2C 16x2. Estado local: mientras la sesión está *bloqueada* cualquier PIN + `#` se manda como check-in de profesor; una vez *activa*, cualquier PIN + `#` se manda como check-in de alumno, salvo que se arme "modo cierre" con `*` (buffer vacío) para mandar el próximo PIN como check-out del profesor.

Además existe un sistema más viejo y más simple — "¿está el profesor disponible ahora?" (`teacher_attendance`, `/api/asistencia/profesores-disponibles`, la vista "Jardín de Profesores" en `asistencia.html`) — que sigue funcionando en paralelo y se actualiza también con estos mismos check-in/check-out, pero es independiente del control de aforo y las encuestas.

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio |
| GET/POST | `/api/apuntes` | Listar / crear apuntes |
| POST | `/api/apuntes/{id}/descargas` | Sumar una descarga |
| GET | `/api/tutores` | Listar tutores |
| POST | `/api/tutores/postularse` | Postularse como tutor (nombre, email, password, materia, título) |
| POST | `/api/tutores/{id}/reservas` | Reservar sesión con un tutor (crea la sesión si no existía) |
| POST | `/api/tutores/mis-sesiones` | El tutor crea una sesión propia, sin esperar una reserva primero |
| GET | `/api/tutores/mis-sesiones/tutor` | Sesiones del tutor logueado, con sus alumnos |
| GET | `/api/tutores/mis-reservas/alumno` | Reservas del alumno logueado, con su PIN personal |
| POST | `/api/tutores/reservas/{id}/aprobar` | El tutor aprueba una reserva → genera `pin_alumno` |
| GET/POST | `/api/foros` | Listar / crear posts del foro |
| POST | `/api/foros/{id}/vote` | Votar un post |
| GET | `/api/asistencia/profesores-disponibles` | Profesores conectados ahora ("Jardín de Profesores") |
| GET | `/api/asistencia/stream` | Stream en tiempo real del jardín (SSE) |
| POST | `/api/asistencia/check-in-tutor` \| `check-in-alumno` \| `check-out-tutor` | Terminal físico — ver sección de arriba |
| GET | `/api/asistencia/stream/alumno` | SSE privado del alumno (dispara el modal de encuesta) |
| POST | `/api/asistencia/encuestas` | Envío de la encuesta de satisfacción |
| POST | `/api/admin/certificaciones/{id}/aprobar` \| `rechazar` | Moderador aprueba/rechaza una postulación a tutor |
| POST | `/api/admin/usuarios/{id}/regenerar-pin-docente` | Moderador regenera el PIN de un profesor ya aprobado |
| POST | `/api/chat` | Chatbot Wawa AI |

## Pendiente / roadmap

- **Verificación con IA de certificaciones**: `app/routers/moderacion.py` y `app/verification.py` son un flujo aparte (LangGraph) que analiza el documento subido — sigue desactivado por defecto porque sus dependencias (`langgraph`, `unstructured`) son pesadas. Para activarlo: descomentar el import en `main.py` y las líneas correspondientes en `requirements.txt`. El panel de moderadores (`admin.py` + `moderadores.html`) NO depende de esto — ya funciona con aprobación manual.
- Persistencia real de la base de datos en producción (ver aviso de Render arriba) — hoy es SQLite en disco efímero, pensado para desarrollo/demo, no para uso continuo.
- Unificar/limpiar los datos semilla si se pasa a una base de datos persistente distinta de SQLite.

