"""Utilidades compartidas por los scripts de la Parte 1 (visión)."""
import base64
import mimetypes
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

CARPETA = Path(__file__).parent
IMAGENES = CARPETA / "imagenes"
RESULTADOS = CARPETA / "resultados"
RESULTADOS.mkdir(exist_ok=True)

MODELO_VISION = os.getenv("MODELO_VISION", "qwen/qwen3.8-27b")


def crear_cliente():
    if not os.getenv("GROQ_API_KEY"):
        raise SystemExit("Falta la variable GROQ_API_KEY en el archivo .env")
    return Groq()


def imagen_a_contenido(ruta, mime=None):
    """Convierte una imagen local en el bloque 'image_url' (base64) que espera la API."""
    ruta = Path(ruta)
    mime = mime or mimetypes.guess_type(ruta.name)[0] or "image/png"
    b64 = base64.b64encode(ruta.read_bytes()).decode("utf-8")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def preguntar(cliente, texto, rutas_imagenes, mime=None, modelo=None, **kwargs):
    """Envía un texto y una o varias imágenes en un mismo mensaje y devuelve el texto."""
    contenido = [{"type": "text", "text": texto}]
    contenido += [imagen_a_contenido(r, mime) for r in rutas_imagenes]
    respuesta = cliente.chat.completions.create(
        model=modelo or MODELO_VISION,
        messages=[{"role": "user", "content": contenido}],
        temperature=0,
        **kwargs,
    )
    return respuesta.choices[0].message.content


# ---------- Parte 2 (audio) ----------
import json

AUDIOS = CARPETA / "audios"
MODELO_AUDIO = os.getenv("MODELO_AUDIO", "whisper-large-v3-turbo")
MODELO_TEXTO = os.getenv("MODELO_TEXTO", "openai/gpt-oss-20b")
FORMATOS_AUDIO = {".wav", ".mp3", ".m4a", ".ogg", ".webm"}
MAX_MB_AUDIO = 25


def listar_audios():
    """Audios de la carpeta audios/ en orden alfabético, con la validación de formato y tamaño."""
    archivos = sorted(p for p in AUDIOS.iterdir() if p.suffix.lower() in FORMATOS_AUDIO)
    if not archivos:
        raise SystemExit(f"No hay audios en {AUDIOS}. Copie allí sus archivos .m4a")
    for a in archivos:
        mb = a.stat().st_size / 1024 / 1024
        if mb > MAX_MB_AUDIO:
            raise SystemExit(f"{a.name} pesa {mb:.1f} MB y el máximo es {MAX_MB_AUDIO} MB")
    return archivos
