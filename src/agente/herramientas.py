# src/agente/herramientas.py
"""
Tools del agente GitBot (Avance 3).

Cada tool es una función normal de Python envuelta en `Herramienta`, que guarda
su descripción (docstring), el esquema de argumentos que ve el LLM y un método
`.invoke(args)` para probarla sin LLM. Los LÍMITES (fragmentos, longitudes,
sitios web permitidos) están escritos aquí, en el código; el prompt no puede
cambiarlos.

Tools:
  buscar_en_base          (búsqueda) fragmentos del corpus local, con documento y página
  analizar_conflicto_merge (tarea)   analiza marcadores de conflicto de un texto pegado
  validar_nombre_rama      (tarea)   aplica las reglas de git check-ref-format
  buscar_en_web            (web)     Tavily restringido a sitios oficiales
"""
import re
from urllib.parse import urlparse

import httpx

from src.rag.config import (
    BASE_MAX_CHARS_FRAGMENTO, BASE_MAX_FRAGMENTOS, TAVILY_API_KEY, UMBRAL_DISTANCIA,
    WEB_MAX_CHARS_EXTRACTO, WEB_MAX_RESULTADOS, WEB_SITIOS_PERMITIDOS,
)

MAX_CHARS_CONSULTA = 300     # una consulta más larga se recorta antes de buscar
MAX_CHARS_TEXTO_CONFLICTO = 6000
MAX_CONFLICTOS_DETALLADOS = 5
MAX_LINEAS_POR_LADO = 12


class Herramienta:
    """Tool con docstring, esquema JSON para el LLM y .invoke() para pruebas."""

    def __init__(self, funcion, tipo: str, parametros: dict, requeridos: list[str]):
        self.funcion = funcion
        self.nombre = funcion.__name__
        self.tipo = tipo
        self.descripcion = " ".join((funcion.__doc__ or "").split())
        self.parametros = parametros
        self.requeridos = requeridos

    def invoke(self, args: dict) -> dict:
        return self.funcion(**args)

    def esquema(self) -> dict:
        """Formato de function calling que entiende Groq (compatible con OpenAI)."""
        return {
            "type": "function",
            "function": {
                "name": self.nombre,
                "description": self.descripcion,
                "parameters": {
                    "type": "object",
                    "properties": self.parametros,
                    "required": self.requeridos,
                    "additionalProperties": False,
                },
            },
        }


# ---------------------------------------------------------------------------
# 1. Búsqueda en la base de conocimientos
# ---------------------------------------------------------------------------
def buscar_en_base(consulta: str) -> dict:
    """Busca en la base de conocimientos local (documentación oficial de GitHub sobre
    autenticación SSH, conflictos de merge y pull requests). Úsala para CUALQUIER
    pregunta técnica sobre Git o GitHub. No la uses para saludos ni para conversación
    casual. Si la pregunta tiene dos temas, llámala una vez por tema, con una consulta
    completa y en español. Devuelve como máximo 4 fragmentos, cada uno con documento
    y página para poder citar."""
    from src.rag.retrieval import recuperar  # import perezoso: carga el modelo al primer uso

    consulta = (consulta or "").strip()[:MAX_CHARS_CONSULTA]
    if not consulta:
        return {"origen": "base", "fragmentos": [], "mensaje": "Consulta vacía."}

    fragmentos = []
    for f in recuperar(consulta, top_k=BASE_MAX_FRAGMENTOS):
        if f["distancia"] > UMBRAL_DISTANCIA:   # mismo filtro de relevancia del Avance 2
            continue
        fragmentos.append({
            "documento": f["documento"],
            "pagina": f["pagina"],
            "texto": f["texto"].strip()[:BASE_MAX_CHARS_FRAGMENTO],
            "distancia": f["distancia"],
        })
    fragmentos = fragmentos[:BASE_MAX_FRAGMENTOS]

    if not fragmentos:
        return {
            "origen": "base",
            "fragmentos": [],
            "mensaje": "SIN_RESULTADOS: la base de conocimientos no tiene información relevante para esta consulta.",
        }
    return {"origen": "base", "fragmentos": fragmentos}


# ---------------------------------------------------------------------------
# 2. Tareas del dominio (lo que el LLM no debe hacer «de memoria»)
# ---------------------------------------------------------------------------
_INICIO = re.compile(r"^<{7}(?: (.*))?$")
_SEPARADOR = re.compile(r"^={7}$")
_FIN = re.compile(r"^>{7}(?: (.*))?$")


def analizar_conflicto_merge(texto_archivo: str) -> dict:
    """Analiza el contenido de un archivo con marcadores de conflicto de merge
    (<<<<<<<, =======, >>>>>>>). Cuenta los conflictos, indica a qué rama pertenece cada
    lado y devuelve las líneas de cada versión. Úsala cuando el usuario PEGUE el texto de
    un archivo en conflicto; no la uses para explicar conceptos en general."""
    texto = (texto_archivo or "")[:MAX_CHARS_TEXTO_CONFLICTO]
    estado, actual, conflictos = "fuera", None, []

    for n, linea in enumerate(texto.splitlines(), start=1):
        linea = linea.rstrip()
        if estado == "fuera":
            m = _INICIO.match(linea)
            if m:
                actual = {"linea_inicio": n, "rama_actual": (m.group(1) or "HEAD").strip(),
                          "rama_entrante": None, "version_actual": [], "version_entrante": []}
                estado = "actual"
        elif estado == "actual":
            if _SEPARADOR.match(linea):
                estado = "entrante"
            else:
                actual["version_actual"].append(linea)
        elif estado == "entrante":
            m = _FIN.match(linea)
            if m:
                actual["rama_entrante"] = (m.group(1) or "").strip()
                actual["linea_fin"] = n
                conflictos.append(actual)
                actual, estado = None, "fuera"
            else:
                actual["version_entrante"].append(linea)

    incompleto = estado != "fuera"
    if not conflictos and not incompleto:
        return {"origen": "tarea", "total_conflictos": 0,
                "mensaje": "No se encontraron marcadores de conflicto en el texto."}

    detalle = []
    for c in conflictos[:MAX_CONFLICTOS_DETALLADOS]:
        detalle.append({
            "lineas": f'{c["linea_inicio"]}-{c["linea_fin"]}',
            "rama_actual": c["rama_actual"],
            "rama_entrante": c["rama_entrante"],
            "version_actual": c["version_actual"][:MAX_LINEAS_POR_LADO],
            "version_entrante": c["version_entrante"][:MAX_LINEAS_POR_LADO],
            "solo_un_lado_tiene_cambios": not c["version_actual"] or not c["version_entrante"],
        })
    resultado = {"origen": "tarea", "total_conflictos": len(conflictos), "detalle": detalle}
    if len(conflictos) > MAX_CONFLICTOS_DETALLADOS:
        resultado["nota"] = f"Se muestran solo los primeros {MAX_CONFLICTOS_DETALLADOS} conflictos."
    if incompleto:
        resultado["advertencia"] = "El texto termina con un bloque de conflicto sin cerrar (faltan marcadores)."
    return resultado


def validar_nombre_rama(nombre: str) -> dict:
    """Valida un nombre de rama (o de etiqueta) de Git con las reglas exactas de
    `git check-ref-format` y lista cada regla que incumple. Úsala cuando el usuario
    pregunte si un nombre de rama es válido o por qué Git lo rechaza."""
    nombre = (nombre or "")[:250]
    problemas = []

    if not nombre.strip():
        problemas.append("El nombre está vacío.")
    else:
        if nombre != nombre.strip():
            problemas.append("Tiene espacios al inicio o al final.")
        if " " in nombre.strip():
            problemas.append("Contiene espacios.")
        if any(ord(c) < 32 or ord(c) == 127 for c in nombre):
            problemas.append("Contiene caracteres de control.")
        for c in "~^:?*[\\":
            if c in nombre:
                problemas.append(f"Contiene el carácter prohibido «{c}».")
        if ".." in nombre:
            problemas.append("Contiene «..» (dos puntos seguidos).")
        if "@{" in nombre:
            problemas.append("Contiene «@{».")
        if nombre == "@":
            problemas.append("El nombre no puede ser solo «@».")
        if nombre.startswith("/") or nombre.endswith("/") or "//" in nombre:
            problemas.append("No puede empezar o terminar con «/» ni contener «//».")
        if nombre.endswith("."):
            problemas.append("No puede terminar en «.».")
        if nombre.startswith("-"):
            problemas.append("No puede empezar con «-».")
        for parte in nombre.split("/"):
            if parte.startswith("."):
                problemas.append(f"El componente «{parte}» empieza con «.».")
            if parte.endswith(".lock"):
                problemas.append(f"El componente «{parte}» termina en «.lock».")

    return {"origen": "tarea", "nombre": nombre, "valido": not problemas,
            "problemas": list(dict.fromkeys(problemas))}


# ---------------------------------------------------------------------------
# 3. Búsqueda web controlada
# ---------------------------------------------------------------------------
def _host_permitido(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in WEB_SITIOS_PERMITIDOS)


def buscar_en_web(consulta: str) -> dict:
    """Busca en la web, SOLO en sitios oficiales (docs.github.com, git-scm.com, github.blog,
    githubstatus.com). Úsala únicamente cuando buscar_en_base no tenga la respuesta Y la
    pregunta trate de información pública o actual de Git/GitHub (una versión reciente,
    una definición general, el estado del servicio). Nunca la uses para saludos, para
    temas ajenos a Git/GitHub ni antes de consultar la base. Escribe la consulta con
    palabras generales: no incluyas datos del usuario ni contenido de la base."""
    consulta = (consulta or "").strip()[:MAX_CHARS_CONSULTA]
    if not consulta:
        return {"origen": "web", "resultados": [], "mensaje": "Consulta vacía."}
    if not TAVILY_API_KEY:
        return {"origen": "web", "resultados": [],
                "mensaje": "ERROR: la búsqueda web no está configurada (falta TAVILY_API_KEY)."}

    try:
        r = httpx.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {TAVILY_API_KEY}"},
            json={
                "query": consulta,
                "max_results": WEB_MAX_RESULTADOS,
                "include_domains": WEB_SITIOS_PERMITIDOS,   # fijo: el LLM no lo controla
                "search_depth": "basic",
                "include_answer": False,
            },
            timeout=20,
        )
        r.raise_for_status()
        crudos = r.json().get("results", [])
    except Exception as e:  # red caída, clave inválida, límite del plan...
        return {"origen": "web", "resultados": [], "mensaje": f"ERROR: no se pudo consultar la web ({type(e).__name__})."}

    resultados = []
    for item in crudos:
        url = item.get("url", "")
        if not _host_permitido(url):    # segunda barrera, por si el servicio devolviera otro sitio
            continue
        resultados.append({
            "origen": "web",
            "titulo": (item.get("title") or "")[:150],
            "url": url,
            "extracto": " ".join((item.get("content") or "").split())[:WEB_MAX_CHARS_EXTRACTO],
        })
    resultados = resultados[:WEB_MAX_RESULTADOS]

    if not resultados:
        return {"origen": "web", "resultados": [],
                "mensaje": "SIN_RESULTADOS: no hay resultados en los sitios permitidos."}
    return {"origen": "web", "resultados": resultados}


# ---------------------------------------------------------------------------
# Registro de tools
# ---------------------------------------------------------------------------
HERRAMIENTAS = {h.nombre: h for h in [
    Herramienta(
        buscar_en_base, "búsqueda",
        {"consulta": {"type": "string", "description": "Consulta completa en español sobre un solo tema."}},
        ["consulta"],
    ),
    Herramienta(
        analizar_conflicto_merge, "tarea",
        {"texto_archivo": {"type": "string", "description": "Texto del archivo en conflicto, tal como lo pegó el usuario."}},
        ["texto_archivo"],
    ),
    Herramienta(
        validar_nombre_rama, "tarea",
        {"nombre": {"type": "string", "description": "Nombre de la rama a validar, exactamente como lo escribió el usuario."}},
        ["nombre"],
    ),
    Herramienta(
        buscar_en_web, "web",
        {"consulta": {"type": "string", "description": "Consulta general en español o inglés, sin datos personales."}},
        ["consulta"],
    ),
]}


def esquemas() -> list[dict]:
    return [h.esquema() for h in HERRAMIENTAS.values()]


if __name__ == "__main__":
    # Prueba de las tools SIN LLM (esto es lo que se captura para el informe)
    import json
    print(json.dumps(buscar_en_base("Permission denied (publickey) al hacer git push"), indent=2, ensure_ascii=False)[:1800])
