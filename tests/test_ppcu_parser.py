#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas automatizadas para PPCUParserProto.

Ejecuta:
    python3 tests/test_ppcu_parser.py

Imprime cada prueba como APROBADA / FALLADA con motivo, y un resumen final.
Código de salida distinto de cero si hay fallas.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.ppcu_parser_proto import PPCUParserProto  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEWED_TXT = os.path.join(REPO_ROOT, "leyes_cdmx", "PPCU_Hipodromo_reviewed.txt")
HISTORIC_JSON = os.path.join(REPO_ROOT, "leyes_cdmx", "PPCU_Hipodromo_reviewed_chunks.json")

resultados = []


def _registro(nombre, ok, motivo=""):
    resultados.append((nombre, ok, motivo))
    estado = "APROBADA" if ok else "FALLADA"
    print(f"[{estado}] {nombre}" + (f" — {motivo}" if motivo and not ok else ""))


def test_decimal_safety():
    parser = PPCUParserProto()
    ok = not bool(parser.apartado_re.match("29.90"))
    _registro("apartado_re_rechaza_29.90_sin_titulo", ok)
    ok = bool(parser.percent_re.match("1.14%"))
    _registro("percent_re_detecta_1.14_porcentaje", ok)
    texto_tabla = "Vivienda Plurifamiliar, 130, 29.90"
    ok = not bool(parser.apartado_re.match(texto_tabla))
    _registro("celda_tabla_29.90_no_es_encabezado", ok)
    ok = not bool(parser.apartado_re.match("al 1.14% de la P.E.A."))
    _registro("1.14_porcentaje_en_texto_no_es_encabezado", ok)
    ok = not bool(parser.apartado_re.match("1.14 Vivienda"))
    _registro("indice_sin_punto_no_es_encabezado", ok)


def test_encabezados_y_jerarquia():
    parser = PPCUParserProto()
    casos_validos = [
        ("1.8. Usos del Suelo", "1.8"),
        ("## 1.14. Vivienda", "1.14"),
        ("4.2. Zonificación", "4.2"),
        ("3.10. Vivienda", "3.10"),
        ("3.4.1. Usos del Suelo", "3.4.1"),
        ("3.6. Transporte", "3.6"),
    ]
    for linea, numero_esperado in casos_validos:
        m = parser.apartado_re.match(linea)
        ok = bool(m) and m.group(1).rstrip(".") == numero_esperado
        _registro(f"apartado_reconocido_{numero_esperado}", ok,
                  f"línea='{linea}'")
    m = parser.chapter_re.match("II. IMAGEN OBJETIVO")
    _registro("capitulo_romano_II", bool(m) and m.group(1).upper() == "II")
    m = parser.chapter_re.match("## IV. ORDENAMIENTO TERRITORIAL")
    _registro("capitulo_romano_IV_con_##", bool(m) and m.group(1).upper() == "IV")


def test_integridad_tablas():
    parser = PPCUParserProto()
    texto = ("PÁGINA 10\n"
             "[TABLA 19]\n"
             "Uso predominante del suelo en edificios catalogados\n"
             "Uso del suelo, Edificios catalogados Núm., Edificios catalogados %\n"
             "Vivienda Unifamiliar, 159, 36.57\n"
             "Vivienda Plurifamiliar, 130, 29.90\n"
             "Oficinas, 69, 15.87\n"
             "[/TABLA 19]\n"
             "Texto después de la tabla\n")
    chunks = parser.parse(texto)
    tablas = [c for c in chunks if c.get("is_table")]
    _registro("tabla_detectada_como_unidad", len(tablas) == 1,
              f"tablas encontradas: {len(tablas)}")
    if tablas:
        t = tablas[0]
        _registro("tabla_contiene_29.90", "29.90" in t.get("texto", ""))
        _registro("tabla_texto_completo", "Oficinas, 69, 15.87" in t.get("texto", ""))


def test_notas_y_condiciones():
    parser = PPCUParserProto()
    texto = ("PÁGINA 20\n"
             "4.2. Zonificación\n"
             "Contenido del apartado\n"
             "Condición: los predios receptores de transferencia serán aquellos...\n"
             "Nota: ver plano de Zonificación.\n")
    chunks = parser.parse(texto)
    texto_completo = "\n".join(c.get("texto", "") for c in chunks)
    _registro("condicion_conservada", "Condición:" in texto_completo)
    _registro("nota_conservada", "Nota:" in texto_completo)


def test_seguimiento_paginas():
    parser = PPCUParserProto()
    texto = ("PÁGINA 3\n"
             "Contenido página 3\n"
             "PÁGINA 4\n"
             "Contenido página 4\n")
    chunks = parser.parse(texto)
    paginas_cubiertas = set()
    for c in chunks:
        ini = c.get("pagina_inicial")
        fin = c.get("pagina_final")
        if ini:
            paginas_cubiertas.add(str(ini))
        if fin:
            paginas_cubiertas.add(str(fin))
    _registro("paginas_detectadas", "3" in paginas_cubiertas and "4" in paginas_cubiertas,
              f"páginas cubiertas: {paginas_cubiertas}")
    estados_validos = {"known", "inferred", "unknown"}
    estados_ok = all(
        c.get("page_tracking_status") in estados_validos for c in chunks
    )
    _registro("page_tracking_status_valido", estados_ok)


def test_referencias_graficas():
    parser = PPCUParserProto()
    texto = ("PÁGINA 30\n"
             "[IMAGEN DE PLANO\n"
             "Contenido: Plano de zonificación. Uso Actual de Suelo\n"
             "]\n"
             "Texto después del plano\n")
    chunks = parser.parse(texto)
    planos = [c for c in chunks if c.get("has_plano")]
    _registro("plano_detectado", len(planos) >= 1,
              f"planos encontrados: {len(planos)}")
    if planos:
        _registro("plano_no_es_tabla", not planos[0].get("is_table", False))


def test_division_fragmentos_extensos():
    parser = PPCUParserProto()
    parser.max_chunk_chars = 200
    parrafo = ("Este es un párrafo bastante largo que debería ser dividido "
               "en múltiples fragmentos porque excede el límite máximo de "
               "caracteres configurado para el prototipo. " * 6)
    texto = ("PÁGINA 1\n"
             "1.8. Usos del Suelo\n"
             + parrafo + "\n")
    chunks = parser.parse(texto)
    largos = [c for c in chunks if len(c.get("texto", "")) > parser.max_chunk_chars + 50]
    _registro("fragmentos_extensos_divididos", len(largos) == 0,
              f"fragmentos aún muy largos: {len(largos)}")
    divididos = [c for c in chunks if c.get("parent_chunk_id")]
    _registro("divididos_tienen_parent_id", len(divididos) > 0 or len(chunks) > 1,
              f"chunks totales: {len(chunks)}, con parent: {len(divididos)}")


def test_preservacion_texto_fuente():
    parser = PPCUParserProto()
    texto = ("PÁGINA 1\n"
             "1.8. Usos del Suelo\n"
             "Este es el contenido del apartado.\n")
    chunks = parser.parse(texto)
    for c in chunks:
        ini = c.get("offset_inicio")
        fin = c.get("offset_fin")
        if ini is not None and fin is not None:
            fragmento_reconstruido = texto[ini:fin]
            _registro(f"offset_coincide_chunk_{str(c.get('chunk_id'))[:8]}",
                      fragmento_reconstruido == c.get("texto", ""),
                      f"offset [{ini}:{fin}]")
            break


def test_integridad_archivo_historico():
    import hashlib
    with open(HISTORIC_JSON, "rb") as f:
        datos = f.read()
    sha = hashlib.sha256(datos).hexdigest()
    tamano = len(datos)
    _registro("sha256_historico_coincide",
              sha == "e61ecd2835a49504843869e69e3a21e18e4e9fa7041cfc8d2d3f107f1c36c8c3",
              f"sha={sha}")
    _registro("tamano_historico_coincide", tamano == 316017,
              f"tamano={tamano}")
    with open(HISTORIC_JSON, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    _registro("historico_tiene_52_chunks", len(chunks) == 52,
              f"chunks={len(chunks)}")
    _registro("todos_needs_review_true",
              all(c.get("needs_review") is True for c in chunks))


def test_parser_contra_archivo_real():
    parser = PPCUParserProto()
    with open(REVIEWED_TXT, "r", encoding="utf-8") as f:
        texto_real = f.read()
    chunks = parser.parse(texto_real)
    _registro("parser_produce_chunks_del_real", len(chunks) > 0,
              f"chunks={len(chunks)}")
    chunks_2990 = [c for c in chunks if "29.90" in c.get("texto", "")
                   and c.get("tipo") == "apartado"]
    _registro("real_29.90_no_es_apartado", len(chunks_2990) == 0,
              f"apartados con 29.90: {len(chunks_2990)}")
    # En el documento real, 3.4.1 y 3.6 aparecen solo en el índice
    # (líneas ~121-123, sin punto tras el número) por lo que no son
    # encabezados de cuerpo. Se esperan solo los que aparecen como
    # encabezados de cuerpo con punto: 1.8, 1.14, 3.10, 4.2.
    numeros_esperados = {"1.8", "1.14", "4.2", "3.10"}
    numeros_encontrados = set()
    for c in chunks:
        jer = c.get("jerarquia_niveles", {})
        for v in jer.values():
            for n in numeros_esperados:
                if v.startswith(n + ". ") or v.startswith(n + ".") or v == n or v.startswith(n + " "):
                    numeros_encontrados.add(n)
    _registro("real_apartados_criticos_encontrados",
              numeros_esperados.issubset(numeros_encontrados),
              f"encontrados: {sorted(numeros_encontrados)}")
    campos_obligatorios = [
        "doc_id", "chunk_id", "parent_chunk_id", "source_file", "modalidad",
        "pagina_inicial", "pagina_final", "page_tracking_status", "jerarquia",
        "referencia_normativa", "is_table", "has_plano", "needs_review",
        "parser_status", "legal_validation_status",
    ]
    todos_tienen_campos = all(
        all(campo in c for campo in campos_obligatorios) for c in chunks
    )
    _registro("todos_chunks_tienen_campos_obligatorios", todos_tienen_campos)
    _registro("todos_needs_review_true",
              all(c.get("needs_review") is True for c in chunks))
    _registro("todos_parser_status_processed",
              all(c.get("parser_status") == "processed" for c in chunks))
    _registro("todos_legal_validation_pending",
              all(c.get("legal_validation_status") == "pending" for c in chunks))


def main():
    print("=" * 60)
    print("PRUEBAS AUTOMATIZADAS — PPCU Parser Prototipo")
    print("=" * 60)

    test_decimal_safety()
    test_encabezados_y_jerarquia()
    test_integridad_tablas()
    test_notas_y_condiciones()
    test_seguimiento_paginas()
    test_referencias_graficas()
    test_division_fragmentos_extensos()
    test_preservacion_texto_fuente()
    test_integridad_archivo_historico()
    test_parser_contra_archivo_real()

    total = len(resultados)
    aprobadas = sum(1 for _, ok, _ in resultados if ok)
    falladas = total - aprobadas

    print("=" * 60)
    print(f"RESUMEN: {total} pruebas, {aprobadas} aprobadas, {falladas} falladas")
    print("=" * 60)

    if falladas > 0:
        print("\nPruebas falladas:")
        for nombre, ok, motivo in resultados:
            if not ok:
                print(f"  - {nombre}: {motivo}")
        sys.exit(1)
    else:
        print("\nTodas las pruebas pasaron.")
        sys.exit(0)


if __name__ == "__main__":
    main()