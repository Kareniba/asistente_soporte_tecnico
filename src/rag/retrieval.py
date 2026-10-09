# src/rag/retrieval.py
from .config import TOP_K
from .embeddings import embed_consulta
from .vectorstore import get_coleccion


def recuperar(pregunta: str, top_k: int = TOP_K) -> list[dict]:
    """Busca los top_k fragmentos más parecidos a la pregunta (similitud coseno)."""
    resultado = get_coleccion().query(
        query_embeddings=[embed_consulta(pregunta)],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    fragmentos = []
    for texto, meta, dist in zip(
        resultado["documents"][0],
        resultado["metadatas"][0],
        resultado["distances"][0],
    ):
        fragmentos.append({
            "texto": texto,
            "documento": meta["documento"],
            "pagina": meta["pagina"],
            "distancia": round(dist, 4),  # más bajo = más parecido
        })
    return fragmentos


if __name__ == "__main__":
    pregunta = "Me sale Permission denied (publickey) cuando hago git push"
    print(f"Pregunta: {pregunta}\n")
    for i, f in enumerate(recuperar(pregunta), start=1):
        print(f"[{i}] {f['documento']} (p.{f['pagina']}) distancia={f['distancia']}")
        print(f"    {f['texto'][:150]}...\n")