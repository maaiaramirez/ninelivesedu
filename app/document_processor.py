"""Extracción de texto de documentos subidos por tutores/profesores para su verificación."""
import requests
from io import BytesIO
from unstructured.partition.auto import partition


def extract_text_from_url(file_url: str) -> str:
    """Descarga un archivo desde una URL y extrae su texto en memoria."""
    response = requests.get(file_url)
    response.raise_for_status()

    file_buffer = BytesIO(response.content)
    elements = partition(file=file_buffer)
    full_text = "\n\n".join([str(el) for el in elements])

    return full_text
