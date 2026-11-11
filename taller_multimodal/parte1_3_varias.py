"""1.3 Varias imágenes relacionadas en una misma solicitud (máximo 3)."""
from comun import IMAGENES, RESULTADOS, crear_cliente, preguntar

IMAGENES_ENVIADAS = [next(IMAGENES.glob("err1*.png")), next(IMAGENES.glob("err2*.png"))]
PREGUNTA = (
    "La primera imagen muestra el resultado de ejecutar un git merge en una terminal y la segunda "
    "el contenido del archivo afectado después del merge. ¿Qué relación hay entre ambas? "
    "Explica qué significan los marcadores <<<<<<<, ======= y >>>>>>> y qué pasos debe seguir el "
    "usuario para resolver el conflicto y terminar el merge."
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
