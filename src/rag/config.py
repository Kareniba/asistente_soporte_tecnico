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

# --- Generación (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "llama-3.3-70b-versatile"
LLM_TEMPERATURE = 0.1