"""
main.py
=======
Junta todo: crea la app de FastAPI, expone los endpoints REST (login,
registro, aulas, historial) y el WebSocket que habla con el ESP32 y con
la web en tiempo real — igual en el protocolo que backend_ejemplo.py,
pero ahora cada cambio de estado se guarda en la base de datos.
"""

import json
from typing import Dict, List

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import Base, SessionLocal, engine, get_db

# Crea las tablas en la base de datos si todavía no existen.
# (Para un proyecto en producción "de verdad" se usaría Alembic para
# migraciones versionadas; para este alcance, create_all alcanza.)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nine Lives Edu - Backend")

# CORS: permite que tu frontend (en otro dominio, ej. Render o GitHub
# Pages) pueda llamar a esta API desde el navegador. "*" es comodo para
# desarrollo/proyecto escolar; en un producto real conviene restringirlo
# a tu dominio exacto.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =======================================================================
# AUTENTICACION
# =======================================================================

@app.post("/auth/registro", response_model=schemas.UsuarioOut, status_code=status.HTTP_201_CREATED)
def registro(datos: schemas.UsuarioRegistro, db: Session = Depends(get_db)):
    """
    Crea un usuario nuevo. Si rol == "tutor", también crea su fila en
    la tabla `tutores` con el código de acceso (el que va a tipear en
    el teclado del hardware — ver el aviso de sincronización en el README).
    """
    ya_existe = db.query(models.Usuario).filter(models.Usuario.email == datos.email).first()
    if ya_existe:
        raise HTTPException(status_code=400, detail="Ese email ya está registrado")

    nuevo_usuario = models.Usuario(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=auth.hashear_password(datos.password),
        rol=datos.rol,
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    if datos.rol == models.RolUsuario.tutor:
        if not datos.codigo_acceso:
            raise HTTPException(
                status_code=400,
                detail="Los tutores necesitan un codigo_acceso (el que van a tipear en el teclado del hardware)",
            )
        codigo_repetido = db.query(models.Tutor).filter(
            models.Tutor.codigo_acceso == datos.codigo_acceso
        ).first()
        if codigo_repetido:
            raise HTTPException(status_code=400, detail="Ese código de acceso ya está en uso por otro tutor")

        nuevo_tutor = models.Tutor(
            usuario_id=nuevo_usuario.id,
            especialidad=datos.especialidad,
            codigo_acceso=datos.codigo_acceso,
        )
        db.add(nuevo_tutor)
        db.commit()

    return nuevo_usuario


@app.post("/auth/login", response_model=schemas.TokenOut)
def login(datos: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == datos.email).first()

    if not usuario or not auth.verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    token = auth.crear_token({"sub": str(usuario.id)})
    return schemas.TokenOut(access_token=token)


@app.get("/auth/yo", response_model=schemas.UsuarioOut)
def yo(usuario_actual: models.Usuario = Depends(auth.obtener_usuario_actual)):
    """Devuelve los datos del usuario dueño del token enviado."""
    return usuario_actual


# =======================================================================
# AULAS / HISTORIAL
# =======================================================================

@app.get("/aulas", response_model=List[schemas.AulaOut])
def listar_aulas(db: Session = Depends(get_db)):
    return db.query(models.Aula).all()


@app.get("/aulas/{identificador}/historial", response_model=List[schemas.HistorialOut])
def historial_aula(identificador: str, db: Session = Depends(get_db)):
    aula = db.query(models.Aula).filter(models.Aula.identificador == identificador).first()
    if not aula:
        raise HTTPException(status_code=404, detail="Aula no encontrada")
    return aula.historial


def _obtener_o_crear_aula(db: Session, identificador: str) -> models.Aula:
    """
    Si el ESP32 manda un aula_id que todavía no existe en la base, la
    creamos sola con un nombre generico. Así no hace falta pre-cargar
    las aulas a mano antes de la primera conexión del hardware.
    """
    aula = db.query(models.Aula).filter(models.Aula.identificador == identificador).first()
    if aula is None:
        aula = models.Aula(
            identificador=identificador,
            nombre=f"Aula {identificador}",
            estado_actual=models.EstadoAula.INAC,
        )
        db.add(aula)
        db.commit()
        db.refresh(aula)
    return aula


# =======================================================================
# WEBSOCKET (hardware ESP32 <-> web), con persistencia en la DB
# =======================================================================

# Conexiones activas por aula: {"A1": [websocket_hardware, websocket_web1, ...]}
conexiones_por_aula: Dict[str, List[WebSocket]] = {}


@app.websocket("/ws/aula/{aula_id}")
async def websocket_aula(websocket: WebSocket, aula_id: str):
    await websocket.accept()
    conexiones_por_aula.setdefault(aula_id, []).append(websocket)
    print(f"Nueva conexion en aula {aula_id}. Total: {len(conexiones_por_aula[aula_id])}")

    # Al conectarse, le mandamos el ultimo estado conocido (leido de la DB)
    db = SessionLocal()
    try:
        aula = _obtener_o_crear_aula(db, aula_id)
        estado_inicial = {
            "tipo": "estado",
            "aula": aula.identificador,
            "estado": aula.estado_actual.value,
            "codigo": "sync",
        }
        await websocket.send_json(estado_inicial)
    finally:
        db.close()

    try:
        while True:
            data = await websocket.receive_text()

            try:
                mensaje = json.loads(data)
            except json.JSONDecodeError:
                print(f"Mensaje no valido recibido de aula {aula_id}: {data}")
                continue

            print(f"Aula {aula_id} envio: {mensaje}")

            if mensaje.get("tipo") == "estado":
                _guardar_estado_en_db(aula_id, mensaje)
                await _difundir_a_aula(aula_id, mensaje, excluir=websocket)

    except WebSocketDisconnect:
        conexiones_por_aula[aula_id].remove(websocket)
        print(f"Conexion cerrada en aula {aula_id}. Restantes: {len(conexiones_por_aula[aula_id])}")


def _guardar_estado_en_db(aula_id: str, mensaje: dict) -> None:
    """
    Persiste un cambio de estado: actualiza la fila de Aula (estado
    actual) y agrega una fila nueva en HistorialEstado. Abrimos nuestra
    propia sesion de DB aca porque este codigo corre fuera del ciclo
    normal de requests de FastAPI (es un WebSocket), asi que no podemos
    usar la dependencia Depends(get_db).
    """
    db = SessionLocal()
    try:
        aula = _obtener_o_crear_aula(db, aula_id)

        estado_str = mensaje.get("estado", "INAC")
        codigo_usado = mensaje.get("codigo")

        try:
            estado_enum = models.EstadoAula(estado_str)
        except ValueError:
            print(f"Estado desconocido recibido: {estado_str}")
            return

        # Buscamos si el codigo usado corresponde a un tutor registrado.
        # Si no corresponde a ninguno (ej. "sync" o un codigo no
        # registrado en la DB todavia), tutor queda en None: el cambio
        # de estado se guarda igual, solo que sin atribucion a un tutor.
        tutor = None
        if codigo_usado:
            tutor = db.query(models.Tutor).filter(
                models.Tutor.codigo_acceso == codigo_usado
            ).first()

        aula.estado_actual = estado_enum
        aula.tutor_actual_id = tutor.id if (tutor and estado_enum != models.EstadoAula.INAC) else None

        registro = models.HistorialEstado(
            aula_id=aula.id,
            tutor_id=tutor.id if tutor else None,
            estado=estado_enum,
            codigo_usado=codigo_usado,
        )
        db.add(registro)
        db.commit()
    finally:
        db.close()


async def _difundir_a_aula(aula_id: str, mensaje: dict, excluir: WebSocket = None):
    """Reenvia un mensaje a todos los clientes conectados de una misma aula."""
    for conexion in conexiones_por_aula.get(aula_id, []):
        if conexion is excluir:
            continue
        await conexion.send_json(mensaje)


@app.post("/aula/{aula_id}/forzar")
async def forzar_estado(aula_id: str, estado: str, tutor: str = ""):
    """Fuerza un estado desde afuera (ej. un panel de administración) sin pasar por el teclado."""
    comando = {"comando": "forzar_estado", "estado": estado, "tutor": tutor}
    await _difundir_a_aula(aula_id, comando)
    return {"ok": True, "enviado": comando}
