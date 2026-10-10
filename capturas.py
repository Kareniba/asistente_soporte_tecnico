import sys
from src.rag.pipeline import responder

pregunta = " ".join(sys.argv[1:])
r = responder(pregunta)
print(f"\nPREGUNTA: {pregunta}")
print(f"[consulta usada: {r['consulta']} | distancia: {r['distancia']}]\n")
print(r["respuesta"])
print("\nFuentes:")
for f in r["fuentes"]:
    print(f" - {f['documento']} (p.{f['pagina']})")
print(f"\nen_contexto: {r['en_contexto']}")