# streamlit_app.py
try:  # chromadb necesita un sqlite más nuevo en Streamlit Cloud
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import json
import os

import streamlit as st

for clave in ("GROQ_API_KEY", "TAVILY_API_KEY"):  # las claves salen de los Secrets de la plataforma, nunca del repo
    try:
        os.environ[clave] = st.secrets[clave]
    except Exception:
        pass

from src.agente.agente import responder_agente  # después de fijar las variables de entorno

st.set_page_config(page_title="GitBot", page_icon="🤖")
st.title("GitBot: soporte técnico de Git y GitHub")
st.caption("Agente con herramientas: busca en la base de conocimientos, usa tareas del dominio y, solo si hace falta, la web oficial.")

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []


def mostrar_detalles(m):
    """Tools usadas con sus argumentos y fuentes separadas por origen."""
    tools = m.get("tools")
    if tools is not None:
        with st.expander(f"Tools usadas ({len(tools)})" if tools else "Tools usadas: ninguna"):
            for t in tools:
                st.markdown(f"**{t['nombre']}**")
                st.code(json.dumps(t["args"], ensure_ascii=False), language="json")
                st.caption(t["resumen"])
    if m.get("fuentes_base"):
        with st.expander("Fuentes de la base de conocimientos"):
            for f in m["fuentes_base"]:
                st.markdown(f"**{f['documento']}** (pág. {f['pagina']})")
                st.caption(f["fragmento"][:300])
    if m.get("fuentes_web"):
        with st.expander("Resultados de la web"):
            for w in m["fuentes_web"]:
                st.markdown(f"[web] [{w['titulo'] or w['url']}]({w['url']})")
                st.caption(w["url"])


for m in st.session_state.mensajes:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            mostrar_detalles(m)

pregunta = st.chat_input("Escribe tu pregunta...")
if pregunta:
    historial = [{"role": m["role"], "content": m["content"]} for m in st.session_state.mensajes]
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)
    with st.chat_message("assistant"):
        with st.spinner("El agente está decidiendo qué herramientas usar..."):
            try:
                r = responder_agente(pregunta, historial)
            except Exception:
                r = {"respuesta": "No pude procesar tu pregunta. Revisa las claves y la configuración del agente.",
                     "tools": [], "fuentes_base": [], "fuentes_web": []}
        st.markdown(r["respuesta"])
        mensaje = {"role": "assistant", "content": r["respuesta"], "tools": r["tools"],
                   "fuentes_base": r["fuentes_base"], "fuentes_web": r["fuentes_web"]}
        mostrar_detalles(mensaje)
    st.session_state.mensajes.append(mensaje)
