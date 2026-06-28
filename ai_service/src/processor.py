import requests
from io import BytesIO
from unstructured.partition.auto import partition

def extract_text_from_url(file_url: str) -> str:
    """Descarga un archivo desde una URL y extrae su texto en memoria."""
    # 1. Descargamos el archivo
    response = requests.get(file_url)
    response.raise_for_status() # Lanza error si la URL falla
    
    # 2. Lo cargamos en memoria temporal (BytesIO)
    file_buffer = BytesIO(response.content)
    
    # 3. Extraemos el texto detectando el formato automáticamente
    elements = partition(file=file_buffer)
    full_text = "\n\n".join([str(el) for el in elements])
    
    return full_text