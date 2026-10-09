# src/rag/pipeline.py
"""
Pipeline RAG completo. Contrato con la interfaz:

responder(pregunta, historial) -> {
    "respuesta": str,
    "fuentes": [{"documento": str, "fragmento": str, "pagina": int}],
    "en_contexto": bool,      # extra: False si no estaba en el corpus
    "contextos": [str],       # extra: fragmentos recuperados (los usa Ragas)
    "consulta": str,          # extra: pregunta reformulada usada para buscar
    "distancia": float | None # extra: distancia del mejor fragmento
}
historial: [{"role": "user" | "assistant", "content": "..."}]
"""
from .config import TOP_K, UMBRAL_DISTANCIA
from .retrieval import recuperar
from .generacion import generar, reformular_pregunta

MENSAJE_FUERA_DE_CORPUS = (
    "No encontré esa información en mi base de conocimientos. "
    "Solo puedo ayudarte con soporte técnico de Git y GitHub "
    "(autenticación SSH, conflictos de merge y pull requests)."
)


def _formatear_respuesta(r: dict) -> str:
    if not r.get("en_contexto"):
        return MENSAJE_FUERA_DE_CORPUS
    texto = r.get("diagnostico", "").strip()
    pasos = r.get("solucion", [])
    if pasos:
        texto += "\n\n" + "\n".join(f"{i}. {p}" for i, p in enumerate(pasos, start=1))
    return texto


def responder(pregunta: str, historial: list[dict] | None = None, top_k: int = TOP_K) -> dict:
    historial = historial or []

    # Seguimientos: se reformula como pregunta completa antes de buscar
    consulta = reformular_pregunta(pregunta, historial)

    fragmentos = recuperar(consulta, top_k=top_k)
    contextos = [f["texto"] for f in fragmentos]
    distancia = fragmentos[0]["distancia"] if fragmentos else None

    # Filtro: si lo mejor que hay está muy lejos, no se llama al LLM
    if distancia is None or distancia > UMBRAL_DISTANCIA:
        return {
            "respuesta": MENSAJE_FUERA_DE_CORPUS,
            "fuentes": [],
            "en_contexto": False,
            "contextos": contextos,
            "consulta": consulta,
            "distancia": distancia,
        }

    # Generación con el prompt del Avance 1 refinado
    resultado = generar(consulta, fragmentos, historial)
    en_contexto = bool(resultado.get("en_contexto"))

    # Convierte los números de fragmento en documento + texto citable
    ids = [i for i in resultado.get("fuentes_usadas", []) if isinstance(i, int) and 1 <= i <= len(fragmentos)]
    if en_contexto and not ids:
        ids = [1]
    fuentes = [
        {
            "documento": fragmentos[i - 1]["documento"],
            "fragmento": fragmentos[i - 1]["texto"][:400],
            "pagina": fragmentos[i - 1]["pagina"],
        }
        for i in ids
    ] if en_contexto else []

    return {
        "respuesta": _formatear_respuesta(resultado),
        "fuentes": fuentes,
        "en_contexto": en_contexto,
        "contextos": contextos,
        "consulta": consulta,
        "distancia": distancia,
    }


if __name__ == "__main__":
    historial = []
    for p in [
        "Tengo un conflicto de merge en mi pull request, ¿cómo lo resuelvo?",
        "¿y si prefiero hacerlo desde la línea de comandos?",
        "¿qué hago después de resolverlo?",
    ]:
        r = responder(p, historial)
        print(f"\n>>> {p}")
        print(f"[consulta usada: {r['consulta']} | distancia: {r['distancia']}]")
        print(r["respuesta"])
        print("Fuentes:", [f["documento"] for f in r["fuentes"]], "| en_contexto:", r["en_contexto"])
        historial += [{"role": "user", "content": p}, {"role": "assistant", "content": r["respuesta"]}]
