# evaluacion/comparar_costo.py
"""
Costo: pipeline fijo (Avance 2) vs agente (Avance 3) sobre las mismas preguntas.
Mide llamadas al LLM, tokens y tiempo de respuesta (promedio por pregunta).

Uso:  python -m evaluacion.comparar_costo
Salida: evaluacion/resultados/costo.json y costo.md
"""
import json
import time
from pathlib import Path

import src.rag.generacion as gen
from src.agente.agente import responder_agente
from src.rag.pipeline import responder

CARPETA = Path(__file__).parent
RESULTADOS = CARPETA / "resultados"
N_PREGUNTAS = 6     # preguntas dentro del corpus, repartidas a lo largo del conjunto


class Medidor:
    """Envuelve el cliente de Groq para contar llamadas y tokens del pipeline fijo."""

    def __init__(self, cliente):
        self.cliente, self.llamadas, self.tokens = cliente, 0, 0
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, **kw):
        r = self.cliente.chat.completions.create(**kw)
        self.llamadas += 1
        self.tokens += getattr(r.usage, "total_tokens", 0) or 0
        return r


def con_reintento(fn):
    for intento in range(1, 6):
        try:
            return fn()
        except Exception as e:
            if "429" not in str(e) and "rate" not in str(e).lower():
                raise
            time.sleep(15 * intento)
    raise RuntimeError("límite de Groq")


def main():
    preguntas = [q for q in json.loads((CARPETA / "preguntas_eval.json").read_text(encoding="utf-8")) if q["en_corpus"]]
    paso = max(1, len(preguntas) // N_PREGUNTAS)
    elegidas = preguntas[::paso][:N_PREGUNTAS]

    real = gen._get_cliente()
    medidor = Medidor(real)
    gen._get_cliente = lambda: medidor      # el pipeline fijo ahora pasa por el medidor

    pipe = {"llamadas": [], "tokens": [], "tiempo": []}
    agente = {"llamadas": [], "tokens": [], "tiempo": []}
    for q in elegidas:
        medidor.llamadas = medidor.tokens = 0
        t0 = time.perf_counter()
        con_reintento(lambda: responder(q["pregunta"], []))
        pipe["tiempo"].append(time.perf_counter() - t0)
        pipe["llamadas"].append(medidor.llamadas)
        pipe["tokens"].append(medidor.tokens)
        time.sleep(8)

        r = con_reintento(lambda: responder_agente(q["pregunta"], []))
        agente["llamadas"].append(r["llamadas_llm"])
        agente["tokens"].append(r["tokens"])
        agente["tiempo"].append(r["tiempo_s"])
        print(f'#{q["id"]}: pipeline {pipe["llamadas"][-1]} llamadas / {pipe["tokens"][-1]} tokens | '
              f'agente {r["llamadas_llm"]} llamadas / {r["tokens"]} tokens')
        time.sleep(8)

    def prom(l):
        return round(sum(l) / len(l), 2)

    resumen = {
        "preguntas": [q["id"] for q in elegidas],
        "pipeline_fijo": {k: prom(v) for k, v in pipe.items()},
        "agente": {k: prom(v) for k, v in agente.items()},
    }
    (RESULTADOS / "costo.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    p, a = resumen["pipeline_fijo"], resumen["agente"]
    tabla = "\n".join([
        "| Medida (promedio por pregunta) | Pipeline fijo (Avance 2) | Agente (Avance 3) |", "|---|---|---|",
        f'| Llamadas al LLM | {p["llamadas"]} | {a["llamadas"]} |',
        f'| Tokens | {p["tokens"]} | {a["tokens"]} |',
        f'| Tiempo de respuesta (s) | {p["tiempo"]} | {a["tiempo"]} |',
    ])
    (RESULTADOS / "costo.md").write_text(tabla, encoding="utf-8")
    print("\n" + tabla)
    print("Preguntas usadas:", resumen["preguntas"])


if __name__ == "__main__":
    main()
