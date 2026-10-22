"""
Nine Lives Edu — almacenamiento de archivos privados en Cloudinary.

Lo usa app/routers/tutores.py para guardar el título/documento que sube un
tutor al postularse.

Cómo funciona:
  - Si NO hay credenciales de Cloudinary en las variables de entorno,
    CLOUDINARY_CONFIGURADO es False y tutores.py guarda el archivo en disco
    (storage/uploads), como siempre. La app arranca igual.
  - Si hay credenciales, subir_privado() sube el archivo como PRIVADO (nunca
    queda con un link público) y devuelve su public_id para guardarlo en la
    base de datos.

Variables de entorno (Render -> Environment). Alcanza con UNA de estas opciones:
  CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
  o bien las tres: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

OJO: mientras app/routers/admin.py solo lea los documentos desde el disco
(UPLOADS_DIR), NO cargues estas variables: el moderador no podría abrir los
archivos que se suban a Cloudinary.
"""
import os

CLOUDINARY_CONFIGURADO = bool(
    os.getenv("CLOUDINARY_URL")
    or (
        os.getenv("CLOUDINARY_CLOUD_NAME")
        and os.getenv("CLOUDINARY_API_KEY")
        and os.getenv("CLOUDINARY_API_SECRET")
    )
)


def subir_privado(contenido: bytes, filename: str, carpeta: str) -> str:
    """Sube el archivo como privado y devuelve su public_id (no una URL)."""
    if not CLOUDINARY_CONFIGURADO:
        raise RuntimeError("Cloudinary no está configurado.")

    # Import tardío: si Cloudinary no se usa, la app arranca aunque el paquete no esté.
    import cloudinary
    import cloudinary.uploader

    if not os.getenv("CLOUDINARY_URL"):
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
            secure=True,
        )

    resultado = cloudinary.uploader.upload(
        contenido,
        public_id=os.path.splitext(filename)[0],
        folder=carpeta,
        resource_type="auto",
        type="authenticated",  # privado: solo accesible con URL firmada
        overwrite=False,
    )
    return resultado["public_id"]
