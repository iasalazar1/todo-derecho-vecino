#!/usr/bin/env python3
"""Prueba interactiva del recuperador de Todo Derecho Vecino.

Requiere .venv activo, PGPASSFILE válido y túnel SSM hacia Aurora en 127.0.0.1:15432.
No escribe en la base de datos ni modifica fuentes o embeddings.
"""
import json
import os
from pathlib import Path

from retriever import retrieve, retrieve_land_use

ZONIFICACIONES = ("H", "HC", "HO", "HM", "HCS", "E", "EA")


def comprobar_precondiciones():
    pgpass = os.environ.get("PGPASSFILE")
    if not pgpass or not Path(pgpass).is_file():
        raise RuntimeError(
            "No se encuentra PGPASSFILE. Activa el entorno y configura, por ejemplo:\n"
            'export PGPASSFILE="$HOME/.pgpass-todo-derecho-vecino"'
        )


def main():
    comprobar_precondiciones()
    print("Todo Derecho Vecino — prueba interactiva del recuperador")
    print("1. Búsqueda semántica (pregunta libre)")
    print("2. Consulta estructurada de la Tabla 22 (actividad + zonificación)")
    opcion = input("Selecciona 1 o 2 [1]: ").strip() or "1"

    if opcion == "1":
        pregunta = input("Escribe tu pregunta jurídica: ").strip()
        if not pregunta:
            raise ValueError("La pregunta no puede estar vacía.")
        top_k_text = input("Número de resultados [5]: ").strip() or "5"
        try:
            top_k = int(top_k_text)
        except ValueError as exc:
            raise ValueError("El número de resultados debe ser un entero.") from exc
        resultados = retrieve(pregunta, top_k=top_k)
    elif opcion == "2":
        actividad = input("Nombre de la actividad tal como aparece en la tabla: ").strip()
        zona = input(f"Zonificación {', '.join(ZONIFICACIONES)}: ").strip().upper()
        if zona not in ZONIFICACIONES:
            raise ValueError(f"Zonificación inválida. Usa: {', '.join(ZONIFICACIONES)}.")
        resultados = retrieve_land_use(actividad, zona)
    else:
        raise ValueError("Opción inválida. Selecciona 1 o 2.")

    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    print(f"\nResultados recuperados: {len(resultados)}")
    if resultados and any(r.get("pendiente_revision") is True for r in resultados):
        print("AVISO: hay resultados pendientes de revisión jurídica; no son validación definitiva.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}")
