from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

MAX_HISTORY_MESSAGES = 20


def generate_answer(question, history):
    """
    Respuesta temporal para probar la interfaz y el historial.

    IMPORTANTE:
    Esta función se conectará al sistema RAG cuando esté
    disponible el código de tu compañera. No modifica pipeline.py.
    """

    previous_messages = len(history)

    return {
        "answer": (
            "Prueba de GitBot: recibí tu pregunta correctamente. "
            f"También recibí {previous_messages} mensajes anteriores. "
            "El motor RAG todavía debe conectarse para generar "
            "respuestas basadas en la documentación."
        ),
        "sources": []
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "La solicitud no contiene JSON válido."}), 400

    question = data.get("question", "")
    history = data.get("history", [])

    if not isinstance(question, str) or not question.strip():
        return jsonify({"error": "Escribe una pregunta antes de enviarla."}), 400

    if not isinstance(history, list):
        return jsonify({"error": "El historial debe ser una lista."}), 400

    # Conservamos únicamente los últimos mensajes válidos.
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

    # Aquí se conectará posteriormente el sistema RAG.
    result = generate_answer(question.strip(), valid_history)

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)