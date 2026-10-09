# evaluacion/evaluar_ragas.py
"""
Evaluación del RAG con Ragas (4 métricas) + control de alucinaciones.

Uso (desde la raíz del proyecto):
    python -m evaluacion.evaluar_ragas --etiqueta baseline
    python -m evaluacion.evaluar_ragas --etiqueta topk6 --top-k 6 --regenerar
"""
import argparse
import json
import time
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_groq import ChatGroq
from ragas import EvaluationDataset, RunConfig, SingleTurnSample, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)

from src.rag.config import GROQ_API_KEY, TOP_K
from src.rag.embeddings import embed_consulta, embed_textos
from src.rag.pipeline import responder

CARPETA = Path(__file__).parent
RESULTADOS = CARPETA / "resultados"
RESULTADOS.mkdir(exist_ok=True)


class EmbeddingsFastembed(Embeddings):
    """Reutiliza los embeddings del pipeline como embeddings del juez (sin torch)."""

    def embed_documents(self, texts):
        return embed_textos(texts)

    def embed_query(self, text):
        return embed_consulta(text)


def generar_respuestas(preguntas, top_k, ruta, regenerar):
    """Corre cada pregunta por el pipeline y guarda las respuestas (cache)."""
    if ruta.exists() and not regenerar:
        print(f"[eval] usando respuestas guardadas: {ruta.name}")
        return json.loads(ruta.read_text(encoding="utf-8"))

    salida = []
    for q in preguntas:
        for intento in range(1, 8):
            try:
                r = responder(q["pregunta"], [], top_k=top_k)
                break
            except Exception as e:
                if "429" not in str(e) and "rate" not in str(e).lower():
                    raise
                espera = 15 * intento
                print(f"[eval] límite de Groq en pregunta {q['id']}, reintento {intento} en {espera}s")
                time.sleep(espera)
        else:
            raise RuntimeError(f"Pregunta {q['id']} falló tras 7 reintentos")

        salida.append({
            "id": q["id"],
            "en_corpus": q["en_corpus"],
            "pregunta": q["pregunta"],
            "reference": q["ground_truth"],
            "respuesta": r["respuesta"],
            "contextos": r["contextos"],
            "en_contexto": r["en_contexto"],
        })
        print(f"[eval] respondida pregunta {q['id']}/{len(preguntas)}")
        time.sleep(8)
    ruta.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", default="baseline", help="nombre de esta corrida (baseline, mejora1...)")
    ap.add_argument("--top-k", type=int, default=TOP_K)
    ap.add_argument("--juez", default="openai/gpt-oss-120b")
    ap.add_argument("--regenerar", action="store_true", help="volver a generar las respuestas")
    args = ap.parse_args()

    preguntas = json.loads((CARPETA / "preguntas_eval.json").read_text(encoding="utf-8"))
    datos = generar_respuestas(
        preguntas, args.top_k, RESULTADOS / f"respuestas_{args.etiqueta}.json", args.regenerar
    )

    # --- Control de alucinaciones (preguntas fuera del corpus) ---
    fuera = [d for d in datos if not d["en_corpus"]]
    rechazos = sum(1 for d in fuera if not d["en_contexto"])
    print(f"\n[alucinaciones] rechazo correcto fuera del corpus: {rechazos}/{len(fuera)}")

    # --- Ragas (solo preguntas dentro del corpus) ---
    dentro = [d for d in datos if d["en_corpus"]]
    muestras = [
        SingleTurnSample(
            user_input=d["pregunta"],
            retrieved_contexts=d["contextos"],
            response=d["respuesta"],
            reference=d["reference"],
        )
        for d in dentro
    ]

    juez = ChatGroq(
    model=args.juez,
    api_key=GROQ_API_KEY,
    temperature=0,
    max_tokens=3000,
    reasoning_effort="low",
)
    llm = LangchainLLMWrapper(juez)
    emb = LangchainEmbeddingsWrapper(EmbeddingsFastembed())

    metricas = [
        Faithfulness(llm=llm),
        ResponseRelevancy(llm=llm, embeddings=emb, strictness=1),
        LLMContextPrecisionWithReference(llm=llm),
        LLMContextRecall(llm=llm),
    ]

    resultado = evaluate(
        dataset=EvaluationDataset(samples=muestras),
        metrics=metricas,
        run_config=RunConfig(max_workers=2, timeout=240, max_retries=8, max_wait=60),
        raise_exceptions=False,
    )
    df = resultado.to_pandas()
    df.insert(0, "id", [d["id"] for d in dentro])

    # Nombres de columna claros, sin depender de la versión de Ragas
    nombres = {"faithfulness": "faithfulness", "relevancy": "answer_relevancy",
               "precision": "context_precision", "recall": "context_recall"}
    renombrar = {c: n for c in df.columns for k, n in nombres.items() if k in c.lower() and c != n}
    df = df.rename(columns=renombrar)

    cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    cols = [c for c in cols if c in df.columns]
    promedios = {c: round(float(df[c].mean()), 4) for c in cols}

    df.to_csv(RESULTADOS / f"detalle_{args.etiqueta}.csv", index=False, encoding="utf-8-sig")
    resumen = {
        "etiqueta": args.etiqueta,
        "top_k": args.top_k,
        "juez": args.juez,
        "preguntas_en_corpus": len(dentro),
        "metricas": promedios,
        "rechazo_fuera_corpus": f"{rechazos}/{len(fuera)}",
        "preguntas_con_nan": int(df[cols].isna().any(axis=1).sum()),
    }
    (RESULTADOS / f"resumen_{args.etiqueta}.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n=== RESUMEN ===")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    print("\nPeores preguntas por métrica:")
    for c in cols:
        peor = df.nsmallest(2, c)[["id", c]]
        print(f"  {c}: " + ", ".join(f"#{int(r['id'])} ({r[c]:.2f})" for _, r in peor.iterrows()))


if __name__ == "__main__":
    main()