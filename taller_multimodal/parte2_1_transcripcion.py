"""2.1 Transcripción de cada audio de la carpeta audios/ con Whisper (Groq)."""
import json

from comun import MODELO_AUDIO, RESULTADOS, crear_cliente, listar_audios


def transcribir(cliente, ruta):
    with open(ruta, "rb") as f:
        r = cliente.audio.transcriptions.create(
            file=(ruta.name, f.read()),
            model=MODELO_AUDIO,
            language="es",
            response_format="verbose_json",
            temperature=0,
        )
    duracion = getattr(r, "duration", None)
    if duracion is None and getattr(r, "segments", None):
        duracion = r.segments[-1]["end"] if isinstance(r.segments[-1], dict) else r.segments[-1].end
    return r.text.strip(), duracion


if __name__ == "__main__":
    cliente = crear_cliente()
    resultados = []
    for ruta in listar_audios():
        print(f"\n=== {ruta.name} ===")
        try:
            texto, duracion = transcribir(cliente, ruta)
        except Exception as e:  # informa el error y sigue con el siguiente audio
            print(f"[ERROR] {type(e).__name__}: {e}")
            continue
        print(f"Duración (s): {duracion}")
        print(f"Transcripción: {texto}")
        resultados.append({"audio": ruta.name, "duracion_s": duracion, "transcripcion": texto})

    (RESULTADOS / "2_1_transcripciones.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado en resultados/2_1_transcripciones.json ({len(resultados)} audios)")
