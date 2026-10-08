# src/rag/pipeline.py

def responder(pregunta: str, historial: list[dict]) -> dict:
    """
    Contrato entre el pipeline RAG (A) y la interfaz (B).

    historial: [{"role": "user" | "assistant", "content": "..."}]
    return: {
        "respuesta": str,
        "fuentes": [{"documento": str, "fragmento": str}]
    }
    """
    # MOCK temporal: A reemplaza esto por el pipeline real
    if "photoshop" in pregunta.lower():
        return {
            "respuesta": "Esa pregunta está fuera de mi alcance: solo ayudo con Git y GitHub.",
            "fuentes": [],
        }
    return {
        "respuesta": f"Respuesta de prueba para: {pregunta}",
        "fuentes": [
            {"documento": "docs_github_ejemplo.pdf", "fragmento": "Fragmento de ejemplo del manual..."}
        ],
    }
