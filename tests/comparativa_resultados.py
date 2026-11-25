#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparativa de resultados: parser experimental vs línea base histórica (52 chunks).

Ejecuta:
    python3 tests/comparativa_resultados.py

Genera una comparación cuantitativa y cualitativa sin modificar el archivo
histórico ni el texto fuente. Solo lee y reporta.
"""

import json
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.ppcu_parser_proto import PPCUParserProto  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEWED_TXT = os.path.join(REPO_ROOT, "leyes_cdmx", "PPCU_Hipodromo_reviewed.txt")
HISTORIC_JSON = os.path.join(REPO_ROOT, "leyes_cdmx", "PPCU_Hipodromo_reviewed_chunks.json")

SHA256_ESPERADO = "e61ecd2835a49504843869e69e3a21e18e4e9fa7041cfc8d2d3f107f1c36c8c3"
TAMANO_ESPERADO = 316017
CHUNKS_ESPERADOS = 52


def cargar_texto_fuente():
    with open(REVIEWED_TXT, "r", encoding="utf-8") as f:
        return f.read()


def cargar_chunks_historicos():
    with open(HISTORIC_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def verificar_integridad_historica():
    """Verifica que el archivo histórico no se haya modificado."""
    with open(HISTORIC_JSON, "rb") as f:
        datos = f.read()
    sha = hashlib.sha256(datos).hexdigest()
    tamano = len(datos)
    ok_sha = sha == SHA256_ESPERADO
    ok_tam = tamano == TAMANO_ESPERADO
    with open(HISTORIC_JSON, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    ok_n = len(chunks) == CHUNKS_ESPERADOS
    return {
        "sha256": sha,
        "sha_esperado": SHA256_ESPERADO,
        "sha_ok": ok_sha,
        "tamano": tamano,
        "tamano_esperado": TAMANO_ESPERADO,
        "tamano_ok": ok_tam,
        "num_chunks": len(chunks),
        "num_chunks_esperado": CHUNKS_ESPERADOS,
        "num_chunks_ok": ok_n,
        "integridad_ok": ok_sha and ok_tam and ok_n,
    }


def stats_longitudes(chunks):
    """Estadísticas de longitud de fragmentos."""
    longs = [len(c.get("texto", "")) for c in chunks]
    if not longs:
        return {"n": 0, "min": 0, "max": 0, "promedio": 0, "mediana": 0}
    longs_sorted = sorted(longs)
    n = len(longs_sorted)
    mediana = longs_sorted[n // 2] if n % 2 == 1 else (
        (longs_sorted[n // 2 - 1] + longs_sorted[n // 2]) / 2
    )
    return {
        "n": n,
        "min": min(longs),
        "max": max(longs),
        "promedio": sum(longs) / n,
        "mediana": mediana,
    }


def contar_menores(chunks, umbral=120):
    return sum(1 for c in chunks if len(c.get("texto", "")) < umbral)


def contar_excesivos(chunks, umbral=2000):
    return sum(1 for c in chunks if len(c.get("texto", "")) > umbral)


def contar_encabezados_aislados(chunks):
    """Fragmentos que son solo un encabezado sin contenido sustancial."""
    count = 0
    for c in chunks:
        t = c.get("texto", "").strip()
        if len(t) < 80 and c.get("tipo") in ("chapter", "apartado", "subapartado", "subhead"):
            count += 1
    return count


def secciones_historicas(chunks):
    """Conjunto de secciones identificadas en los chunks históricos."""
    return set(c.get("seccion") for c in chunks if c.get("seccion"))


def jerarquia_calidad(chunks):
    """Evalúa la calidad de la jerarquía: ¿tienen jerarquia no vacía?"""
    con_jerarquia = sum(1 for c in chunks if c.get("jerarquia"))
    con_padre = sum(1 for c in chunks if c.get("parent_chunk_id"))
    return {
        "con_jerarquia": con_jerarquia,
        "con_parent_chunk_id": con_padre,
        "total": len(chunks),
    }


def ejecutar_parser_nuevo(texto):
    parser = PPCUParserProto()
    return parser.parse(texto)


def reporte_cuantitativo(nombre, chunks):
    stats = stats_longitudes(chunks)
    return {
        "nombre": nombre,
        "total": len(chunks),
        "min": stats["min"],
        "max": stats["max"],
        "promedio": round(stats["promedio"], 1),
        "mediana": stats["mediana"],
        "menores_120": contar_menores(chunks, 120),
        "excesivos_2000": contar_excesivos(chunks, 2000),
        "encabezados_aislados": contar_encabezados_aislados(chunks),
        "jerarquia": jerarquia_calidad(chunks),
    }


def comparar_secciones(historicos, nuevos):
    """Compara qué apartados aparecen en cada versión."""
    secs_hist = secciones_historicas(historicos)
    # Para los nuevos, extraer el número de sección de jerarquia_niveles o referencia
    secs_nuevos = set()
    for c in nuevos:
        for v in c.get("jerarquia_niveles", {}).values():
            # Extraer número decimal al inicio (ej. "1.8. Usos del Suelo" -> "1.8")
            import re
            m = re.match(r"^(\d+(?:\.\d+)*)", v.strip())
            if m:
                secs_nuevos.add(m.group(1))
    return secs_hist, secs_nuevos


def detectar_falso_2990(chunks):
    """Detecta si '29.90' aparece como encabezado de apartado propio."""
    for c in chunks:
        if c.get("tipo") == "apartado" and "29.90" in c.get("texto", ""):
            return True
    return False


def verificar_apartados_criticos(nuevos):
    """Verifica que 1.8, 1.14, 4.2, 3.4.1, 3.6, 3.10 aparezcan como apartados."""
    esperados = {"1.8", "1.14", "4.2", "3.4.1", "3.6", "3.10"}
    encontrados = set()
    for c in nuevos:
        for v in c.get("jerarquia_niveles", {}).values():
            for e in esperados:
                if v.startswith(e + ". ") or v.startswith(e + ".") or v == e or v.startswith(e + " "):
                    encontrados.add(e)
    return esperados, encontrados


def contar_tablas(chunks):
    return sum(1 for c in chunks if c.get("is_table"))


def contar_planos(chunks):
    return sum(1 for c in chunks if c.get("has_plano"))


def ejemplo_antes_despues(historicos, nuevos):
    """Extrae ejemplos representativos antes y después."""
    antes = historicos[0] if historicos else {}
    despues = nuevos[0] if nuevos else {}
    return {
        "antes_chunk_id": antes.get("chunk_id"),
        "antes_seccion": antes.get("seccion"),
        "antes_texto_inicio": antes.get("texto", "")[:120],
        "despues_chunk_id": despues.get("chunk_id"),
        "despues_seccion": despues.get("jerarquia_niveles", {}).get("apartado", ""),
        "despues_texto_inicio": despues.get("texto", "")[:120],
    }


def generar_reporte():
    integridad = verificar_integridad_historica()
    texto = cargar_texto_fuente()
    historicos = cargar_chunks_historicos()
    nuevos = ejecutar_parser_nuevo(texto)

    rep_hist = reporte_cuantitativo("Histórico (52 chunks)", historicos)
    rep_nuevo = reporte_cuantitativo("Nuevo (prototipo)", nuevos)

    secs_hist, secs_nuevos = comparar_secciones(historicos, nuevos)
    omisiones = secs_hist - secs_nuevos
    nuevas_secciones = secs_nuevos - secs_hist
    falso_2990_hist = detectar_falso_2990(historicos)
    falso_2990_nuevo = detectar_falso_2990(nuevos)
    esperados, encontrados = verificar_apartados_criticos(nuevos)
    tablas_hist = contar_tablas(historicos)
    tablas_nuevo = contar_tablas(nuevos)
    planos_nuevo = contar_planos(nuevos)
    ejemplo = ejemplo_antes_despues(historicos, nuevos)

    delta_total = rep_nuevo["total"] - rep_hist["total"]
    delta_prom = rep_nuevo["promedio"] - rep_hist["promedio"]
    delta_menores = rep_nuevo["menores_120"] - rep_hist["menores_120"]
    delta_excesivos = rep_nuevo["excesivos_2000"] - rep_hist["excesivos_2000"]

    mejoras = []
    regresiones = []
    revision_humana = []

    if not falso_2990_hist and falso_2990_nuevo:
        regresiones.append("29.90 detectado como encabezado en el nuevo parser")
    elif falso_2990_hist and not falso_2990_nuevo:
        mejoras.append("29.90 ya no es detectado como encabezado (falso positivo eliminado)")
    elif not falso_2990_hist and not falso_2990_nuevo:
        mejoras.append("29.90 correctamente no es encabezado en ambas versiones")

    if rep_nuevo["menores_120"] < rep_hist["menores_120"]:
        mejoras.append(f"Menos fragmentos <120 chars: {rep_hist['menores_120']} -> {rep_nuevo['menores_120']}")
    elif rep_nuevo["menores_120"] > rep_hist["menores_120"]:
        regresiones.append(f"Más fragmentos <120 chars: {rep_hist['menores_120']} -> {rep_nuevo['menores_120']}")
    if rep_nuevo["excesivos_2000"] < rep_hist["excesivos_2000"]:
        mejoras.append(f"Menos fragmentos excesivos: {rep_hist['excesivos_2000']} -> {rep_nuevo['excesivos_2000']}")
    elif rep_nuevo["excesivos_2000"] > rep_hist["excesivos_2000"]:
        regresiones.append(f"Más fragmentos excesivos: {rep_hist['excesivos_2000']} -> {rep_nuevo['excesivos_2000']}")

    if rep_nuevo["jerarquia"]["con_jerarquia"] > rep_hist["jerarquia"]["con_jerarquia"]:
        mejoras.append("Más fragmentos con jerarquía conservada")

    if omisiones:
        revision_humana.append(f"Secciones históricas no encontradas en nuevo: {sorted(omisiones)}")
    if nuevas_secciones:
        mejoras.append(f"Nuevas secciones detectadas: {sorted(nuevas_secciones)}")

    if esperados - encontrados:
        revision_humana.append(f"Apartados críticos no encontrados: {sorted(esperados - encontrados)}")

    if tablas_nuevo > tablas_hist:
        mejoras.append(f"Más tablas reconocidas: {tablas_hist} -> {tablas_nuevo}")
    elif tablas_nuevo == 0 and tablas_hist == 0:
        mejoras.append("Ambas versiones no detectan tablas como unidades (área de mejora)")

    if planos_nuevo > 0:
        mejoras.append(f"Referencias gráficas (planos) conservadas: {planos_nuevo}")

    print("=" * 70)
    print("COMPARATIVA: PARSER EXPERIMENTAL vs LÍNEA BASE HISTÓRICA (52 chunks)")
    print("=" * 70)

    print("\n--- Integridad del archivo histórico ---")
    print(f"  SHA256: {integridad['sha256']}")
    print(f"  SHA esperado: {integridad['sha_esperado']}")
    print(f"  SHA coincide: {integridad['sha_ok']}")
    print(f"  Tamaño: {integridad['tamano']} bytes (esperado {integridad['tamano_esperado']})")
    print(f"  Chunks: {integridad['num_chunks']} (esperado {integridad['num_chunks_esperado']})")
    print(f"  Integridad OK: {integridad['integridad_ok']}")

    print("\n--- Cuantitativo ---")
    print(f"{'Métrica':<28} {'Histórico':>12} {'Nuevo':>12} {'Δ':>8}")
    print(f"{'Total fragmentos':<28} {rep_hist['total']:>12} {rep_nuevo['total']:>12} {delta_total:>+8}")
    print(f"{'Longitud mínima':<28} {rep_hist['min']:>12} {rep_nuevo['min']:>12} {rep_nuevo['min']-rep_hist['min']:>+8}")
    print(f"{'Longitud máxima':<28} {rep_hist['max']:>12} {rep_nuevo['max']:>12} {rep_nuevo['max']-rep_hist['max']:>+8}")
    print(f"{'Longitud promedio':<28} {rep_hist['promedio']:>12} {rep_nuevo['promedio']:>12} {delta_prom:>+8.1f}")
    print(f"{'Longitud mediana':<28} {rep_hist['mediana']:>12} {rep_nuevo['mediana']:>12} {rep_nuevo['mediana']-rep_hist['mediana']:>+8}")
    print(f"{'Fragmentos < 120 chars':<28} {rep_hist['menores_120']:>12} {rep_nuevo['menores_120']:>12} {delta_menores:>+8}")
    print(f"{'Fragmentos > 2000 chars':<28} {rep_hist['excesivos_2000']:>12} {rep_nuevo['excesivos_2000']:>12} {delta_excesivos:>+8}")
    print(f"{'Encabezados aislados':<28} {rep_hist['encabezados_aislados']:>12} {rep_nuevo['encabezados_aislados']:>12}")
    print(f"{'Con jerarquía':<28} {rep_hist['jerarquia']['con_jerarquia']:>12} {rep_nuevo['jerarquia']['con_jerarquia']:>12}")
    print(f"{'Con parent_chunk_id':<28} {rep_hist['jerarquia']['con_parent_chunk_id']:>12} {rep_nuevo['jerarquia']['con_parent_chunk_id']:>12}")
    print(f"{'Tablas reconocidas':<28} {tablas_hist:>12} {tablas_nuevo:>12}")
    print(f"{'Planos conservados':<28} {'N/A':>12} {planos_nuevo:>12}")

    print("\n--- Apartados críticos ---")
    print(f"  29.90 como encabezado (histórico): {falso_2990_hist}")
    print(f"  29.90 como encabezado (nuevo): {falso_2990_nuevo}")
    print(f"  Esperados: {sorted(esperados)}")
    print(f"  Encontrados: {sorted(encontrados)}")
    print(f"  Faltantes: {sorted(esperados - encontrados)}")

    print("\n--- Mejoras identificadas ---")
    for m in mejoras:
        print(f"  [+] {m}")

    print("\n--- Regresiones identificadas ---")
    for r in regresiones:
        print(f"  [-] {r}")

    print("\n--- Requiere revisión humana ---")
    for r in revision_humana:
        print(f"  [?] {r}")

    print("\n--- Ejemplo antes / después ---")
    print(f"  Antes chunk_id: {ejemplo['antes_chunk_id']}")
    print(f"  Antes sección: {ejemplo['antes_seccion']}")
    print(f"  Antes texto: {ejemplo['antes_texto_inicio']}")
    print(f"  Después chunk_id: {ejemplo['despues_chunk_id']}")
    print(f"  Después sección: {ejemplo['despues_seccion']}")
    print(f"  Después texto: {ejemplo['despues_texto_inicio']}")

    print("\n" + "=" * 70)
    print("CONCLUSIÓN: resultado experimental, no validación jurídica.")
    print("No integrar al procesador productivo sin revisión explícita del usuario.")
    print("=" * 70)

    return {
        "integridad": integridad,
        "historico": rep_hist,
        "nuevo": rep_nuevo,
        "mejoras": mejoras,
        "regresiones": regresiones,
        "revision_humana": revision_humana,
        "ejemplo": ejemplo,
        "falso_2990_hist": falso_2990_hist,
        "falso_2990_nuevo": falso_2990_nuevo,
        "apartados_esperados": sorted(esperados),
        "apartados_encontrados": sorted(encontrados),
        "tablas_hist": tablas_hist,
        "tablas_nuevo": tablas_nuevo,
        "planos_nuevo": planos_nuevo,
    }


def main():
    generar_reporte()


if __name__ == "__main__":
    main()