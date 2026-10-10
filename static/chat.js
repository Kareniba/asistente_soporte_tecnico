const form = document.getElementById("chat-form");
const questionInput = document.getElementById("question");
const sendButton = document.getElementById("send-button");
const clearButton = document.getElementById("clear-chat");
const messagesContainer = document.getElementById("messages");
const statusContainer = document.getElementById("chat-status");

// Historial de la conversación actual.
// No incluye el mensaje inicial de bienvenida.
let history = [];
let sending = false;


function addMessage(role, content, sources = []) {
    const article = document.createElement("article");
    article.className = role === "user"
        ? "message user-message"
        : "message assistant-message";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = role === "user" ? "Tú" : "GitBot";

    const text = document.createElement("div");
    text.className = "message-content";
    text.textContent = content;

    article.append(label, text);

    if (role === "assistant" && Array.isArray(sources) && sources.length > 0) {
        const sourceSection = document.createElement("section");
        sourceSection.className = "sources";

        const heading = document.createElement("h3");
        heading.textContent = "Fuentes consultadas";
        sourceSection.appendChild(heading);

        sources.forEach((source) => {
            const item = document.createElement("div");
            item.className = "source-item";

            const documentName = document.createElement("div");
            documentName.className = "source-document";

            const snippet = document.createElement("p");
            snippet.className = "source-snippet";

            if (typeof source === "string") {
                documentName.textContent = source;
                snippet.textContent = "";
            } else {
                documentName.textContent =
                    source.document ||
                    source.filename ||
                    source.source ||
                    source.title ||
                    "Documento";

                snippet.textContent =
                    source.snippet ||
                    source.fragment ||
                    source.text ||
                    source.content ||
                    source.chunk ||
                    "";
            }

            item.appendChild(documentName);

            if (snippet.textContent) {
                item.appendChild(snippet);
            }

            sourceSection.appendChild(item);
        });

        article.appendChild(sourceSection);
    }

    messagesContainer.appendChild(article);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}


function showWelcomeMessage() {
    addMessage(
        "assistant",
        "¡Hola! Soy GitBot. Puedes preguntarme sobre Git y GitHub. " +
        "También puedes hacer preguntas de seguimiento dentro de esta conversación."
    );
}


form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const question = questionInput.value.trim();

    if (!question || sending) {
        return;
    }

    sending = true;
    sendButton.disabled = true;
    clearButton.disabled = true;
    questionInput.disabled = true;

    // Copiamos los mensajes anteriores antes de agregar la pregunta actual.
    const previousHistory = history.map((message) => ({ ...message }));

    addMessage("user", question);
    questionInput.value = "";
    statusContainer.textContent = "GitBot está preparando una respuesta...";

    try {
        // CORREGIDO: Se quitó el prefijo /api para conectar con Flask correctamente
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question,
                history: previousHistory
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "No se pudo procesar la pregunta.");
        }

        const answer = typeof data.answer === "string"
            ? data.answer
            : "No se recibió una respuesta válida del servidor.";

        const sources = Array.isArray(data.sources) ? data.sources : [];

        addMessage("assistant", answer, sources);

        // Guardamos ambos mensajes para las próximas preguntas.
        history.push(
            { role: "user", content: question },
            { role: "assistant", content: answer }
        );

    } catch (error) {
        addMessage(
            "assistant",
            `No pude comunicarme correctamente con el servidor. ${error.message}`
        );
    } finally {
        sending = false;
        sendButton.disabled = false;
        clearButton.disabled = false;
        questionInput.disabled = false;
        statusContainer.textContent = "";
        questionInput.focus();
    }
});


clearButton.addEventListener("click", () => {
    if (sending) {
        return;
    }

    history = [];
    messagesContainer.replaceChildren();
    showWelcomeMessage();
    statusContainer.textContent = "";
    questionInput.value = "";
    questionInput.focus();
});


// Enter envía el mensaje y Shift + Enter permite escribir varias líneas.
questionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
    }
});
