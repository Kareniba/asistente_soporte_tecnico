"""1.1 Pregunta sobre una imagen local (base64)."""
from comun import IMAGENES, RESULTADOS, crear_cliente, preguntar

IMAGEN = IMAGENES / "img2_academico_p19.png"
PREGUNTA = (
    "Según esta página del reglamento, ¿cuáles son las causales por las que "
    "se pierde la condición de estudiante? Enuméralas."
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
