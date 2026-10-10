# streamlit_app.py
try:  # chromadb necesita un sqlite más nuevo en Streamlit Cloud
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import os

import streamlit as st

try:  # la clave sale de los Secrets de la plataforma, nunca del repo
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

from src.rag.pipeline import responder  # después de fijar la variable de entorno

st.set_page_config(page_title="GitBot", page_icon="🤖")
st.title("GitBot: soporte técnico de Git y GitHub")
st.caption("Pregunta sobre errores de SSH, conflictos de merge y pull requests. Puedes hacer preguntas de seguimiento.")

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []


def mostrar_fuentes(fuentes):
    if fuentes:
        with st.expander("Fuentes"):
            for f in fuentes:
                st.markdown(f"**{f['documento']}** (p. {f['pagina']})")
                st.caption(f["fragmento"][:300])


for m in st.session_state.mensajes:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        mostrar_fuentes(m.get("fuentes"))

pregunta = st.chat_input("Escribe tu pregunta...")
if pregunta:
    historial = [{"role": m["role"], "content": m["content"]} for m in st.session_state.mensajes]
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)
    with st.chat_message("assistant"):
        with st.spinner("Buscando en la documentación..."):
            r = responder(pregunta, historial)
        st.markdown(r["respuesta"])
        mostrar_fuentes(r["fuentes"])
    st.session_state.mensajes.append(
        {"role": "assistant", "content": r["respuesta"], "fuentes": r["fuentes"]}
    )