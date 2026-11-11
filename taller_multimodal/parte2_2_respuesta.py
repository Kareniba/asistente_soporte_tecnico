"""2.2 Respuesta del modelo a partir de la transcripción (flujo audio -> transcripción -> respuesta)."""
import json

from comun import MODELO_TEXTO, RESULTADOS, crear_cliente

SISTEMA = (
    "Eres un asistente de soporte técnico de Git y GitHub (SSH, conflictos de merge y pull requests). "
    "El texto del usuario es la "
    "transcripción automática de un audio y puede tener errores de reconocimiento. "
    "Responde en español, de forma breve y clara, con pasos y comandos exactos. Si no estás seguro de algún dato, "
    "dilo en lugar de inventarlo."
)

if __name__ == "__main__":
    ruta = RESULTADOS / "2_1_transcripciones.json"
    if not ruta.exists():
        raise SystemExit("Primero ejecute parte2_1_transcripcion.py")
    transcripciones = json.loads(ruta.read_text(encoding="utf-8"))
    cliente = crear_cliente()
    salida = []
    for t in transcripciones:
        print(f"\n=== {t['audio']} ===")
        print(f"Transcripción enviada: {t['transcripcion']}")
        r = cliente.chat.completions.create(
            model=MODELO_TEXTO,
            messages=[{"role": "system", "content": SISTEMA},
                      {"role": "user", "content": t["transcripcion"]}],
            temperature=0,
        )
        respuesta = r.choices[0].message.content
        print(f"Respuesta del modelo:\n{respuesta}")
        salida.append({**t, "respuesta": respuesta})
    (RESULTADOS / "2_2_respuestas.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
