# src/rag/embeddings.py
from fastembed import TextEmbedding

from .config import EMBEDDING_MODEL

_modelo = None


def _get_modelo() -> TextEmbedding:
    """Carga el modelo una sola vez (la primera vez lo descarga)."""
    global _modelo
    if _modelo is None:
        _modelo = TextEmbedding(model_name=EMBEDDING_MODEL)
    return _modelo


def embed_textos(textos: list[str]) -> list[list[float]]:
    """Convierte una lista de textos en vectores."""
    return [v.tolist() for v in _get_modelo().embed(textos)]


def embed_consulta(texto: str) -> list[float]:
    """Convierte una sola pregunta en vector."""
    return embed_textos([texto])[0]


if __name__ == "__main__":
    vector = embed_consulta("Me sale Permission denied (publickey)")
    print(f"Dimensión del vector: {len(vector)}")