# Taller: entrada multimodal y audio

Proveedor: Groq. Modelo de visión `qwen/qwen3.8-27b`, audio `whisper-large-v3-turbo`, texto `openai/gpt-oss-20b`.

## Preparación
    pip install -r requirements.txt
    copy .env.example .env      (en Linux/Mac: cp .env.example .env)

Edite `.env` y ponga su clave en `GROQ_API_KEY`. No suba `.env` al repositorio (está en `.gitignore`).

Variables de entorno: `GROQ_API_KEY` (obligatoria), `MODELO_VISION`, `MODELO_AUDIO`, `MODELO_TEXTO` (opcionales, con valores por defecto).

## Parte 1: visión (carpeta imagenes/)
- 1.1 Pregunta sobre una imagen: `python parte1_1_pregunta.py`
- 1.2 Extracción estructurada (valida el JSON y compara con valores_reales.json): `python parte1_2_extraccion.py`
- 1.3 Varias imágenes en una solicitud: `python parte1_3_varias.py`
- 1.4 Error provocado: `python parte1_4_error.py muchas` (también `mime` o `sin_vision`)

## Parte 2: audio (carpeta audios/, archivos .m4a)
- 2.1 Transcripción desde archivo: `python parte2_1_transcripcion.py`
- 2.2 Respuesta del modelo a partir de la transcripción: `python parte2_2_respuesta.py` (después de 2.1)

Los resultados de cada ejecución quedan en `resultados/`.
