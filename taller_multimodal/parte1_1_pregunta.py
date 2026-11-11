"""1.1 Pregunta sobre una imagen local (base64): captura de un error real de Git."""
from comun import IMAGENES, RESULTADOS, crear_cliente, preguntar

IMAGEN = next(IMAGENES.glob("err1*.png"))
PREGUNTA = (
    "Un usuario le envía a un asistente de soporte técnico de Git esta captura de su terminal. "
    "¿Qué error muestra, qué significa y qué debería hacer para resolverlo? "
    "Responde en español con pasos numerados y deja los comandos tal como aparecen."
)

if __name__ == "__main__":
    cliente = crear_cliente()
    print(f"Imagen:   {IMAGEN.name}")
    print(f"Pregunta: {PREGUNTA}\n")
    respuesta = preguntar(cliente, PREGUNTA, [IMAGEN])
    print("Respuesta del modelo:\n" + respuesta)
    (RESULTADOS / "1_1_pregunta.txt").write_text(
        f"Imagen: {IMAGEN.name}\nPregunta: {PREGUNTA}\n\nRespuesta:\n{respuesta}\n", encoding="utf-8"
    )
