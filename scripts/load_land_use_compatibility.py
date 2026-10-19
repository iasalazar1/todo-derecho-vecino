#!/usr/bin/env python3
"""Valida e importa la Tabla 22 a Aurora. Por defecto solo valida; --apply escribe."""
from __future__ import annotations
import argparse, csv, json, os, subprocess, sys, tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "leyes_cdmx" / "PPCU_Hipodromo_tabla_22.json"
ZONES = {"H", "HC", "HO", "HM", "HCS", "E", "EA"}
STATES = {"permitido", "prohibido", "por validar"}

DDL = """
CREATE TABLE IF NOT EXISTS land_use_compatibility (
 id BIGSERIAL PRIMARY KEY,
 documento_id TEXT NOT NULL, tabla_id TEXT NOT NULL, actividad_id TEXT NOT NULL,
 categoria TEXT, subcategoria TEXT, actividad_original TEXT NOT NULL,
 zonificacion TEXT NOT NULL CHECK (zonificacion IN ('H','HC','HO','HM','HCS','E','EA')),
 estado_original TEXT NOT NULL CHECK (estado_original IN ('permitido','prohibido','por validar')),
 alias_busqueda JSONB NOT NULL DEFAULT '[]'::jsonb,
 fuente_archivo TEXT NOT NULL, fuente_paginas JSONB NOT NULL DEFAULT '[]'::jsonb,
 needs_review BOOLEAN NOT NULL DEFAULT TRUE CHECK (needs_review = TRUE),
 importado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE (documento_id, tabla_id, actividad_id, zonificacion)
);
CREATE INDEX IF NOT EXISTS idx_luc_activity ON land_use_compatibility (actividad_id);
CREATE INDEX IF NOT EXISTS idx_luc_zone_state ON land_use_compatibility (zonificacion, estado_original);
CREATE INDEX IF NOT EXISTS idx_luc_aliases ON land_use_compatibility USING GIN (alias_busqueda);
"""

def text(value: Any, field: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: {field} debe ser texto no vacío.")
    return value.strip()

def validate(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró el JSON: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("La raíz del JSON debe ser una lista no vacía.")
    activities, rows, seen = [], [], set()
    for i, r in enumerate(data, 1):
        ctx = f"Registro {i}"
        if not isinstance(r, dict):
            raise ValueError(f"{ctx}: debe ser un objeto.")
        doc = text(r.get("documento_id"), "documento_id", ctx)
        table = text(r.get("tabla_id"), "tabla_id", ctx)
        aid = text(r.get("actividad_id"), "actividad_id", ctx)
        name = text(r.get("actividad_original"), "actividad_original", ctx)
        if (doc, table) != ("ppdu_hipodromo", "tabla_22"):
            raise ValueError(f"{ctx}: documento_id/tabla_id inesperados: {doc}/{table}")
        if aid in seen:
            raise ValueError(f"{ctx}: actividad_id duplicado: {aid}")
        seen.add(aid)
        if r.get("needs_review") is not True:
            raise ValueError(f"{ctx}: needs_review debe ser true.")
        zones = r.get("zonificaciones")
        if not isinstance(zones, dict) or set(zones) != ZONES:
            raise ValueError(f"{ctx}: debe contener exactamente las 7 zonificaciones.")
        aliases = r.get("alias_busqueda")
        if not isinstance(aliases, list) or not all(isinstance(x, str) and x.strip() for x in aliases):
            raise ValueError(f"{ctx}: alias_busqueda debe ser una lista de textos no vacíos.")
        src = r.get("fuente")
        if not isinstance(src, dict):
            raise ValueError(f"{ctx}: fuente debe ser objeto.")
        srcfile = text(src.get("archivo"), "fuente.archivo", ctx)
        pages = src.get("paginas")
        if not isinstance(pages, list) or not pages or not all(isinstance(p, int) and not isinstance(p, bool) and p > 0 for p in pages):
            raise ValueError(f"{ctx}: fuente.paginas debe contener enteros positivos.")
        base = dict(documento_id=doc, tabla_id=table, actividad_id=aid,
                    categoria=r.get("categoria"), subcategoria=r.get("subcategoria"),
                    actividad_original=name,
                    alias_busqueda=json.dumps(aliases, ensure_ascii=False),
                    fuente_archivo=srcfile,
                    fuente_paginas=json.dumps(pages, ensure_ascii=False))
        activities.append(base)
        for zone in sorted(ZONES):
            state = zones[zone]
            if state not in STATES:
                raise ValueError(f"{ctx}, {zone}: estado no admitido {state!r}.")
            rows.append({**base, "zonificacion": zone, "estado_original": state})
    return activities, rows

def apply_rows(rows, args):
    pgpass = os.environ.get("PGPASSFILE")
    if not pgpass or not Path(pgpass).is_file():
        raise RuntimeError("Para --apply, define PGPASSFILE con el archivo de credenciales.")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".csv", delete=False) as f:
        csvpath = Path(f.name)
        writer = csv.writer(f)
        writer.writerow(["documento_id","tabla_id","actividad_id","categoria","subcategoria",
                         "actividad_original","zonificacion","estado_original","alias_busqueda",
                         "fuente_archivo","fuente_paginas","needs_review"])
        for r in rows:
            writer.writerow([r["documento_id"],r["tabla_id"],r["actividad_id"],r["categoria"] or "",
                             r["subcategoria"] or "",r["actividad_original"],r["zonificacion"],
                             r["estado_original"],r["alias_busqueda"],r["fuente_archivo"],
                             r["fuente_paginas"],"true"])
    try:
        copy_path = str(csvpath).replace("'", "''")
        sql = "BEGIN;\n" + DDL + """
CREATE TEMP TABLE land_use_compatibility_stage (
 documento_id TEXT, tabla_id TEXT, actividad_id TEXT, categoria TEXT, subcategoria TEXT,
 actividad_original TEXT, zonificacion TEXT, estado_original TEXT, alias_busqueda JSONB,
 fuente_archivo TEXT, fuente_paginas JSONB, needs_review BOOLEAN
) ON COMMIT DROP;
""" + f"\\copy land_use_compatibility_stage FROM '{copy_path}' WITH (FORMAT csv, HEADER true)\n" + """
INSERT INTO land_use_compatibility (
 documento_id, tabla_id, actividad_id, categoria, subcategoria, actividad_original,
 zonificacion, estado_original, alias_busqueda, fuente_archivo, fuente_paginas, needs_review
)
SELECT documento_id, tabla_id, actividad_id, NULLIF(categoria,''), NULLIF(subcategoria,''),
 actividad_original, zonificacion, estado_original, alias_busqueda, fuente_archivo,
 fuente_paginas, TRUE FROM land_use_compatibility_stage
ON CONFLICT (documento_id, tabla_id, actividad_id, zonificacion) DO UPDATE SET
 categoria=EXCLUDED.categoria, subcategoria=EXCLUDED.subcategoria,
 actividad_original=EXCLUDED.actividad_original, estado_original=EXCLUDED.estado_original,
 alias_busqueda=EXCLUDED.alias_busqueda, fuente_archivo=EXCLUDED.fuente_archivo,
 fuente_paginas=EXCLUDED.fuente_paginas, needs_review=TRUE, importado_en=NOW();
SELECT zonificacion, estado_original, COUNT(*) FROM land_use_compatibility
WHERE documento_id='ppdu_hipodromo' AND tabla_id='tabla_22'
GROUP BY zonificacion, estado_original ORDER BY zonificacion, estado_original;
COMMIT;
"""
        cmd = ["psql","-X","-w","-h",args.host,"-p",str(args.port),"-U",args.username,
               "-d",args.database,"-v","ON_ERROR_STOP=1"]
        result = subprocess.run(cmd, input=sql, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Falló la importación.")
        print(result.stdout.strip())
    finally:
        csvpath.unlink(missing_ok=True)

def main():
    p = argparse.ArgumentParser(description="Valida e importa Tabla 22; por defecto no escribe.")
    p.add_argument("--json", type=Path, default=DEFAULT_JSON)
    p.add_argument("--apply", action="store_true", help="Escribe en Aurora dentro de una transacción.")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=15432)
    p.add_argument("--database", default="tododerechovecino")
    p.add_argument("--username", default="tdv_admin")
    args = p.parse_args()
    try:
        activities, rows = validate(args.json)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr); return 1
    counts = Counter(r["estado_original"] for r in rows)
    print(f"JSON: {args.json}")
    print(f"Actividades validadas: {len(activities)}")
    print(f"Celdas validadas: {len(rows)}")
    print(f"Valores: {dict(sorted(counts.items()))}")
    print("Zonificaciones: H, HC, HO, HM, HCS, E, EA")
    print("needs_review: true en todos los registros")
    if not args.apply:
        print("MODO DE PRUEBA: no se conectó ni escribió en Aurora.")
        print("La importación requiere --apply explícito.")
        return 0
    try:
        apply_rows(rows, args)
    except (OSError, RuntimeError, subprocess.SubprocessError) as e:
        print(f"ERROR de importación: {e}", file=sys.stderr); return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
