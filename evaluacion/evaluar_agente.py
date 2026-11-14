# evaluacion/evaluar_agente.py
"""
Ragas sobre el AGENTE con el mismo conjunto de evaluación del Avance 2.
Los retrieved_contexts son los fragmentos que devolvieron las tools del agente.

Uso:  python -m evaluacion.evaluar_agente            # corre el agente y evalúa
      python -m evaluacion.evaluar_agente --regenerar # vuelve a generar las respuestas
Salida: resultados/resumen_agente.json, detalle_agente.csv y comparacion_ragas.md
"""
import argparse
import json
import time
from pathlib import Path

from langchain_groq import ChatGroq
from ragas import EvaluationDataset, RunConfig, SingleTurnSample, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall, ResponseRelevancy

from evaluacion.evaluar_ragas import EmbeddingsFastembed
from src.agente.agente import responder_agente
from src.rag.config import GROQ_API_KEY

CARPETA = Path(__file__).parent
RESULTADOS = CARPETA / "resultados"
RESULTADOS.mkdir(exist_ok=True)
COLUMNAS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def generar_respuestas(preguntas, ruta, regenerar):
    if ruta.exists() and not regenerar:
        print(f"[agente] usando respuestas guardadas: {ruta.name}")
        return json.loads(ruta.read_text(encoding="utf-8"))
    salida = []
    for q in preguntas:
        for intento in range(1, 8):
            try:
                r = responder_agente(q["pregunta"], [])
                break
            except Exception as e:
                if "429" not in str(e) and "rate" not in str(e).lower():
                    raise
                print(f"[agente] límite de Groq en pregunta {q['id']}, reintento {intento} en {15 * intento}s")
                time.sleep(15 * intento)
        else:
            raise RuntimeError(f"Pregunta {q['id']} falló tras 7 reintentos")
        salida.append({
            "id": q["id"], "en_corpus": q["en_corpus"], "pregunta": q["pregunta"],
            "reference": q["ground_truth"], "respuesta": r["respuesta"],
            "contextos": r["contextos"], "en_contexto": r["en_contexto"],
            "tools": [t["nombre"] for t in r["tools"]], "llamadas_llm": r["llamadas_llm"],
            "tokens": r["tokens"], "tiempo_s": r["tiempo_s"],
        })
        print(f'[agente] pregunta {q["id"]}/{len(preguntas)} · tools: {salida[-1]["tools"]}')
        time.sleep(8)
    ruta.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--juez", default="openai/gpt-oss-120b")
    ap.add_argument("--regenerar", action="store_true")
    args = ap.parse_args()

    preguntas = json.loads((CARPETA / "preguntas_eval.json").read_text(encoding="utf-8"))
    datos = generar_respuestas(preguntas, RESULTADOS / "respuestas_agente.json", args.regenerar)

    fuera = [d for d in datos if not d["en_corpus"]]
    rechazos = sum(1 for d in fuera if not d["en_contexto"])
    print(f"\n[agente] fuera del corpus: rechazo {rechazos}/{len(fuera)} "
          "(puede ser menor que en el Avance 2: ahora el agente puede responder con la web)")

    dentro = [d for d in datos if d["en_corpus"]]
    muestras = [
        SingleTurnSample(
            user_input=d["pregunta"],
            retrieved_contexts=d["contextos"] or ["(la tool no devolvió fragmentos)"],
            response=d["respuesta"], reference=d["reference"],
        )
        for d in dentro
    ]

    juez = ChatGroq(model=args.juez, api_key=GROQ_API_KEY, temperature=0, max_tokens=3000, reasoning_effort="low")
    llm = LangchainLLMWrapper(juez)
    emb = LangchainEmbeddingsWrapper(EmbeddingsFastembed())
    metricas = [
        Faithfulness(llm=llm),
        ResponseRelevancy(llm=llm, embeddings=emb, strictness=1),
        LLMContextPrecisionWithReference(llm=llm),
        LLMContextRecall(llm=llm),
    ]
    resultado = evaluate(
        dataset=EvaluationDataset(samples=muestras), metrics=metricas,
        run_config=RunConfig(max_workers=2, timeout=240, max_retries=8, max_wait=60),
        raise_exceptions=False,
    )
    df = resultado.to_pandas()
    df.insert(0, "id", [d["id"] for d in dentro])
    nombres = {"faithfulness": "faithfulness", "relevancy": "answer_relevancy",
               "precision": "context_precision", "recall": "context_recall"}
    df = df.rename(columns={c: n for c in df.columns for k, n in nombres.items() if k in c.lower() and c != n})
    cols = [c for c in COLUMNAS if c in df.columns]
    promedios = {c: round(float(df[c].mean()), 4) for c in cols}
    df.to_csv(RESULTADOS / "detalle_agente.csv", index=False, encoding="utf-8-sig")

    resumen = {
        "etiqueta": "agente", "juez": args.juez, "preguntas_en_corpus": len(dentro),
        "metricas": promedios, "rechazo_fuera_corpus": f"{rechazos}/{len(fuera)}",
        "preguntas_con_nan": int(df[cols].isna().any(axis=1).sum()),
        "preguntas_sin_tool_de_busqueda": [d["id"] for d in dentro if "buscar_en_base" not in d["tools"]],
    }
    (RESULTADOS / "resumen_agente.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    # Tabla Avance 2 vs agente (el baseline sale de resumen_baseline.json)
    base = json.loads((RESULTADOS / "resumen_baseline.json").read_text(encoding="utf-8"))["metricas"]
    filas = ["| Métrica | Avance 2 (pipeline fijo) | Avance 3 (agente) | Diferencia |", "|---|---|---|---|"]
    for c in cols:
        filas.append(f"| {c} | {base[c]:.3f} | {promedios[c]:.3f} | {promedios[c] - base[c]:+.3f} |")
    (RESULTADOS / "comparacion_ragas.md").write_text("\n".join(filas), encoding="utf-8")

    print("\n=== RESUMEN AGENTE ===")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    print("\n" + "\n".join(filas))
    print("\nPeores preguntas por métrica:")
    for c in cols:
        peor = df.nsmallest(2, c)[["id", c]]
        print(f"  {c}: " + ", ".join(f"#{int(r['id'])} ({r[c]:.2f})" for _, r in peor.iterrows()))


if __name__ == "__main__":
    main()
