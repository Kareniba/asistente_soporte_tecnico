# src/agente/agente.py
"""
Agente GitBot (Avance 3): el LLM decide qué tool llamar; este programa la ejecuta
y devuelve el resultado al LLM, en un bucle con límite de iteraciones.

responder_agente(pregunta, historial) -> {
    "respuesta": str,
    "fuentes_base": [{"documento", "pagina", "fragmento"}],
    "fuentes_web": [{"titulo", "url", "extracto"}],
    "tools": [{"nombre", "args", "resumen"}],     # lo que muestra la interfaz y el log
    "llamadas_llm": int, "tokens": int, "tiempo_s": float,
    "contextos": [str],                            # fragmentos devueltos por las tools (Ragas)
    "en_contexto": bool,                           # False si respondió el mensaje fijo de rechazo
}
"""
import json
import logging
import time
from datetime import datetime, timezone

from src.rag.config import (
    AGENTE_MAX_ITERACIONES, LLM_MAX_TOKENS, LLM_MODEL, LLM_TEMPERATURE,
    MAX_TURNOS_HISTORIAL, RUTA_LOG_TOOLS,
)
from src.rag.generacion import _get_cliente

from .herramientas import HERRAMIENTAS, esquemas
from .prompt_agente import MENSAJE_FUERA_DE_CORPUS, SYSTEM_PROMPT

log = logging.getLogger("gitbot.agente")

MAX_CHARS_PREGUNTA = 2000
MAX_CHARS_RESULTADO_TOOL = 6000   # tope duro de lo que se le devuelve al LLM por llamada


def _resumir(nombre: str, resultado: dict) -> str:
    """Resumen corto de un resultado de tool, para la interfaz y el log."""
    if nombre == "buscar_en_base":
        docs = [f'{f["documento"]} (p.{f["pagina"]})' for f in resultado.get("fragmentos", [])]
        return f'{len(docs)} fragmentos: ' + "; ".join(docs) if docs else resultado.get("mensaje", "sin resultados")
    if nombre == "buscar_en_web":
        urls = [r["url"] for r in resultado.get("resultados", [])]
        return f'{len(urls)} resultados: ' + "; ".join(urls) if urls else resultado.get("mensaje", "sin resultados")
    if nombre == "analizar_conflicto_merge":
        return f'{resultado.get("total_conflictos", 0)} conflictos encontrados'
    if nombre == "validar_nombre_rama":
        return "válido" if resultado.get("valido") else "inválido: " + "; ".join(resultado.get("problemas", []))
    return str(resultado)[:200]


def _ejecutar_tool(nombre: str, args: dict, ya_llamadas: list[str]) -> dict:
    herramienta = HERRAMIENTAS.get(nombre)
    if herramienta is None:
        return {"error": f"La tool «{nombre}» no existe."}
    # Política «primero la base»: la web solo se habilita si ya se consultó la base en esta pregunta
    if nombre == "buscar_en_web" and "buscar_en_base" not in ya_llamadas:
        return {"origen": "web", "resultados": [],
                "mensaje": "BLOQUEADA: primero debes consultar buscar_en_base. Usa la web solo si la base no tiene la respuesta."}
    try:
        return herramienta.invoke(args)
    except TypeError:
        return {"error": f"Argumentos inválidos para {nombre}."}
    except Exception as e:
        log.exception("Fallo en la tool %s", nombre)
        return {"error": f"La tool {nombre} falló ({type(e).__name__})."}


MAX_REINTENTOS_TOOL_INVALIDA = 2   # veces que se reintenta si el modelo inventa o escribe mal el nombre de una tool


def _llamar_llm(kwargs: dict) -> tuple[object, int]:
    """
    Llama al LLM. Si Groq rechaza la llamada porque el modelo escribió mal el nombre de una
    tool (error `tool_use_failed`), reintenta recordándole los nombres válidos.
    Devuelve (respuesta, número de llamadas hechas) para que el conteo sea honesto.
    """
    llamadas = 0
    mensajes = list(kwargs["messages"])
    for intento in range(MAX_REINTENTOS_TOOL_INVALIDA + 1):
        llamadas += 1
        try:
            return _get_cliente().chat.completions.create(**{**kwargs, "messages": mensajes}), llamadas
        except Exception as e:
            if "tool_use_failed" not in str(e) or intento == MAX_REINTENTOS_TOOL_INVALIDA:
                raise
            log.warning("El modelo llamó una tool inválida; reintento %s", intento + 1)
            mensajes = mensajes + [{
                "role": "user",
                "content": "Aviso del sistema: la llamada anterior usó un nombre de tool inválido. "
                           "Los nombres exactos son: " + ", ".join(HERRAMIENTAS) + ". Vuelve a intentarlo.",
            }]


def _registrar(entrada: dict) -> None:
    try:
        RUTA_LOG_TOOLS.parent.mkdir(parents=True, exist_ok=True)
        with RUTA_LOG_TOOLS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    except OSError:
        log.warning("No se pudo escribir el registro de uso de tools")


def responder_agente(pregunta: str, historial: list[dict] | None = None) -> dict:
    inicio = time.perf_counter()
    pregunta = (pregunta or "").strip()[:MAX_CHARS_PREGUNTA]
    historial = (historial or [])[-MAX_TURNOS_HISTORIAL:]

    mensajes = [{"role": "system", "content": SYSTEM_PROMPT}] + historial + [{"role": "user", "content": pregunta}]
    tools_usadas, nombres_llamados = [], []
    fuentes_base, fuentes_web, contextos = [], [], []
    llamadas_llm, tokens = 0, 0
    respuesta = ""

    for iteracion in range(1, AGENTE_MAX_ITERACIONES + 1):
        ultima = iteracion == AGENTE_MAX_ITERACIONES
        kwargs = dict(model=LLM_MODEL, messages=mensajes, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS)
        if not ultima:   # en la última vuelta no se ofrecen tools: obliga a responder
            kwargs.update(tools=esquemas(), tool_choice="auto")

        r, n = _llamar_llm(kwargs)
        llamadas_llm += n
        tokens += getattr(r.usage, "total_tokens", 0) or 0
        msg = r.choices[0].message

        if not msg.tool_calls:
            respuesta = (msg.content or "").strip()
            break

        mensajes.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in msg.tool_calls
            ],
        })
        for c in msg.tool_calls:
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            resultado = _ejecutar_tool(c.function.name, args, nombres_llamados)
            nombres_llamados.append(c.function.name)

            for f in resultado.get("fragmentos", []):
                contextos.append(f["texto"])
                fuentes_base.append({"documento": f["documento"], "pagina": f["pagina"], "fragmento": f["texto"][:400]})
            for w in resultado.get("resultados", []):
                contextos.append(w["extracto"])
                fuentes_web.append({"titulo": w["titulo"], "url": w["url"], "extracto": w["extracto"]})

            tools_usadas.append({"nombre": c.function.name, "args": args, "resumen": _resumir(c.function.name, resultado)})
            mensajes.append({
                "role": "tool",
                "tool_call_id": c.id,
                "content": json.dumps(resultado, ensure_ascii=False)[:MAX_CHARS_RESULTADO_TOOL],
            })

    if not respuesta:
        respuesta = MENSAJE_FUERA_DE_CORPUS

    rechazo = respuesta.strip().startswith(MENSAJE_FUERA_DE_CORPUS[:40])

    # Solo se muestran como fuentes las que la respuesta realmente cita (sin duplicados)
    def _unicas(items, clave):
        vistos, salida = set(), []
        for it in items:
            k = clave(it)
            if k not in vistos:
                vistos.add(k)
                salida.append(it)
        return salida

    if rechazo:
        fuentes_base, fuentes_web = [], []
    else:
        base_citadas = [f for f in fuentes_base if f["documento"] in respuesta]
        web_citadas = [w for w in fuentes_web if w["url"] in respuesta]
        fuentes_base = _unicas(base_citadas or fuentes_base, lambda f: (f["documento"], f["pagina"]))
        fuentes_web = _unicas(web_citadas or fuentes_web, lambda w: w["url"])

    tiempo = round(time.perf_counter() - inicio, 2)
    _registrar({
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pregunta": pregunta,
        "tools": tools_usadas,
        "llamadas_llm": llamadas_llm,
        "tokens": tokens,
        "tiempo_s": tiempo,
        "rechazo": rechazo,
    })

    return {
        "respuesta": respuesta,
        "fuentes_base": fuentes_base,
        "fuentes_web": fuentes_web,
        "tools": tools_usadas,
        "llamadas_llm": llamadas_llm,
        "tokens": tokens,
        "tiempo_s": tiempo,
        "contextos": contextos,
        "en_contexto": not rechazo,
    }


if __name__ == "__main__":
    import sys
    p = " ".join(sys.argv[1:]) or "Me sale Permission denied (publickey) cuando hago git push"
    r = responder_agente(p)
    print(r["respuesta"])
    print("\nTools:", json.dumps(r["tools"], ensure_ascii=False, indent=2))
    print(f'LLM: {r["llamadas_llm"]} llamadas, {r["tokens"]} tokens, {r["tiempo_s"]} s')
