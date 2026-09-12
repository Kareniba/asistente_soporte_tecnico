# GitBot — Asistente Experto de Soporte Técnico (Git/GitHub)

Proyecto para la materia **Desarrollo de Aplicaciones con IA** (26-II 56BA1A)
**Avance 1**: Diseño de Prompts, Few-Shot Prompting y Delimitadores

## Descripción

GitBot es un asistente de IA especializado en **soporte técnico de Git y
GitHub**: comandos, autenticación (SSH/HTTPS), conflictos de merge, Pull
Requests y errores comunes del flujo de trabajo con repositorios. Está
pensado como el primer paso hacia un sistema completo basado en RAG
(Retrieval-Augmented Generation), donde el asistente podrá "leer" la
documentación oficial de GitHub para responder preguntas técnicas con base
en esa fuente, sin inventar información.

Este avance se enfoca únicamente en la **estructuración del prompt**: cómo
se le indica al modelo su rol, cómo se le muestran ejemplos del formato
esperado, y cómo se separa el contexto (manual/documentación) de la
pregunta del usuario. No incluye conexión ni integración con ningún modelo
LLM por código; el prompt fue diseñado y probado manualmente en la interfaz
web de un chatbot.

## Enfoque elegido

**Analista de Soporte Técnico**, basado en instructivos y documentación de
Git/GitHub.

## Arquitectura del prompt

### 1. System Prompt
Define el rol del asistente (soporte técnico exclusivo de Git/GitHub), sus
reglas de comportamiento (no inventar comandos fuera del contexto
entregado, no responder temas ajenos a Git/GitHub) y el formato de salida
obligatorio en JSON.

### 2. Few-Shot Prompting
Se incluyen dos ejemplos completos de pregunta/respuesta, para que el
modelo aprenda a replicar exactamente el formato JSON esperado
(`diagnostico`, `solucion`, `nivel_confianza`, `fuente`).

### 3. Delimitadores
Cada pregunta del usuario se envía junto con su contexto (fragmento de la
documentación) separados con etiquetas XML `<contexto>` y `<pregunta>`,
evitando que el modelo confunda datos de referencia con instrucciones.

## Formato de salida

```json
{
  "diagnostico": "breve interpretación del problema",
  "solucion": ["paso 1", "paso 2"],
  "nivel_confianza": "alto | medio | bajo",
  "fuente": "parte del manual usada, o 'no encontrado en el contexto'"
}
```

## Evidencia de ejecución

La prueba del prompt (System Prompt + ejemplos few-shot + una pregunta con
su contexto delimitado) se realizó manualmente copiando y pegando el
contenido de `prompts/system_prompt.py` en la interfaz web de un chatbot
(Gemini). Las capturas de pantalla de esas pruebas y su explicación se
encuentran en el archivo PDF entregado junto con este repositorio.

