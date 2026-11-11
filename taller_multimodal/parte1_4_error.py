"""1.4 Error provocado a propósito. Uso: python parte1_4_error.py [muchas|mime|sin_vision]"""
import sys

import groq

from comun import IMAGENES, RESULTADOS, crear_cliente, preguntar

CASOS = {
    # 4 imágenes: el máximo del modelo es 3 por solicitud
    "muchas": dict(imagenes=sorted(IMAGENES.glob("err[1-4]*.png")), mime=None, modelo=None),
    # Un PNG declarado como JPEG
    "mime": dict(imagenes=[next(IMAGENES.glob("err1*.png"))], mime="image/jpeg", modelo=None),
    # Un modelo de solo texto recibiendo una imagen
    "sin_vision": dict(imagenes=[next(IMAGENES.glob("err1*.png"))], mime=None, modelo="llama-3.1-8b-instant"),
}

if __name__ == "__main__":
    caso = sys.argv[1] if len(sys.argv) > 1 else "muchas"
    if caso not in CASOS:
        raise SystemExit(f"Caso inválido. Opciones: {', '.join(CASOS)}")
    cfg = CASOS[caso]
    cliente = crear_cliente()
    print(f"Caso: {caso} | imágenes enviadas: {len(cfg['imagenes'])} | modelo: {cfg['modelo'] or 'el de visión por defecto'}")
    try:
        r = preguntar(cliente, "Describe brevemente estas imágenes.", cfg["imagenes"],
                      mime=cfg["mime"], modelo=cfg["modelo"])
        print("No hubo error. Respuesta:", r[:300])
    except groq.APIStatusError as e:
        texto = f"Código HTTP: {e.status_code}\nTipo: {type(e).__name__}\nMensaje: {e.message}"
        print("\n[ERROR DE LA API]\n" + texto)
        (RESULTADOS / f"1_4_error_{caso}.txt").write_text(texto + "\n", encoding="utf-8")
