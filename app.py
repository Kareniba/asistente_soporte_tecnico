
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

MAX_HISTORY_MESSAGES = 20
MAX_QUESTION_LENGTH = 2000


def generate_answer(question, history):
    """
    Conecta Flask con el pipeline RAG existente.
    No modifica src/rag/pipeline.py.
    """

    # Importación dentro de la función para no cargar el RAG
    # hasta que llegue la primera pregunta.
    from src.rag.pipeline import responder

    result = responder(
        pregunta=question,
        historial=history
    )

    # Adaptamos los nombres que devuelve el RAG a los que
    # utiliza nuestra interfaz JavaScript.
    sources = []

    for source in result.get("fuentes", []):
        sources.append({
            "document": source.get("documento", "Documento"),
            "snippet": source.get("fragmento", ""),
            "page": source.get("pagina")
        })

    return {
        "answer": result.get(
            "respuesta",
            "No se pudo generar una respuesta."
        ),
        "sources": sources,
        "en_contexto": result.get("en_contexto", False),
        "query": result.get("consulta", question)
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "La solicitud no contiene JSON válido."
        }), 400

    question = data.get("question", "")
    history = data.get("history", [])

    if not isinstance(question, str) or not question.strip():
        return jsonify({
            "error": "Escribe una pregunta antes de enviarla."
        }), 400

    question = question.strip()

    if len(question) > MAX_QUESTION_LENGTH:
        return jsonify({
            "error": "La pregunta supera el límite permitido."
        }), 400

    if not isinstance(history, list):
        return jsonify({
            "error": "El historial debe ser una lista."
        }), 400

    valid_history = []

    for message in history[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        content = message.get("content")

        if role in ("user", "assistant") and isinstance(content, str):
            valid_history.append({
                "role": role,
                "content": content[:5000]
            })

    try:
        result = generate_answer(question, valid_history)
        return jsonify(result)

    except Exception:
        app.logger.exception("Error al procesar la pregunta con el RAG")

        return jsonify({
            "error": (
                "No pude procesar tu pregunta. "
                "Revisa la configuración del RAG y sus dependencias."
            )
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
