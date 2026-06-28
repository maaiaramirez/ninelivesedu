# Nine Lives Edu (Node.js + Frontend estático)

Aplicación web que conecta estudiantes con tutores, apuntes y foros colaborativos. Partiendo de la carpeta `codigos pagina`, ahora se expone un backend en Node.js/Express que sirve la misma interfaz y ofrece endpoints para alimentar a futuras apps móviles o web.

## 🚀 Puesta en marcha

```bash
npm install
npm run dev        # recarga automática con nodemon
# o
npm start          # servidor en modo producción
```

### 📱 Empaquetar como App (Android con Capacitor)

Requisitos: Android Studio (SDK + build-tools), Java 17, Node.

```bash
# 1) Instala dependencias de Capacitor
npm install
npm install @capacitor/core @capacitor/cli

# 2) Copia el frontend a /www
npm run sync-www    # usa PowerShell/bash según tu SO

# 3) Inicializa/actualiza Capacitor
npx cap init ninelivesedu com.ninelivesedu.app --web-dir=www   # ya está en repo, puedes omitir si existe
npx cap add android                                      # ya creado si existe /android

# 4) Copia assets al proyecto Android
npm run cap:copy

# 5) Abre Android Studio para generar el APK
npm run cap:open
# En Android Studio: Build > Build Bundle(s)/APK(s) > Build APK(s)
```

El APK queda en `android/app/build/outputs/apk/debug/app-debug.apk` (o release si firmas).

Notas:
- `codigos pagina` es la fuente; `www` es la salida que consume Capacitor.
- El service worker ya cachea estáticos; offline funciona con los recursos incluidos. Las llamadas a `/api` requieren red/servidor.
```

El servidor se levanta en `http://localhost:3000` por defecto y publica tanto los archivos estáticos (`codigos pagina`) como las APIs REST bajo `/api`.

## 📁 Estructura relevante

```
.
├── codigos pagina/            # HTML, CSS, JS e imágenes originales
├── src/
│   ├── data/                  # Datos seed utilizados para poblar la BD
│   ├── db/                    # Inicialización y helpers de sql.js
│   ├── routes/                # Routers Express para cada dominio
│   └── server.js              # Configuración principal de Express
├── storage/ninelivesedu.sqlite   # Base de datos persistida (se crea al arrancar)
├── package.json
└── README.md                  # Este archivo
```

## 🧠 Endpoints principales

| Recurso      | Método | Ruta                                | Descripción                                   |
|--------------|--------|-------------------------------------|-----------------------------------------------|
| Apuntes      | GET    | `/api/apuntes`                      | Lista todos los apuntes                       |
|              | POST   | `/api/apuntes`                      | Crea un apunte (multipart + archivo real)     |
|              | GET    | `/api/apuntes/:id/descargar`        | Descarga el archivo físico subido             |
|              | POST   | `/api/apuntes/:id/descargas`        | Incrementa contador de descargas              |
| Tutores      | GET    | `/api/tutores`                      | Lista tutores y su disponibilidad             |
|              | POST   | `/api/tutores/:id/reservas`         | Solicita una reserva rápida                   |
|              | POST   | `/api/tutores/intercambios`         | Registra intercambios tutoría x tutoría       |
| Foros        | GET    | `/api/foros`                        | Lista posts de la comunidad                   |
|              | POST   | `/api/foros`                        | Crea un post                                  |
|              | POST   | `/api/foros/:id/vote`               | Incrementa votos                              |
|              | POST   | `/api/foros/:id/respuestas`         | Añade una respuesta                           |
| Asistencia   | GET    | `/api/asistencia/profesores-disponibles` | Lista profesores disponibles en tiempo real |
|              | GET    | `/api/asistencia/stream`            | Stream SSE para actualizar disponibilidad     |
|              | POST   | `/api/asistencia/esp32/check-in`    | Marca profesor disponible (ESP32 + PIN)       |
|              | POST   | `/api/asistencia/esp32/check-out`   | Marca profesor no disponible                   |

> Todos los endpoints leen y escriben en `storage/ninelivesedu.sqlite`, gestionada mediante `sql.js` (SQLite compilado a WebAssembly).

## 🗃️ Base de datos

- **Motor**: [`sql.js`](https://github.com/sql-js/sql.js) (sin dependencias nativas).
- **Archivo**: `storage/ninelivesedu.sqlite` (se crea automáticamente al iniciar el servidor).
- **Seed**: las colecciones definidas en `src/data` se insertan sólo la primera vez.
- **Reset**: basta con borrar `storage/ninelivesedu.sqlite` y reiniciar el servidor para regenerarla con los datos iniciales.

## 📱 Frontend (sin cambios visuales)

Los HTML y estilos originales se mantienen, pero la lógica en `apuntes.js`, `tutores.js` y `foros.js` ahora consume las APIs anteriores, lo que facilita reutilizar el backend desde una app móvil (Flutter, React Native, etc.).

## ✅ Próximos pasos sugeridos

- Migrar de `sql.js` a un motor gestionado (SQLite nativo, Postgres, MongoDB, etc.).
- Añadir autenticación y control de sesiones.
- Integrar WebRTC/servicios de videollamada.
- Conectar pasarelas de pago para cerrar el flujo de reservas.

Con esto tienes un monorepo sencillo listo para iterar sobre el backend y mantener la misma experiencia visual. ¡Éxitos construyendo Nine Lives Edu! 💡

## 🔐 Variables de entorno sugeridas

- `ESP32_API_KEY`: clave esperada en header `x-esp32-key` para endpoints del dispositivo.
- `PIN_HASH_SECRET`: semilla para hash SHA-256 del PIN docente.

> Demo inicial: se crea `teacher-demo-1` con PIN `123456` (hasheado en DB) para pruebas locales.

## 📎 Subida de archivos de apuntes

- Los archivos se guardan en `storage/uploads`.
- Se exponen públicamente por `/uploads/...`.
- Formatos permitidos: PDF, Word, PowerPoint, PNG, JPG, WEBP.
- Límite por archivo: 15 MB.

