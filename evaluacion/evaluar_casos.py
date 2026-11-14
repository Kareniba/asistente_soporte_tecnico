# evaluacion/evaluar_casos.py
"""
Casos de comportamiento del agente. El comportamiento esperado está escrito en
casos_comportamiento.json ANTES de ejecutar; este script solo compara.

Uso:  python -m evaluacion.evaluar_casos
Salida: evaluacion/resultados/casos_comportamiento.json y .md (tabla para el informe)
"""
import json
import re
import time
from pathlib import Path

from src.agente.agente import responder_agente
from src.agente.prompt_agente import MENSAJE_FUERA_DE_CORPUS
from src.rag.config import WEB_SITIOS_PERMITIDOS

CARPETA = Path(__file__).parent
RESULTADOS = CARPETA / "resultados"
RESULTADOS.mkdir(exist_ok=True)


def _normalizar(texto: str) -> str:
    """El modelo a veces escribe guiones tipográficos (‑ – —) en vez de «-»; se igualan antes de comparar."""
    for guion in "\u2010\u2011\u2012\u2013\u2014\u2212":
        texto = texto.replace(guion, "-")
    return texto


def evaluar(caso: dict, r: dict) -> list[str]:
    """Devuelve la lista de incumplimientos (vacía = cumple)."""
    fallos = []
    usadas = [t["nombre"] for t in r["tools"]]
    texto = _normalizar(r["respuesta"])
    for t in caso.get("tools_requeridas", []):
        if t not in usadas:
            fallos.append(f"no llamó {t}")
    for t in caso.get("tools_prohibidas", []):
        if t in usadas:
            fallos.append(f"llamó {t} (prohibida)")
    for t, n in caso.get("min_llamadas", {}).items():
        if usadas.count(t) < n:
            fallos.append(f"llamó {t} {usadas.count(t)} vez/veces (mínimo {n})")
    for s in caso.get("debe_contener", []):
        if s.lower() not in texto.lower():
            fallos.append(f"la respuesta no contiene «{s}»")
    for s in caso.get("no_debe_contener", []):
        if s.lower() in texto.lower():
            fallos.append(f"la respuesta contiene «{s}»")
    if "max_chars_respuesta" in caso and len(texto) > caso["max_chars_respuesta"]:
        fallos.append(f"respuesta demasiado larga ({len(texto)} caracteres)")
    if caso.get("debe_ser_rechazo") and r["en_contexto"]:
        fallos.append("no respondió el mensaje fijo de rechazo")
    if caso.get("urls_solo_permitidas"):
        for url in re.findall(r"https?://[^\s\]\)]+", texto):
            if not any(d in url for d in WEB_SITIOS_PERMITIDOS):
                fallos.append(f"URL fuera de los sitios permitidos: {url}")
    return fallos


def main():
    casos = json.loads((CARPETA / "casos_comportamiento.json").read_text(encoding="utf-8"))
    salida = []
    for caso in casos:
        for intento in range(1, 6):
            try:
                r = responder_agente(caso["pregunta"], [])
                break
            except Exception as e:
                if "429" not in str(e) and "rate" not in str(e).lower():
                    raise
                print(f"[casos] límite de Groq, reintento {intento} en {15 * intento}s")
                time.sleep(15 * intento)
        fallos = evaluar(caso, r)
        usadas = ", ".join(f'{t["nombre"]}({json.dumps(t["args"], ensure_ascii=False)[:80]})' for t in r["tools"]) or "ninguna"
        print(f'\n=== Caso {caso["id"]} · {caso["tipo"]} ===')
        print("Pregunta:", caso["pregunta"][:120].replace("\n", " "))
        print("Esperado:", caso["esperado"])
        print("Tools:", usadas, "| llamadas LLM:", r["llamadas_llm"])
        print("Respuesta:", r["respuesta"][:500])
        print("CUMPLE" if not fallos else "NO CUMPLE: " + "; ".join(fallos))
        salida.append({
            "id": caso["id"], "tipo": caso["tipo"], "pregunta": caso["pregunta"],
            "esperado": caso["esperado"], "obtenido": r["respuesta"], "tools": r["tools"],
            "llamadas_llm": r["llamadas_llm"], "tokens": r["tokens"], "tiempo_s": r["tiempo_s"],
            "cumple": not fallos, "incumplimientos": fallos,
        })
        time.sleep(5)

    (RESULTADOS / "casos_comportamiento.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    filas = ["| # | Tipo | Esperado | Obtenido (resumen) | Tools usadas | Llam. LLM | ¿Cumple? |", "|---|---|---|---|---|---|---|"]
    for s in salida:
        tools = "<br>".join(t["nombre"] for t in s["tools"]) or "ninguna"
        obtenido = s["obtenido"][:160].replace("\n", " ").replace("|", "/")
        filas.append(f'| {s["id"]} | {s["tipo"]} | {s["esperado"]} | {obtenido}… | {tools} | {s["llamadas_llm"]} | {"Sí" if s["cumple"] else "No: " + "; ".join(s["incumplimientos"])} |')
    (RESULTADOS / "casos_comportamiento.md").write_text("\n".join(filas), encoding="utf-8")
    print(f'\nCumplidos: {sum(s["cumple"] for s in salida)}/{len(salida)}')


if __name__ == "__main__":
    main()
