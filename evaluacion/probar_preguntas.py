# evaluacion/probar_preguntas.py
"""Corre las preguntas del dataset por el pipeline y muestra qué tal le fue a cada una."""
import json
import time
from pathlib import Path

from src.rag.pipeline import responder
from src.rag.retrieval import recuperar

RUTA = Path(__file__).parent / "preguntas_eval.json"
preguntas = json.loads(RUTA.read_text(encoding="utf-8"))

aciertos_ret = 0
total_con_corpus = 0
aciertos_rechazo = 0
total_fuera = 0

for q in preguntas:
    r = responder(q["pregunta"])
    docs = [f["documento"] for f in recuperar(q["pregunta"])]

    print(f"\n[{q['id']}] ({q['tipo']}) {q['pregunta']}")
    print(f"    Respuesta: {r['respuesta'][:200].replace(chr(10), ' ')}...")

    if q["en_corpus"]:
        total_con_corpus += 1
        ok = q["documento_esperado"] in docs
        aciertos_ret += ok
        print(f"    Documento esperado recuperado: {'SI' if ok else 'NO'}")
        print(f"    Respondió con contexto: {r['en_contexto']}")
    else:
        total_fuera += 1
        ok = not r["en_contexto"]
        aciertos_rechazo += ok
        print(f"    Rechazó correctamente: {'SI' if ok else 'NO (posible alucinación)'}")

    time.sleep(1)  # para no pasarse del límite de Groq

print("\n" + "=" * 50)
print(f"Recuperación correcta: {aciertos_ret}/{total_con_corpus}")
print(f"Rechazo correcto fuera del corpus: {aciertos_rechazo}/{total_fuera}")