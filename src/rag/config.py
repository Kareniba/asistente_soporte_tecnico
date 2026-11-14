# src/rag/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Rutas ---
BASE_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = BASE_DIR / "data" / "docs"          # corpus
CHROMA_DIR = BASE_DIR / "chroma_db"            # índice persistente

# --- Chunking ---
CHUNK_SIZE = 800        # caracteres por fragmento
CHUNK_OVERLAP = 120     # solapamiento entre fragmentos

# --- Embeddings (fastembed, sin torch) ---
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# --- Base vectorial ---
COLLECTION_NAME = "gitbot_docs"

# --- Recuperación ---
TOP_K = 4
UMBRAL_DISTANCIA = 0.6   # si el mejor fragmento está más lejos que esto, se considera fuera del corpus

# --- Generación (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "openai/gpt-oss-120b"
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 2000      # alto porque gpt-oss gasta tokens razonando antes de responder
MAX_TURNOS_HISTORIAL = 6   # mensajes previos que se envían para preguntas de seguimiento # cuántos mensajes previos se envían para preguntas de seguimiento

# --- Agente (Avance 3) ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AGENTE_MAX_ITERACIONES = 5     # máximo de llamadas al LLM por pregunta (la última se fuerza sin tools)
BASE_MAX_FRAGMENTOS = 4        # fragmentos que devuelve buscar_en_base por llamada
BASE_MAX_CHARS_FRAGMENTO = 800 # longitud máxima de cada fragmento devuelto
WEB_MAX_RESULTADOS = 3         # resultados que devuelve buscar_en_web
WEB_MAX_CHARS_EXTRACTO = 300   # longitud máxima del extracto de cada resultado web
WEB_SITIOS_PERMITIDOS = [      # fijados en el código: el LLM no puede cambiarlos
    "docs.github.com",
    "git-scm.com",
    "github.blog",
    "githubstatus.com",
]
RUTA_LOG_TOOLS = BASE_DIR / "logs" / "uso_tools.jsonl"
