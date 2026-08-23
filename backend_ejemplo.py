"""
NINE LIVES EDU - Backend de referencia (FastAPI)
=================================================
Ejemplo minimo del endpoint WebSocket que espera el firmware del ESP32.
No es el backend final del proyecto: sirve para probar la comunicacion
Arduino <-> servidor mientras desarrollas el resto de la plataforma
(PWA, base de datos, autenticacion, etc).

Ejecutar localmente con:
    pip install fastapi "uvicorn[standard]"
    uvicorn backend_ejemplo:app --host 0.0.0.0 --port 8000 --reload

El ESP32 (en modo local) se conecta a:
    ws://<IP_DE_ESTA_PC>:8000/ws/aula/A1

---------------------------------------------------------------------
DESPLIEGUE EN RENDER (para que funcione desde cualquier red, no solo local)
---------------------------------------------------------------------
1) Subi este archivo + requirements.txt a un repo de GitHub.
2) En Render: New > Web Service > conecta ese repo.
3) Configuracion del servicio:
     Build Command: pip install -r requirements.txt
     Start Command: uvicorn backend_ejemplo:app --host 0.0.0.0 --port $PORT
   (Render inyecta la variable $PORT automaticamente, no la fijes vos)
4) Al terminar el deploy, Render te da una URL publica, por ejemplo:
     https://nine-lives-edu-backend.onrender.com
5) Con ese dominio (sin "https://"):
   - En el .ino del ESP32: RENDER_HOST = "nine-lives-edu-backend.onrender.com"
   - En script.js de la web: RENDER_HOST = "nine-lives-edu-backend.onrender.com"

Nota: el plan gratuito de Render "duerme" el servicio tras un rato sin
trafico, y tarda unos segundos en despertar con la primera conexion.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

app = FastAPI()

# Conexiones activas por aula: {"A1": [websocket_hardware, websocket_pwa1, ...]}
conexiones_por_aula: Dict[str, List[WebSocket]] = {}

# Ultimo estado conocido de cada aula, para informarlo a quien se conecte despues
ultimo_estado_por_aula: Dict[str, dict] = {}


@app.websocket("/ws/aula/{aula_id}")
async def websocket_aula(websocket: WebSocket, aula_id: str):
    await websocket.accept()
    conexiones_por_aula.setdefault(aula_id, []).append(websocket)
    print(f"Nueva conexion en aula {aula_id}. Total: {len(conexiones_por_aula[aula_id])}")

    # Si ya conocemos el ultimo estado del aula, se lo mandamos al que recien se conecta
    if aula_id in ultimo_estado_por_aula:
        await websocket.send_json(ultimo_estado_por_aula[aula_id])

    try:
        while True:
            data = await websocket.receive_text()

            try:
                mensaje = json.loads(data)
            except json.JSONDecodeError:
                print(f"Mensaje no valido recibido de aula {aula_id}: {data}")
                continue

            print(f"Aula {aula_id} envio: {mensaje}")

            # Si es una actualizacion de estado del hardware, la guardamos
            # y la reenviamos (broadcast) a todos los clientes de esa aula
            # (por ejemplo, apps/PWA de los alumnos escuchando ese canal).
            if mensaje.get("tipo") == "estado":
                ultimo_estado_por_aula[aula_id] = mensaje
                await difundir_a_aula(aula_id, mensaje, excluir=websocket)

    except WebSocketDisconnect:
        conexiones_por_aula[aula_id].remove(websocket)
        print(f"Conexion cerrada en aula {aula_id}. Restantes: {len(conexiones_por_aula[aula_id])}")


async def difundir_a_aula(aula_id: str, mensaje: dict, excluir: WebSocket = None):
    """Reenvia un mensaje a todos los clientes conectados de una misma aula."""
    for conexion in conexiones_por_aula.get(aula_id, []):
        if conexion is excluir:
            continue
        await conexion.send_json(mensaje)


# ---------------------------------------------------------------------
# Endpoint de ejemplo para forzar un estado desde afuera (ej. panel admin)
# Envia un comando al hardware conectado en esa aula.
# ---------------------------------------------------------------------
@app.post("/aula/{aula_id}/forzar")
async def forzar_estado(aula_id: str, estado: str, tutor: str = ""):
    comando = {"comando": "forzar_estado", "estado": estado, "tutor": tutor}
    await difundir_a_aula(aula_id, comando)
    return {"ok": True, "enviado": comando}
