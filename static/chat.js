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


function buildDetails(summaryText, className) {
    const details = document.createElement("details");
    details.className = className;
    const summary = document.createElement("summary");
    summary.textContent = summaryText;
    details.appendChild(summary);
    return details;
}


function addMessage(role, content, extras = {}) {
    const tools = Array.isArray(extras.tools) ? extras.tools : [];
    const sourcesBase = Array.isArray(extras.sourcesBase) ? extras.sourcesBase : [];
    const sourcesWeb = Array.isArray(extras.sourcesWeb) ? extras.sourcesWeb : [];

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

    if (role === "assistant") {
        // Tools usadas y argumentos (solo en respuestas del agente, no en bienvenida/errores)
        if (Array.isArray(extras.tools)) {
        const toolsBox = buildDetails(
            tools.length > 0
                ? `Tools usadas (${tools.length})`
                : "Tools usadas: ninguna",
            "tools-used"
        );
        tools.forEach((tool) => {
            const item = document.createElement("div");
            item.className = "tool-item";

            const name = document.createElement("div");
            name.className = "tool-name";
            name.textContent = tool.name;

            const args = document.createElement("code");
            args.className = "tool-args";
            args.textContent = JSON.stringify(tool.args);

            const summary = document.createElement("p");
            summary.className = "source-snippet";
            summary.textContent = tool.summary || "";

            item.append(name, args, summary);
            toolsBox.appendChild(item);
        });
        article.appendChild(toolsBox);
        }

        // Fuentes de la base de conocimientos
        if (sourcesBase.length > 0) {
            const section = document.createElement("section");
            section.className = "sources";
            const heading = document.createElement("h3");
            heading.textContent = "Fuentes de la base de conocimientos";
            section.appendChild(heading);

            sourcesBase.forEach((source) => {
                const item = document.createElement("div");
                item.className = "source-item";

                const documentName = document.createElement("div");
                documentName.className = "source-document";
                documentName.textContent =
                    `${source.document || "Documento"} (pág. ${source.page ?? "?"})`;

                item.appendChild(documentName);
                if (source.snippet) {
                    const snippet = document.createElement("p");
                    snippet.className = "source-snippet";
                    snippet.textContent = source.snippet;
                    item.appendChild(snippet);
                }
                section.appendChild(item);
            });
            article.appendChild(section);
        }

        // Resultados de la web (se muestran aparte, marcados como web)
        if (sourcesWeb.length > 0) {
            const section = document.createElement("section");
            section.className = "sources sources-web";
            const heading = document.createElement("h3");
            heading.textContent = "Resultados de la web";
            section.appendChild(heading);

            sourcesWeb.forEach((source) => {
                const item = document.createElement("div");
                item.className = "source-item";

                const link = document.createElement("a");
                link.className = "source-document";
                link.href = source.url;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.textContent = `[web] ${source.title || source.url}`;

                const url = document.createElement("p");
                url.className = "source-snippet";
                url.textContent = source.url;

                item.append(link, url);
                section.appendChild(item);
            });
            article.appendChild(section);
        }
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
        const response = await fetch("/api/chat", {
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

        addMessage("assistant", answer, {
            tools: data.tools,
            sourcesBase: data.sources_base,
            sourcesWeb: data.sources_web
        });

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