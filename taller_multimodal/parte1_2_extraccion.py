"""1.2 Extracción estructurada (JSON validado) de capturas de errores de Git y comparación con los valores reales."""
import json
from typing import Literal, Optional

from pydantic import BaseModel, ValidationError

from comun import CARPETA, IMAGENES, RESULTADOS, crear_cliente, preguntar


class ErrorGit(BaseModel):
    """Esquema de extracción: 6 campos de una captura de terminal con un error de Git/SSH."""
    comando_ejecutado: str                       # comando que produce el error
    mensaje_error: str                           # línea principal del error o aviso
    tipo_error: Literal["conflicto_de_merge", "autenticacion_ssh", "remoto_no_configurado", "otro"]
    recurso_afectado: Optional[str] = None       # archivo, host o remoto mencionado en el error (null si no hay)
    relacionado_con_ssh: bool                    # el error es de autenticación/conexión SSH
    sugiere_solucion: bool                       # la propia pantalla indica cómo solucionarlo


PROMPT = """Analiza esta captura de una terminal con un error de Git y devuelve ÚNICAMENTE un JSON con estos campos:
- comando_ejecutado (string): el comando cuyo resultado muestra el error (no los comandos de preparación anteriores).
- mensaje_error (string): la línea principal del error o aviso, copiada tal cual aparece.
- tipo_error (string): exactamente uno de "conflicto_de_merge", "autenticacion_ssh", "remoto_no_configurado" u "otro".
- recurso_afectado (string o null): el archivo, host o remoto que menciona el error; null si no menciona ninguno.
- relacionado_con_ssh (booleano): true si el error es de autenticación o conexión SSH.
- sugiere_solucion (booleano): true si la propia pantalla indica cómo solucionarlo.
No agregues texto fuera del JSON."""

CAMPOS = list(ErrorGit.model_fields)


def normalizar(valor):
    if valor is None:
        return None
    return str(valor).strip().lower().rstrip(".")


def coincide(real, extraido):
    """None solo coincide con None; los textos coinciden si son iguales o uno contiene al otro."""
    r, e = normalizar(real), normalizar(extraido)
    if r is None or e is None:
        return r is e
    return r == e or r in e or e in r


if __name__ == "__main__":
    cliente = crear_cliente()
    reales = json.loads((CARPETA / "valores_reales.json").read_text(encoding="utf-8"))
    filas, aciertos, total = [], 0, 0

    for prefijo, real in reales.items():
        imagen = next(IMAGENES.glob(f"{prefijo}*.png"))
        print(f"\n=== {imagen.name} ===")
        crudo = preguntar(cliente, PROMPT, [imagen], response_format={"type": "json_object"})
        print("Respuesta cruda:", crudo)

        # Validación: si el JSON no cumple el esquema se informa y se sigue con la siguiente imagen
        try:
            extraido = ErrorGit.model_validate_json(crudo).model_dump()
        except ValidationError as e:
            print(f"[JSON INVÁLIDO] {imagen.name}: {e.error_count()} error(es) de esquema")
            for err in e.errors():
                print(f"   - {err['loc']}: {err['msg']}")
            total += len(CAMPOS)  # todos los campos cuentan como no acertados
            continue

        for campo in CAMPOS:
            ok = coincide(real[campo], extraido[campo])
            aciertos += ok
            total += 1
            filas.append({"imagen": imagen.name, "campo": campo, "real": real[campo],
                          "extraido": extraido[campo], "correcto": ok})
            print(f"  {campo:20} real={str(real[campo])!r:55} extraído={str(extraido[campo])!r:55} {'OK' if ok else 'NO'}")

    pct = 100 * aciertos / total if total else 0
    print(f"\nAciertos: {aciertos} de {total} campos = {pct:.1f} %")
    (RESULTADOS / "1_2_extraccion.json").write_text(
        json.dumps({"filas": filas, "aciertos": aciertos, "total": total, "porcentaje": pct},
                   ensure_ascii=False, indent=2), encoding="utf-8")
