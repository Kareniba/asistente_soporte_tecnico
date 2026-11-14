"""Pruebas sin red: tools puras y bucle del agente con un LLM falso. Ejecutar: python -m pytest tests -q"""
import json
from types import SimpleNamespace as NS

import src.agente.agente as ag
from src.agente.herramientas import HERRAMIENTAS


def _llamada(nombre, args, id_="c1"):
    return NS(id=id_, function=NS(name=nombre, arguments=json.dumps(args)))


def _resp(content=None, calls=None):
    return NS(choices=[NS(message=NS(content=content, tool_calls=calls))], usage=NS(total_tokens=10))


class ClienteFalso:
    def __init__(self, respuestas):
        self.respuestas, self.visto = list(respuestas), []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.visto.append(kw)
        return self.respuestas.pop(0)


def _parchear(monkeypatch, tmp_path, cliente):
    monkeypatch.setattr(ag, "_get_cliente", lambda: cliente)
    monkeypatch.setattr(ag, "RUTA_LOG_TOOLS", tmp_path / "log.jsonl")


def test_saludo_sin_tools(monkeypatch, tmp_path):
    c = ClienteFalso([_resp("¡Hola! ¿En qué te ayudo?")])
    _parchear(monkeypatch, tmp_path, c)
    r = ag.responder_agente("Hola")
    assert r["tools"] == [] and r["llamadas_llm"] == 1


def test_tool_de_tarea_y_log(monkeypatch, tmp_path):
    c = ClienteFalso([_resp(calls=[_llamada("validar_nombre_rama", {"nombre": "a b"})]), _resp("No es válida: contiene espacios.")])
    _parchear(monkeypatch, tmp_path, c)
    r = ag.responder_agente("¿Es válida la rama 'a b'?")
    assert r["tools"][0]["nombre"] == "validar_nombre_rama" and r["llamadas_llm"] == 2
    linea = json.loads((tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert linea["tools"][0]["args"] == {"nombre": "a b"}


def test_web_bloqueada_sin_base(monkeypatch, tmp_path):
    c = ClienteFalso([_resp(calls=[_llamada("buscar_en_web", {"consulta": "x"})]), _resp(ag.MENSAJE_FUERA_DE_CORPUS)])
    _parchear(monkeypatch, tmp_path, c)
    r = ag.responder_agente("¿Última versión de Git?")
    contenido = [m for m in c.visto[1]["messages"] if m["role"] == "tool"][0]["content"]
    assert "BLOQUEADA" in contenido and r["en_contexto"] is False


def test_limite_de_iteraciones(monkeypatch, tmp_path):
    bucle = [_resp(calls=[_llamada("validar_nombre_rama", {"nombre": "x"}, f"c{i}")]) for i in range(ag.AGENTE_MAX_ITERACIONES - 1)]
    c = ClienteFalso(bucle + [_resp("Respuesta forzada")])
    _parchear(monkeypatch, tmp_path, c)
    r = ag.responder_agente("pregunta")
    assert r["llamadas_llm"] == ag.AGENTE_MAX_ITERACIONES and "tools" not in c.visto[-1]


def test_tool_inexistente_y_args_malos(monkeypatch, tmp_path):
    c = ClienteFalso([_resp(calls=[_llamada("borrar_todo", {}), _llamada("validar_nombre_rama", {"x": 1}, "c2")]), _resp("ok")])
    _parchear(monkeypatch, tmp_path, c)
    assert ag.responder_agente("hola")["respuesta"] == "ok"


def test_conflicto_y_ramas():
    t = "<<<<<<< HEAD\na\n=======\nb\n>>>>>>> dev\n"
    assert HERRAMIENTAS["analizar_conflicto_merge"].invoke({"texto_archivo": t})["total_conflictos"] == 1
    assert not HERRAMIENTAS["validar_nombre_rama"].invoke({"nombre": "a..b"})["valido"]
    assert HERRAMIENTAS["validar_nombre_rama"].invoke({"nombre": "feature/ok"})["valido"]


def test_reintento_si_el_modelo_escribe_mal_la_tool(monkeypatch, tmp_path):
    class Falla(ClienteFalso):
        def _create(self, **kw):
            self.visto.append(kw)
            r = self.respuestas.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

    mal = Exception("Error code: 400 - tool_use_failed: attempted to call tool 'analisar_conflicto_merge'")
    c = Falla([mal, _resp("Listo")])
    _parchear(monkeypatch, tmp_path, c)
    r = ag.responder_agente("pega un archivo")
    assert r["respuesta"] == "Listo" and r["llamadas_llm"] == 2
    assert "nombres exactos" in c.visto[1]["messages"][-1]["content"]
