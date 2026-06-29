from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Esto permite que tu iPhone se conecte sin bloqueos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def inicio():
    return {"mensaje": "El backend de Python está vivo"}

@app.post("/login")
def login():
    # Aquí irá tu lógica de login más adelante
    return {"success": True, "message": "Conectado al nuevo backend"}