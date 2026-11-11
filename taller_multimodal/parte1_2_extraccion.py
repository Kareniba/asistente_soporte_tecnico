"""1.2 Extracción estructurada (JSON validado) y comparación con los valores reales."""
import json

from pydantic import BaseModel, ValidationError

from comun import CARPETA, IMAGENES, RESULTADOS, crear_cliente, preguntar


class PaginaReglamento(BaseModel):
    """Esquema de extracción: 6 campos de una página de reglamento."""
    documento: str            # nombre del reglamento
    primer_articulo: int      # número del primer ARTÍCULO que inicia en la página
    ultimo_articulo: int      # número del último ARTÍCULO que inicia en la página
    numero_paragrafos: int    # cantidad de PARÁGRAFOS que aparecen en la página
    nit_institucion: str      # NIT que aparece en el pie de página
    tema_principal: str       # tema principal de la página, en pocas palabras


PROMPT = """Analiza esta página de un reglamento institucional y devuelve ÚNICAMENTE un JSON con estos campos:
- documento (string): "Reglamento Académico Institucional" o "Reglamento Interno de Trabajo".
- primer_articulo (entero): número del primer ARTÍCULO cuyo encabezado inicia en la página.
- ultimo_articulo (entero): número del último ARTÍCULO cuyo encabezado inicia en la página.
- numero_paragrafos (entero): cantidad de PARÁGRAFOS que aparecen en la página (0 si no hay).
- nit_institucion (string): el NIT del pie de página.
- tema_principal (string): el tema principal de la página, en pocas palabras.
No agregues texto fuera del JSON."""

CAMPOS = list(PaginaReglamento.model_fields)


def normalizar(valor):
    return str(valor).strip().lower()


if __name__ == "__main__":
    cliente = crear_cliente()
    reales = json.loads((CARPETA / "valores_reales.json").read_text(encoding="utf-8"))
    filas, aciertos, total = [], 0, 0

    for nombre, real in reales.items():
        print(f"\n=== {nombre} ===")
        crudo = preguntar(cliente, PROMPT, [IMAGENES / nombre],
                          response_format={"type": "json_object"})
        print("Respuesta cruda:", crudo)

        # Validación: si el JSON no cumple el esquema se informa y se sigue con la siguiente imagen
        try:
            extraido = PaginaReglamento.model_validate_json(crudo).model_dump()
        except ValidationError as e:
            print(f"[JSON INVÁLIDO] {nombre}: {e.error_count()} error(es) de esquema")
            for err in e.errors():
                print(f"   - {err['loc']}: {err['msg']}")
            total += len(CAMPOS)  # todos los campos cuentan como no acertados
            continue

        for campo in CAMPOS:
            # 'tema_principal' es de texto libre: se revisa a mano (columna 'revisar')
            if campo == "tema_principal":
                filas.append({"imagen": nombre, "campo": campo, "real": real[campo],
                              "extraido": extraido[campo], "correcto": None})
                continue
            ok = normalizar(real[campo]) == normalizar(extraido[campo])
            aciertos += ok
            total += 1
            filas.append({"imagen": nombre, "campo": campo, "real": real[campo],
                          "extraido": extraido[campo], "correcto": ok})
            print(f"  {campo:18} real={real[campo]!r:45} extraído={extraido[campo]!r:45} {'OK' if ok else 'NO'}")

    pct = 100 * aciertos / total if total else 0
    print(f"\nAciertos (sin contar tema_principal, que se juzga a mano): {aciertos} de {total} = {pct:.1f} %")
    (RESULTADOS / "1_2_extraccion.json").write_text(
        json.dumps({"filas": filas, "aciertos": aciertos, "total": total, "porcentaje": pct},
                   ensure_ascii=False, indent=2), encoding="utf-8")
