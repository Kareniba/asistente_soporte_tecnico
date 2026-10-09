# src/rag/chunking.py
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import CHUNK_SIZE, CHUNK_OVERLAP
from .ingesta import cargar_documentos


def crear_chunks(documentos: list[dict],
                 chunk_size: int = CHUNK_SIZE,
                 chunk_overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Divide cada documento en fragmentos con solapamiento.
    Criterio de corte: primero párrafos, luego líneas, luego frases y,
    como último recurso, palabras, para no cortar ideas a la mitad.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for doc in documentos:
        for i, texto in enumerate(splitter.split_text(doc["texto"])):
            chunks.append({
                "id": f'{doc["documento"]}_p{doc["pagina"]}_c{i}',
                "texto": texto,
                "documento": doc["documento"],
                "pagina": doc["pagina"],
            })
    return chunks


if __name__ == "__main__":
    chunks = crear_chunks(cargar_documentos())
    print(f"Total de chunks: {len(chunks)}")
    if chunks:
        print("\nEjemplo:")
        print(chunks[0]["id"])
        print(chunks[0]["texto"][:300])