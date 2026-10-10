# GitBot — Asistente experto de soporte técnico de Git/GitHub (RAG)

Proyecto de **Desarrollo de Aplicaciones con IA** · Avance 2: flujo RAG completo, evaluación con Ragas y despliegue conversacional.



## ¿Qué hace?

GitBot responde en español preguntas de soporte técnico sobre **autenticación SSH, conflictos de merge y pull requests**, usando únicamente la documentación oficial de GitHub indexada en una base vectorial propia. Cada respuesta cita el documento y el fragmento que la respalda, y cuando la pregunta no está cubierta por la base de conocimientos lo dice en lugar de inventar.

Privacidad: el corpus y el índice vectorial se mantienen en el proyecto (carpeta `chroma_db/`). Al modelo de lenguaje solo se le envían los fragmentos recuperados para cada consulta, nunca el corpus completo.

## Flujo RAG implementado
<img width="2016" height="1202" alt="image" src="https://github.com/user-attachments/assets/a9919227-b282-4e4b-b632-cd1207c4e924" />


| Etapa | Archivo | Decisión técnica |
|---|---|---|
| Corpus | `data/docs/` | 31 documentos de GitHub Docs (Markdown) sobre troubleshooting de SSH, conflictos de merge y pull requests. |
| Ingesta | `src/rag/ingesta.py` | Lectores para PDF, DOCX, TXT/MD y HTML. En los `.md` se limpian el front matter, las etiquetas Liquid y los enlaces. |
| Chunking | `src/rag/chunking.py` | `RecursiveCharacterTextSplitter`, 800 caracteres con solapamiento de 120; corta por párrafo, luego línea, frase y palabra. Resultado: 98 chunks (media de 600 caracteres). |
| Embeddings | `src/rag/embeddings.py` | `paraphrase-multilingual-MiniLM-L12-v2` con fastembed (sin PyTorch). Es multilingüe: los documentos están en inglés y las preguntas en español. |
| Índice | `src/rag/vectorstore.py` | Chroma persistente (`chroma_db/`), colección `gitbot_docs`, distancia coseno. Metadatos: `documento` y `pagina`. |
| Recuperación | `src/rag/retrieval.py` | Similitud coseno, `top_k = 4`. |
| Control de alucinaciones | `src/rag/pipeline.py` | Si el mejor fragmento tiene distancia > 0.6 no se llama al LLM; además el LLM marca `en_contexto: false` cuando el contexto no alcanza. |
| Seguimientos | `src/rag/generacion.py` | Antes de buscar, el LLM reescribe la pregunta de seguimiento como pregunta completa usando los últimos 6 mensajes. |
| Generación | `src/rag/prompt.py`, `generacion.py` | Groq `openai/gpt-oss-120b`, temperatura 0.1. System prompt + 3 ejemplos few-shot + historial + contexto numerado en etiquetas XML (`<contexto>`, `<fragmento>`, `<pregunta>`). Salida JSON: `en_contexto`, `diagnostico`, `solucion`, `nivel_confianza`, `fuentes_usadas`. |

## Evaluación con Ragas

Conjunto de 18 preguntas (`evaluacion/preguntas_eval.json`): 14 dentro del corpus con respuesta de referencia y 4 fuera del corpus. Juez: `openai/gpt-oss-120b` en Groq. Las preguntas fuera del corpus se miden aparte con la tasa de rechazo.

| Métrica | Baseline (`top_k=4`) | Iteración de mejora |
|---|---|---|
| faithfulness | 0.885 | `PENDIENTE` |
| answer_relevancy | 0.762 | `PENDIENTE` |
| context_precision | 0.732 | `PENDIENTE` |
| context_recall | 0.899 | `PENDIENTE` |
| Rechazo fuera del corpus | 4/4 | `PENDIENTE` |

El análisis completo y la iteración de mejora están en el PDF de entrega.

## Instalación y ejecución local

```bash
git clone <URL-DEL-REPOSITORIO>
cd asistente_soporte_tecnico
python -m venv .venv
# Windows: .venv\Scripts\activate    |  Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz (no se sube al repositorio):

```
GROQ_API_KEY=tu_clave_de_groq
```

El índice ya viene en `chroma_db/`. Para reconstruirlo desde `data/docs/`:

```bash
python -m src.rag.vectorstore
```

Probar el pipeline por consola y lanzar el chat:

```bash
python -m src.rag.pipeline
python app.py            # http://127.0.0.1:5000
```

## Evaluación (solo en tu equipo)

```bash
pip install -r requirements-eval.txt
python -m evaluacion.evaluar_ragas --etiqueta baseline
python -m evaluacion.evaluar_ragas --etiqueta topk3 --top-k 3 --regenerar
```

Los resultados quedan en `evaluacion/resultados/`. Ragas no se instala en el despliegue.

## Despliegue en Render

1. Subir el repositorio a GitHub con `chroma_db/` incluido (no debe estar en `.gitignore`).
2. En Render: **New → Web Service**, conectar el repositorio.
3. Configuración:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --workers 1 --timeout 120`
   - **Environment:** `GROQ_API_KEY` = la clave de Groq y `PYTHON_VERSION` = `3.12.3` (o la versión estable que se use).
4. La clave nunca se escribe en el código ni en el repositorio: solo en las variables de entorno de Render.

Nota: en el plan gratuito el servicio se duerme tras unos minutos sin uso y la primera visita tarda en responder (carga el modelo de embeddings).

## Estructura

```
app.py                 # servidor Flask del chat
templates/, static/    # interfaz web
src/rag/               # pipeline RAG (ingesta, chunking, embeddings, índice, recuperación, prompt, generación)
data/docs/             # corpus
chroma_db/             # índice vectorial persistente
evaluacion/            # preguntas, script de Ragas y resultados
docs/                  # diagrama del flujo
```

