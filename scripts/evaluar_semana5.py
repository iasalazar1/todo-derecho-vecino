"""Evaluación reproducible del retriever para la Semana 5.

Reutiliza las funciones existentes. No escribe en la base de datos.
La relevancia semántica requiere anotación manual.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retriever import retrieve, retrieve_land_use


ARCHIVO_CASOS = ROOT / "tests" / "evaluacion_semana5.json"


def evaluar_estructurados(casos):
    aprobados = 0
    fallidos = 0

    print("\n=== EVALUACIÓN ESTRUCTURADA ===")

    for caso in casos:
        identificador = caso["id"]

        try:
            resultados = retrieve_land_use(
                caso["actividad"],
                caso["zonificacion"],
            )

            estados = {
                resultado.get("estado_original")
                for resultado in resultados
            }

            estado_esperado = caso["estado_esperado"]
            correcto = (
                len(resultados) > 0
                and estados == {estado_esperado}
                and all(
                    resultado.get("pendiente_revision") is True
                    for resultado in resultados
                )
            )

            if correcto:
                aprobados += 1
                estado = "OK"
            else:
                fallidos += 1
                estado = "FALLO"

            print(
                f"{estado} {identificador}: "
                f"actividad={caso['actividad']!r}, "
                f"zona={caso['zonificacion']}, "
                f"esperado={estado_esperado!r}, "
                f"devuelto={sorted(estados)!r}, "
                f"resultados={len(resultados)}"
            )

        except Exception as error:
            fallidos += 1
            print(f"FALLO {identificador}: {type(error).__name__}: {error}")

    total = len(casos)
    porcentaje = (aprobados / total * 100) if total else 0

    print(
        f"\nResultado estructurado: {aprobados}/{total} aprobados "
        f"({porcentaje:.1f} %); fallidos: {fallidos}."
    )
    return aprobados, fallidos


def evaluar_semanticos(casos):
    print("\n=== EVALUACIÓN SEMÁNTICA ===")
    total_resultados = 0

    for caso in casos:
        print(f"\nCaso {caso['id']}: {caso['pregunta']}")

        try:
            resultados = retrieve(
                caso["pregunta"],
                top_k=caso.get("top_k", 5),
            )
        except Exception as error:
            print(f"ERROR: {type(error).__name__}: {error}")
            continue

        total_resultados += len(resultados)

        if not resultados:
            print("No se recuperaron fragmentos.")
            continue

        for posicion, resultado in enumerate(resultados, start=1):
            print(
                f"\n[{posicion}] "
                f"Documento: {resultado.get('documento')}\n"
                f"Artículo: {resultado.get('articulo')}\n"
                f"Cita: {resultado.get('cita_legal')}\n"
                f"Distancia: {resultado.get('distancia_coseno')}\n"
                f"Pendiente de revisión: "
                f"{resultado.get('pendiente_revision')}\n"
                f"Fragmento: {resultado.get('fragmento', '')[:500]}"
            )

        print(
            "\nAnotación manual pendiente: identificar cuáles resultados "
            "son pertinentes para la pregunta. No se calcula Precision@5 "
            "definitiva con referencias incompletas."
        )

    print(
        f"\nResultados semánticos mostrados: {total_resultados}. "
        "La cantidad recuperada no representa por sí sola la calidad."
    )


def main():
    with ARCHIVO_CASOS.open(encoding="utf-8") as archivo:
        evaluacion = json.load(archivo)

    print("Evaluación de Semana 5 — Todo Derecho Vecino")
    print(f"Archivo de casos: {ARCHIVO_CASOS.relative_to(ROOT)}")
    print("Modo de ejecución: solo lectura; no modifica datos.")

    aprobados, fallidos = evaluar_estructurados(
        evaluacion.get("estructurados", [])
    )

    evaluar_semanticos(evaluacion.get("semanticos", []))

    print("\n=== RESUMEN ===")
    print(f"Pruebas estructuradas aprobadas: {aprobados}")
    print(f"Pruebas estructuradas fallidas: {fallidos}")
    print("Evaluación semántica: requiere revisión humana.")
    print("Revisión jurídica y vigencia normativa: pendientes.")

    if fallidos:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
