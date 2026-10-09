# src/rag/vectorstore.py
import chromadb

from .config import CHROMA_DIR, COLLECTION_NAME
from .chunking import crear_chunks
from .embeddings import embed_textos
from .ingesta import cargar_documentos


def _get_cliente():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_coleccion():
    """Devuelve la colección existente (la usa la recuperación)."""
    return _get_cliente().get_collection(COLLECTION_NAME)


def construir_indice(chunks: list[dict] | None = None, batch: int = 64) -> int:
    """Borra el índice anterior y lo reconstruye desde cero. Devuelve cuántos chunks guardó."""
    if chunks is None:
        chunks = crear_chunks(cargar_documentos())

    cliente = _get_cliente()
    try:
        cliente.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    coleccion = cliente.create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    for i in range(0, len(chunks), batch):
        lote = chunks[i:i + batch]
        coleccion.add(
            ids=[c["id"] for c in lote],
            documents=[c["texto"] for c in lote],
            embeddings=embed_textos([c["texto"] for c in lote]),
            metadatas=[{"documento": c["documento"], "pagina": c["pagina"]} for c in lote],
        )
        print(f"[indice] {min(i + batch, len(chunks))}/{len(chunks)} chunks indexados")

    return len(chunks)


if __name__ == "__main__":
    total = construir_indice()
    print(f"Índice creado en {CHROMA_DIR} con {total} chunks")