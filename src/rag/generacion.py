# src/rag/generacion.py
import json

from groq import Groq

from .config import (
    GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, MAX_TURNOS_HISTORIAL,
)
from .prompt import SYSTEM_PROMPT, FEW_SHOT, construir_mensaje_usuario

_cliente = None


def _get_cliente() -> Groq:
    global _cliente
    if _cliente is None:
        if not GROQ_API_KEY:
            raise RuntimeError("Falta GROQ_API_KEY: ponla en el archivo .env o en las variables de entorno.")
        _cliente = Groq(api_key=GROQ_API_KEY)
    return _cliente


def reformular_pregunta(pregunta: str, historial: list[dict] | None) -> str:
    """
    Convierte una pregunta de seguimiento en una pregunta completa e independiente,
    usando el historial. Si no hay historial, devuelve la pregunta tal cual.
    """
    if not historial:
        return pregunta

    ultimos = historial[-MAX_TURNOS_HISTORIAL:]
    conversacion = "\n".join(f'{m["role"]}: {m["content"][:300]}' for m in ultimos)
    instruccion = (
        "Reescribe la ÚLTIMA pregunta del usuario como una pregunta completa e "
        "independiente, usando la conversación para incluir el tema al que se refiere. "
        "Si ya es independiente, devuélvela igual. Responde SOLO con la pregunta, en español.\n\n"
        f"<conversacion>\n{conversacion}\n</conversacion>\n"
        f"<ultima_pregunta>\n{pregunta}\n</ultima_pregunta>"
    )
    try:
        r = _get_cliente().chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": instruccion}],
            temperature=0,
            max_tokens=800,
        )
        return (r.choices[0].message.content or "").strip() or pregunta
    except Exception:
        return pregunta


def generar(pregunta: str, fragmentos: list[dict], historial: list[dict] | None = None) -> dict:
    """
    Llama al LLM con: system prompt + few-shot + historial reciente + contexto recuperado.
    Devuelve el JSON del asistente ya convertido a dict.
    """
    historial = (historial or [])[-MAX_TURNOS_HISTORIAL:]

    mensajes = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + FEW_SHOT
        + historial
        + [{"role": "user", "content": construir_mensaje_usuario(pregunta, fragmentos)}]
    )

    respuesta = _get_cliente().chat.completions.create(
        model=LLM_MODEL,
        messages=mensajes,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        response_format={"type": "json_object"},
    )
    texto = respuesta.choices[0].message.content

    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return {
            "en_contexto": False,
            "diagnostico": "No pude generar una respuesta válida.",
            "solucion": [],
            "nivel_confianza": "bajo",
            "fuentes_usadas": [],
        }


if __name__ == "__main__":
    from .retrieval import recuperar

    pregunta = "Me sale Permission denied (publickey) cuando hago git push"
    fragmentos = recuperar(pregunta)
    print(json.dumps(generar(pregunta, fragmentos), indent=2, ensure_ascii=False))