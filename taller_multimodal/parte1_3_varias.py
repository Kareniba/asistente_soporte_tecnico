"""1.3 Varias imágenes relacionadas en una misma solicitud (máximo 3)."""
from comun import IMAGENES, RESULTADOS, crear_cliente, preguntar

IMAGENES_ENVIADAS = [IMAGENES / "img6_academico_p55.png", IMAGENES / "img5_trabajo_p47.png"]
PREGUNTA = (
    "La primera imagen es del Reglamento Académico (estudiantes) y la segunda del Reglamento "
    "Interno de Trabajo (trabajadores). Compara cómo cada uno trata las sanciones y los recursos "
    "que se pueden presentar contra ellas: instancias, plazos y diferencias principales."
)

if __name__ == "__main__":
    cliente = crear_cliente()
    print("Imágenes:", ", ".join(i.name for i in IMAGENES_ENVIADAS))
    print(f"Pregunta: {PREGUNTA}\n")
    respuesta = preguntar(cliente, PREGUNTA, IMAGENES_ENVIADAS)
    print("Respuesta del modelo:\n" + respuesta)
    (RESULTADOS / "1_3_varias.txt").write_text(
        f"Imágenes: {[i.name for i in IMAGENES_ENVIADAS]}\nPregunta: {PREGUNTA}\n\nRespuesta:\n{respuesta}\n",
        encoding="utf-8")
