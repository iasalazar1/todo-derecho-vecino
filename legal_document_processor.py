"""
legal_document_processor.py

Orquesta el pipeline de preprocesamiento de leyes de Todo Derecho Vecino:

  1. Toma el texto ya revisado manualmente (*_reviewed.txt, generado por
     pdf_text_extractor.py).
  2. Limpia marcadores de página y encabezados repetidos.
  3. Detecta la jerarquía del documento (Título / Capítulo / Sección) para
     dar contexto a cada artículo.
  4. Divide el texto en artículos y, dentro de cada uno, en fracciones.
  5. Enriquece cada fracción con:
       - sujetos_obligados candidatos, cruzando el texto de la fracción
         contra las entidades más frecuentes que detecta autoridad_ner.py
       - un tipo_disposicion candidato (Obligación / Prohibición /
         Definición / Sanción / Procedimiento), usando señales léxicas
         simples y las palabras clave de procedimiento_ner.py
  6. Exporta un JSON con el esquema de metadatos de la propuesta v4
     (sección 2.7), listo para generar embeddings.

Los campos inferidos automáticamente (sujetos_obligados, tipo_disposicion)
se marcan con "needs_review": true para que un humano los confirme --
el mismo espíritu del paso manual que ya existe en pdf_text_extractor.py.

Uso:
    python legal_document_processor.py leyes_cdmx/LEY_AMBIENTAL_DE_LA_CDMX_1.2_reviewed.txt \
        --titulo "Ley Ambiental de la Ciudad de México" \
        --fuente "https://data.consejeria.cdmx.gob.mx/portal_old/uploads/gacetas/..."
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

# --- Enriquecimiento opcional: si spaCy o el modelo en español no están
# disponibles, el pipeline sigue funcionando, solo sin sujetos_obligados
# automáticos (quedan como lista vacía y marcados para revisión). ---
try:
    from autoridad_ner import load_spanish_model, extract_actor_entities
    _NER_AVAILABLE = True
except Exception:  # pragma: no cover - spaCy o el modelo no instalados
    _NER_AVAILABLE = False

from procedimiento_ner import PROCEDURE_KEYWORDS


MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

PAGE_MARKER_RE = re.compile(r"---\s*PAGE\s+\d+\s*---")
PUBLICACION_RE = re.compile(
    r"PUBLICADA?\s+EN\s+LA\s+GACETA\s+OFICIAL[^.]*?EL\s+(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚa-záéíóú]+)\s+DE\s+(\d{4})",
    re.IGNORECASE,
)
REFORMA_RE = re.compile(
    r"[ÚU]ltima\s+reforma\s+publicada.{0,60}?el\s+(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+de\s+(\d{4})",
    re.IGNORECASE,
)

TITULO_RE = re.compile(r"\bT[ÍI]TULO\s+([A-ZÁÉÍÓÚ]+)\b\.?", re.IGNORECASE)
CAPITULO_RE = re.compile(r"\bCAP[ÍI]TULO\s+([IVXLCDM]+)\b\.?", re.IGNORECASE)
SECCION_RE = re.compile(r"\bSECCI[ÓO]N\s+([A-ZÁÉÍÓÚ]+)\b\.?", re.IGNORECASE)

# Cubre variantes reales observadas: "Artículo 1º .- ", "Artículo 25.-",
# "Artículo 7 Bis.-". El ".-" se exige como obligatorio a propósito: sin
# esa condición, el patrón también capturaba referencias cruzadas dentro
# del propio texto (p. ej. "de conformidad con el artículo 11 de la Ley
# General...") y multiplicaba por 3 el número real de artículos. Se
# comprobó contra el texto real de la Ley Ambiental: con ".-" obligatorio,
# los 325 números de artículo detectados salen únicos y en orden
# ascendente; sin esa condición aparecían 1,014 fragmentos con muchos
# artículos repetidos hasta 46 veces.
ARTICULO_RE = re.compile(
    r"Art[íi]culo\s+(\d+)\s*(?:[°ºoO]|[Bb]is|[Tt]er)?\s*\.\s*-\s*"
)

FRACCION_RE = re.compile(r"(?:^|\s)([IVXLCDM]{1,6})\.\s*-?\s*")

ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(value: str) -> int:
    total = 0
    for i, ch in enumerate(value):
        v = ROMAN_VALUES.get(ch, 0)
        if i + 1 < len(value) and v < ROMAN_VALUES.get(value[i + 1], 0):
            total -= v
        else:
            total += v
    return total


def _spanish_date_to_iso(dia: str, mes: str, anio: str) -> Optional[str]:
    mes_num = MESES.get(mes.strip().lower())
    if not mes_num:
        return None
    return f"{int(anio):04d}-{mes_num:02d}-{int(dia):02d}"


@dataclass
class LegalChunk:
    chunk_id: str
    tipo_documento: str
    titulo_completo: str
    jurisdiccion: str
    fecha_publicacion: Optional[str]
    fecha_ultima_reforma: Optional[str]
    estado_vigencia: str
    titulo: Optional[str]
    capitulo: Optional[str]
    seccion: Optional[str]
    articulo: str
    fraccion: Optional[str]
    contexto_superior: str
    tema_principal: Optional[str]
    tipo_disposicion: Optional[str]
    sujetos_obligados: list
    cita_legal: str
    fuente: str
    texto: str
    needs_review: bool = field(default=False)


def clean_running_noise(text: str, titulo_completo: str) -> str:
    """Quita marcadores de página y el encabezado del documento que se
    repite en cada página (ruido típico de la extracción con PyPDF2)."""
    text = PAGE_MARKER_RE.sub(" ", text)
    header_pattern = re.compile(re.escape(titulo_completo.upper()))
    text = header_pattern.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_document_dates(raw_text: str):
    fecha_publicacion = None
    fecha_reforma = None
    m = PUBLICACION_RE.search(raw_text)
    if m:
        fecha_publicacion = _spanish_date_to_iso(*m.groups())
    m = REFORMA_RE.search(raw_text)
    if m:
        fecha_reforma = _spanish_date_to_iso(*m.groups())
    return fecha_publicacion, fecha_reforma


def split_by_hierarchy(text: str):
    """Recorre el texto y registra en qué posición cambia el Título,
    Capítulo o Sección vigente, para poder asignarlo luego a cada artículo."""
    markers = []
    for pattern, kind in ((TITULO_RE, "titulo"), (CAPITULO_RE, "capitulo"), (SECCION_RE, "seccion")):
        for m in pattern.finditer(text):
            markers.append((m.start(), kind, m.group(0).strip()))
    markers.sort(key=lambda item: item[0])
    return markers


def current_hierarchy_at(markers, position: int) -> dict:
    context = {"titulo": None, "capitulo": None, "seccion": None}
    for pos, kind, value in markers:
        if pos > position:
            break
        context[kind] = value
        if kind == "titulo":
            context["capitulo"] = None
            context["seccion"] = None
        elif kind == "capitulo":
            context["seccion"] = None
    return context


def split_articles(text: str):
    """Devuelve una lista de (numero_articulo, texto_articulo, posicion_inicial)."""
    matches = list(ARTICULO_RE.finditer(text))
    articles = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        articles.append((m.group(1), text[start:end].strip(), m.start()))
    return articles


def split_fracciones(articulo_texto: str):
    """Divide un artículo en fracciones (I, II, III...). Solo acepta una
    fracción si continúa la secuencia ascendente esperada, para reducir
    falsos positivos al detectar números romanos sueltos en el texto."""
    matches = list(FRACCION_RE.finditer(articulo_texto))
    expected = 1
    accepted = []
    for m in matches:
        value = roman_to_int(m.group(1).upper())
        if value == expected:
            accepted.append(m)
            expected += 1
    if len(accepted) < 2:
        return [(None, articulo_texto)]
    fracciones = []
    for i, m in enumerate(accepted):
        start = m.end()
        end = accepted[i + 1].start() if i + 1 < len(accepted) else len(articulo_texto)
        fracciones.append((m.group(1), articulo_texto[start:end].strip()))
    return fracciones


def guess_tipo_disposicion(texto: str):
    """Heurística léxica simple, no un clasificador entrenado.
    Devuelve (tipo_candidato, necesita_revision)."""
    lowered = texto.lower()
    if re.search(r"\bqueda(n)?\s+prohibid", lowered) or "prohibición" in lowered:
        return "Prohibición", True
    if re.search(r"para\s+(los\s+)?efectos\s+de\s+(esta|la\s+presente)\s+ley", lowered):
        return "Definición", True
    if re.search(r"sanci[oó]n|multa|infracci[oó]n", lowered):
        return "Sanción", True
    if any(kw in lowered for kw in PROCEDURE_KEYWORDS):
        return "Procedimiento", True
    if re.search(r"deber(á|án)|estar(á|án)\s+obligad", lowered):
        return "Obligación", True
    return None, True


def guess_sujetos_obligados(texto: str, entidades_documento: list):
    encontrados = [nombre for nombre, _ in entidades_documento if nombre.lower() in texto.lower()]
    return encontrados[:5], bool(encontrados)


def process_document(reviewed_path: str, titulo_completo: str, jurisdiccion: str,
                      fuente: str, tipo_documento: str = "Ley"):
    with open(reviewed_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    fecha_publicacion, fecha_reforma = extract_document_dates(raw_text)
    text = clean_running_noise(raw_text, titulo_completo)

    entidades_documento = []
    if _NER_AVAILABLE:
        try:
            nlp = load_spanish_model()
            entidades_documento = extract_actor_entities(text, nlp)
        except Exception as error:  # pragma: no cover
            print(f"[aviso] No se pudo ejecutar NER de autoridades: {error}")
    else:
        print("[aviso] spaCy/es_core_news_sm no disponible: sujetos_obligados quedará vacío.")

    hierarchy_markers = split_by_hierarchy(text)
    articles = split_articles(text)

    chunks = []
    for articulo_num, articulo_texto, pos in articles:
        contexto = current_hierarchy_at(hierarchy_markers, pos)
        contexto_superior = " / ".join(
            v for v in (contexto["titulo"], contexto["capitulo"], contexto["seccion"]) if v
        ) or titulo_completo

        for fraccion_num, fraccion_texto in split_fracciones(articulo_texto):
            if not fraccion_texto or len(fraccion_texto) < 10:
                continue
            tipo_disposicion, tipo_needs_review = guess_tipo_disposicion(fraccion_texto)
            sujetos, sujetos_found = guess_sujetos_obligados(fraccion_texto, entidades_documento)

            cita = f"{titulo_completo}, Art. {articulo_num}"
            if fraccion_num:
                cita += f", Fracc. {fraccion_num}"

            chunk = LegalChunk(
                chunk_id=hashlib.sha1(f"{titulo_completo}-{articulo_num}-{fraccion_num}".encode()).hexdigest()[:12],
                tipo_documento=tipo_documento,
                titulo_completo=titulo_completo,
                jurisdiccion=jurisdiccion,
                fecha_publicacion=fecha_publicacion,
                fecha_ultima_reforma=fecha_reforma,
                estado_vigencia="Vigente",
                titulo=contexto["titulo"],
                capitulo=contexto["capitulo"],
                seccion=contexto["seccion"],
                articulo=articulo_num,
                fraccion=fraccion_num,
                contexto_superior=contexto_superior,
                tema_principal=None,
                tipo_disposicion=tipo_disposicion,
                sujetos_obligados=sujetos,
                cita_legal=cita,
                fuente=fuente,
                texto=fraccion_texto,
                needs_review=(tipo_needs_review or not sujetos_found or tipo_disposicion is None),
            )
            chunks.append(chunk)

    return [asdict(c) for c in chunks]


def main():
    parser = argparse.ArgumentParser(
        description="Procesa una ley ya revisada (*_reviewed.txt) en fragmentos con metadatos."
    )
    parser.add_argument("reviewed_path", nargs="?", help="Ruta al archivo *_reviewed.txt")
    parser.add_argument("--titulo", help="Título completo del documento")
    parser.add_argument("--jurisdiccion", default="Ciudad de México")
    parser.add_argument("--fuente", help="URL o referencia oficial del documento")
    parser.add_argument("--tipo-documento", default="Ley")
    parser.add_argument("--out", help="Ruta de salida JSON (por defecto, junto al archivo de entrada)")
    parser.add_argument(
        "--batch",
        metavar="CONFIG_JSON",
        help=(
            "Ruta a un JSON con la lista de documentos a procesar, en vez de pasar "
            "un solo archivo. Cada entrada: {'reviewed_path', 'titulo', 'fuente', "
            "'jurisdiccion' (opcional), 'tipo_documento' (opcional)}. "
            "Los documentos cuyo reviewed_path todavía no exista se saltan con un aviso, "
            "para que puedas correr el mismo comando conforme vayas terminando la revisión de OCR."
        ),
    )
    args = parser.parse_args()

    if args.batch:
        with open(args.batch, "r", encoding="utf-8") as f:
            entries = json.load(f)
        procesados, saltados = 0, 0
        for entry in entries:
            reviewed_path = entry["reviewed_path"]
            if not os.path.exists(reviewed_path):
                print(f"[saltado] Aún no existe: {reviewed_path} (falta terminar la revisión de OCR)")
                saltados += 1
                continue
            chunks = process_document(
                reviewed_path,
                entry["titulo"],
                entry.get("jurisdiccion", "Ciudad de México"),
                entry["fuente"],
                entry.get("tipo_documento", "Ley"),
            )
            out_path = entry.get("out") or os.path.splitext(reviewed_path)[0] + "_chunks.json"
            with open(out_path, "w", encoding="utf-8") as f_out:
                json.dump(chunks, f_out, ensure_ascii=False, indent=2)
            necesitan_revision = sum(1 for c in chunks if c["needs_review"])
            print(f"[ok] {entry['titulo']}: {len(chunks)} fragmentos ({necesitan_revision} para revisión) -> {out_path}")
            procesados += 1
        print(f"\nResumen: {procesados} documentos procesados, {saltados} pendientes de revisión de OCR.")
        return

    if not args.reviewed_path or not args.titulo or not args.fuente:
        parser.error("sin --batch, se requieren: reviewed_path, --titulo y --fuente")

    chunks = process_document(
        args.reviewed_path, args.titulo, args.jurisdiccion, args.fuente, args.tipo_documento
    )

    out_path = args.out or os.path.splitext(args.reviewed_path)[0] + "_chunks.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    necesitan_revision = sum(1 for c in chunks if c["needs_review"])
    print(f"Documento procesado: {len(chunks)} fragmentos generados.")
    print(f"  -> {necesitan_revision} requieren revisión manual (tipo_disposicion o sujetos_obligados).")
    print(f"Guardado en: {out_path}")


if __name__ == "__main__":
    main()
    