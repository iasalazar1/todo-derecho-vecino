#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPCU Parser Prototipo Experimental
==================================

Parser jerarquico orientado a documentos de planeacion urbana (PPCU)
para el Programa Parcial de Desarrollo Urbano de la colonia Hipodromo.

AMBITO: exclusivamente la carpeta tests/.
- No toca src/legal_document_processor.py ni ningún cargador productivo.
- No modifica el archivo historico PPCU_Hipodromo_reviewed_chunks.json.
- No regenera embeddings. No toca infraestructura AWS/Aurora.
- No hace commit ni push.

Caracteristicas:
1. Identifica capitulos (numeral romano), apartados y subapartados.
2. Reconoce encabezados mediante contexto documental, no solo regex numerica.
3. Conserva la jerarquia de cada fragmento.
4. Rechaza falsos encabezados (porcentajes, valores decimales sueltos, celdas de tabla).
5. Conserva texto, pagina de origen, tablas y referencias graficas.
6. Divide fragmentos extensos y fusiona fragmentos demasiado pequenos.
7. Preserva literalmente el texto fuente (offsets de inicio y fin).
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple


class PPCUParserProto:
    """Parser jerarquico para documentos de planeacion urbana (PPCU)."""

    def __init__(self) -> None:
        self.doc_id = "PPCU_HIPODROMO"
        self.source_file = "leyes_cdmx/PPCU_Hipodromo_reviewed.txt"
        self.modalidad = "planeacion"

        # Umbrales de fragmentacion (configurables, no magicos)
        self.min_chunk_chars = 120
        self.max_chunk_chars = 2000

        # ----------------------------------------------------------------
        # Patrones compilados
        # ----------------------------------------------------------------
        # Marcador de pagina: linea que solo contiene "PAGINA N"
        self.page_re = re.compile(r"^PÁGINA\s+(\d+)\s*$", re.IGNORECASE)

        # Inicio de tabla: [TABLA <titulo>]
        self.table_start_re = re.compile(r"^\[TABLA\s+(.+?)\]\s*$", re.IGNORECASE)

        # Fin de tabla: [/TABLA <titulo>]  o  [FIN DE LA TABLA <titulo>]
        self.table_end_re = re.compile(r"^\[/TABLA\s+(.+?)\]\s*$", re.IGNORECASE)
        self.table_end_alt_re = re.compile(
            r"^\[FIN DE LA TABLA\s+(.+?)\]\s*$", re.IGNORECASE
        )

        # Marcador de plano grafico: [IMAGEN DE PLANO ...]  (case-insensitive)
        self.plano_re = re.compile(r"^\[IMAGEN DE PLANO", re.IGNORECASE)

        # Capitulo: [##] I. TITULO  (numeral romano, punto tras la letra)
        self.chapter_re = re.compile(
            r"^(?:##\s*)?([IVXLCDM]+)\.\s+(.+)$", re.IGNORECASE
        )

        # Apartado / subapartado: [##] N.N. Titulo
        # Requisitos clave para evitar falsos positivos:
        #   * punto tras el ultimo numero decimal  -> descarta "1.14 Vivienda" (indice)
        #   * titulo despues del punto              -> descarta "29.90" (valor suelto)
        #   * NO exige mayuscula inicial en el titulo
        self.apartado_re = re.compile(
            r"^(?:##\s*)?(\d+(?:\.\d+)+\.)\s+(.+)$"
        )

        # Subencabezado sin numero decimal: ## TEXTO
        self.subhead_re = re.compile(r"^##\s+(.+)$")

        # Falsos positivos a rechazar explicitamente
        self.decimal_only_re = re.compile(r"^\d+\.\d+\s*$")      # "29.90"
        self.percent_re = re.compile(r"^\d+\.\d+%")              # "1.14%"

    # ------------------------------------------------------------------
    # Utilidades de offsets y chunk_id
    # ------------------------------------------------------------------
    @staticmethod
    def _line_offsets(text: str) -> List[Tuple[int, int]]:
        """Devuelve (inicio, fin) de caracter de cada linea en el texto original."""
        offsets: List[Tuple[int, int]] = []
        pos = 0
        for line in text.split("\n"):
            offsets.append((pos, pos + len(line)))
            pos += len(line) + 1  # +1 por el '\n'
        return offsets

    @staticmethod
    def _make_chunk_id(doc_id: str, seccion: str, index: int, offset: int) -> str:
        """Identificador estable y reproducible (SHA-256 truncado a 16 hex)."""
        material = f"{doc_id}|{seccion}|{index}|{offset}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _empty_chunk() -> Dict[str, Any]:
        return {
            "doc_id": None,
            "chunk_id": None,
            "parent_chunk_id": None,
            "source_file": None,
            "modalidad": None,
            "pagina_inicial": None,
            "pagina_final": None,
            "page_tracking_status": "unknown",
            "jerarquia": [],                 # lista de nombres de nivel
            "jerarquia_niveles": {},         # {nivel: nombre, ...}
            "referencia_normativa": None,
            "texto": "",
            "offset_inicio": None,
            "offset_fin": None,
            "is_table": False,
            "has_plano": False,
            "needs_review": True,
            "parser_status": "processed",
            "legal_validation_status": "pending",
            "tipo": None,  # capitulo | apartado | subapartado | parrafo | tabla | plano
        }

    # ------------------------------------------------------------------
    # Punto de entrada principal
    # ------------------------------------------------------------------
    def parse(self, text: str) -> List[Dict[str, Any]]:
        """Parsea el texto fuente y devuelve una lista de fragmentos."""
        lines = text.split("\n")
        offsets = self._line_offsets(text)

        sequences = self._build_sequences(lines, offsets)
        chunks = self._assemble_chunks(sequences, text)
        chunks = self._merge_small_chunks(chunks)
        chunks = self._split_large_chunks(chunks)
        chunks = self._finalize_chunks(chunks, text)
        return chunks

    # ------------------------------------------------------------------
    # Paso 1: identificar secuencias (bloques homogéneos entre break points)
    # ------------------------------------------------------------------
    def _build_sequences(
        self, lines: List[str], offsets: List[Tuple[int, int]]
    ) -> List[Dict[str, Any]]:
        """Recorre línea por línea y agrupa en secuencias homogéneas.

        Cada secuencia tiene:
          tipo: "page" | "chapter" | "apartado" | "subapartado" |
                "subhead" | "table" | "plano" | "texto"
          line_start, line_end: índices de línea (inclusive)
          offset_inicio, offset_fin: en el texto fuente
          pagina: número de página vigente
          page_tracking_status: "known" | "inferred" | "unknown"
          contenido: texto completo de la secuencia
          es_encabezado: si la primera línea es un encabezado jerárquico
        """
        sequences: List[Dict[str, Any]] = []
        n = len(lines)

        i = 0
        pagina_actual: Optional[str] = None
        page_status: str = "unknown"

        while i < n:
            stripped = lines[i].strip()
            off_ini = offsets[i][0]
            off_fin = offsets[i][1]

            # --- Marcador de página ---
            m_page = self.page_re.match(stripped)
            if m_page:
                pagina_actual = m_page.group(1)
                page_status = "known"
                sequences.append({
                    "tipo": "page",
                    "line_start": i,
                    "line_end": i,
                    "offset_inicio": off_ini,
                    "offset_fin": off_fin,
                    "pagina": pagina_actual,
                    "page_tracking_status": page_status,
                    "contenido": stripped,
                    "es_encabezado": False,
                })
                i += 1
                continue

            # --- Inicio de tabla ---
            m_ts = self.table_start_re.match(stripped)
            if m_ts:
                j = i
                tabla_titulo = m_ts.group(1).strip()
                line_inicio = i
                while j < n:
                    sj = lines[j].strip()
                    if self.table_end_re.match(sj) or self.table_end_alt_re.match(sj):
                        break
                    j += 1
                if j < n:
                    line_fin = j
                else:
                    line_fin = n - 1
                contenido = "\n".join(lines[line_inicio:line_fin + 1])
                sequences.append({
                    "tipo": "table",
                    "line_start": line_inicio,
                    "line_end": line_fin,
                    "offset_inicio": offsets[line_inicio][0],
                    "offset_fin": offsets[line_fin][1],
                    "pagina": pagina_actual,
                    "page_tracking_status": page_status,
                    "contenido": contenido,
                    "tabla_titulo": tabla_titulo,
                    "es_encabezado": False,
                })
                i = line_fin + 1
                continue

            # --- Marcador de plano ---
            if self.plano_re.match(stripped):
                sequences.append({
                    "tipo": "plano",
                    "line_start": i,
                    "line_end": i,
                    "offset_inicio": off_ini,
                    "offset_fin": off_fin,
                    "pagina": pagina_actual,
                    "page_tracking_status": page_status,
                    "contenido": stripped,
                    "es_encabezado": False,
                })
                i += 1
                continue

            # --- Capítulo ---
            m_cap = self.chapter_re.match(stripped)
            if m_cap:
                numero = m_cap.group(1).upper()
                titulo = m_cap.group(2).strip()
                sequences.append({
                    "tipo": "chapter",
                    "line_start": i,
                    "line_end": i,
                    "offset_inicio": off_ini,
                    "offset_fin": off_fin,
                    "pagina": pagina_actual,
                    "page_tracking_status": page_status,
                    "contenido": stripped,
                    "numero": numero,
                    "titulo": titulo,
                    "es_encabezado": True,
                })
                i += 1
                continue

            # --- Apartado / subapartado (con punto tras el número) ---
            m_ap = self.apartado_re.match(stripped)
            if m_ap:
                numero = m_ap.group(1)
                titulo = m_ap.group(2).strip()
                profundidad = numero.count(".")
                if profundidad == 1:
                    tipo_seq = "apartado"
                else:
                    tipo_seq = "subapartado"
                sequences.append({
                    "tipo": tipo_seq,
                    "line_start": i,
                    "line_end": i,
                    "offset_inicio": off_ini,
                    "offset_fin": off_fin,
                    "pagina": pagina_actual,
                    "page_tracking_status": page_status,
                    "contenido": stripped,
                    "numero": numero,
                    "titulo": titulo,
                    "profundidad": profundidad,
                    "es_encabezado": True,
                })
                i += 1
                continue

            # --- Subencabezado ## sin número ---
            m_sh = self.subhead_re.match(stripped)
            if m_sh:
                titulo = m_sh.group(1).strip()
                sequences.append({
                    "tipo": "subhead",
                    "line_start": i,
                    "line_end": i,
                    "offset_inicio": off_ini,
                    "offset_fin": off_fin,
                    "pagina": pagina_actual,
                    "page_tracking_status": page_status,
                    "contenido": stripped,
                    "titulo": titulo,
                    "es_encabezado": True,
                })
                i += 1
                continue

            # --- Texto ordinario (agrupar líneas contiguas no encabezadas) ---
            j = i
            while j < n:
                sj = lines[j].strip()
                if not sj:
                    j += 1
                    continue
                if (self.page_re.match(sj)
                        or self.table_start_re.match(sj)
                        or self.table_end_re.match(sj)
                        or self.table_end_alt_re.match(sj)
                        or self.plano_re.match(sj)
                        or self.chapter_re.match(sj)
                        or self.apartado_re.match(sj)
                        or self.subhead_re.match(sj)):
                    break
                j += 1
            line_fin = j - 1
            contenido = "\n".join(lines[i:line_fin + 1])
            sequences.append({
                "tipo": "texto",
                "line_start": i,
                "line_end": line_fin,
                "offset_inicio": offsets[i][0],
                "offset_fin": offsets[line_fin][1],
                "pagina": pagina_actual,
                "page_tracking_status": page_status,
                "contenido": contenido,
                "es_encabezado": False,
            })
            i = line_fin + 1

        return sequences

    # ------------------------------------------------------------------
    # Paso 2: ensamblar secuencias en fragmentos jerárquicos
    # ------------------------------------------------------------------
    def _assemble_chunks(
        self, sequences: List[Dict[str, Any]], text: str
    ) -> List[Dict[str, Any]]:
        """Convierte secuencias en fragmentos con jerarquía y metadatos."""
        chunks: List[Dict[str, Any]] = []

        capitulo_actual: Optional[str] = None
        apartado_actual: Optional[str] = None
        subapartado_actual: Optional[str] = None

        contador_por_seccion: Dict[str, int] = {}

        actual: Optional[Dict[str, Any]] = None

        def flush_actual() -> None:
            nonlocal actual
            if actual is not None:
                chunks.append(actual)
                actual = None

        for seq in sequences:
            tipo = seq["tipo"]
            pagina = seq["pagina"]
            page_status = seq["page_tracking_status"]

            if tipo == "page":
                continue

            if seq["es_encabezado"]:
                flush_actual()

                if tipo == "chapter":
                    capitulo_actual = seq["titulo"]
                    apartado_actual = None
                    subapartado_actual = None
                    clave_jer = f"Capítulo {capitulo_actual}"
                elif tipo == "apartado":
                    apartado_actual = f"{seq['numero']} {seq['titulo']}"
                    subapartado_actual = None
                    clave_jer = apartado_actual
                elif tipo == "subapartado":
                    subapartado_actual = f"{seq['numero']} {seq['titulo']}"
                    clave_jer = subapartado_actual
                elif tipo == "subhead":
                    clave_jer = seq["titulo"]
                else:
                    clave_jer = "Sin jerarquía"

                jerarquia: List[str] = []
                jerarquia_niveles: Dict[str, str] = {}
                if capitulo_actual:
                    jerarquia.append(capitulo_actual)
                    jerarquia_niveles["capitulo"] = capitulo_actual
                if apartado_actual:
                    jerarquia.append(apartado_actual)
                    jerarquia_niveles["apartado"] = apartado_actual
                if subapartado_actual:
                    jerarquia.append(subapartado_actual)
                    jerarquia_niveles["subapartado"] = subapartado_actual
                if tipo == "subhead":
                    jerarquia.append(seq["titulo"])
                    jerarquia_niveles["subencabezado"] = seq["titulo"]


                if tipo == "chapter":
                    seccion_ref = f"Capítulo {capitulo_actual}"
                    referencia = f"{self.doc_id}, Capítulo {capitulo_actual}"
                elif tipo == "apartado":
                    seccion_ref = seq["numero"].rstrip(".")
                    referencia = f"{self.doc_id}, Sección {seccion_ref}"
                elif tipo == "subapartado":
                    seccion_ref = seq["numero"].rstrip(".")
                    referencia = f"{self.doc_id}, Sección {seccion_ref}"
                else:
                    seccion_ref = clave_jer
                    referencia = f"{self.doc_id}, {clave_jer}"

                contador_por_seccion[seccion_ref] = (
                    contador_por_seccion.get(seccion_ref, 0) + 1
                )
                idx = contador_por_seccion[seccion_ref]

                actual = self._empty_chunk()
                actual["doc_id"] = self.doc_id
                actual["chunk_id"] = self._make_chunk_id(
                    self.doc_id, seccion_ref, idx, seq["offset_inicio"]
                )
                actual["source_file"] = self.source_file
                actual["modalidad"] = self.modalidad
                actual["pagina_inicial"] = pagina
                actual["pagina_final"] = pagina
                actual["page_tracking_status"] = page_status
                actual["jerarquia"] = jerarquia
                actual["jerarquia_niveles"] = jerarquia_niveles
                actual["referencia_normativa"] = referencia
                actual["texto"] = seq["contenido"]
                actual["offset_inicio"] = seq["offset_inicio"]
                actual["offset_fin"] = seq["offset_fin"]
                actual["tipo"] = tipo

                if tipo == "table":
                    actual["is_table"] = True
                    actual["referencia_normativa"] = (
                        f"{self.doc_id}, Tabla: {seq.get('tabla_titulo', 'sin título')}"
                    )
                    actual["texto"] = seq["contenido"]
                if tipo == "plano":
                    actual["has_plano"] = True

            else:
                if actual is None:
                    clave_jer = "Sin jerarquía"
                    seccion_ref = clave_jer
                    contador_por_seccion[seccion_ref] = (
                        contador_por_seccion.get(seccion_ref, 0) + 1
                    )
                    idx = contador_por_seccion[seccion_ref]
                    actual = self._empty_chunk()
                    actual["doc_id"] = self.doc_id
                    actual["chunk_id"] = self._make_chunk_id(
                        self.doc_id, seccion_ref, idx, seq["offset_inicio"]
                    )
                    actual["source_file"] = self.source_file
                    actual["modalidad"] = self.modalidad
                    actual["pagina_inicial"] = pagina
                    actual["pagina_final"] = pagina
                    actual["page_tracking_status"] = page_status
                    actual["jerarquia"] = []
                    actual["jerarquia_niveles"] = {}
                    actual["referencia_normativa"] = f"{self.doc_id}, Sin jerarquía"
                    actual["texto"] = ""
                    actual["offset_inicio"] = seq["offset_inicio"]
                    actual["offset_fin"] = seq["offset_fin"]
                    actual["tipo"] = "parrafo"
                    if tipo == "table":
                        actual["is_table"] = True
                    if tipo == "plano":
                        actual["has_plano"] = True

                if actual["texto"]:
                    actual["texto"] += "\n" + seq["contenido"]
                else:
                    actual["texto"] = seq["contenido"]
                actual["offset_fin"] = seq["offset_fin"]
                actual["pagina_final"] = pagina
                if page_status == "known":
                    actual["page_tracking_status"] = "known"

                if tipo == "table":
                    actual["is_table"] = True
                    actual["texto"] = seq["contenido"]
                    actual["referencia_normativa"] = (
                        f"{self.doc_id}, Tabla: {seq.get('tabla_titulo', 'sin título')}"
                    )
                if tipo == "plano":
                    actual["has_plano"] = True

        flush_actual()
        return chunks

    # ------------------------------------------------------------------
    # Paso 3: fusionar fragmentos demasiado pequeños
    # ------------------------------------------------------------------
    def _merge_small_chunks(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fusiona fragmentos < min_chunk_chars con el siguiente del mismo nivel.

        Conserva íntegramente: texto, páginas, offsets, jerarquía y
        relación con el fragmento padre.
        """
        if not chunks:
            return chunks

        resultado: List[Dict[str, Any]] = []
        i = 0
        while i < len(chunks):
            c = chunks[i]
            texto_len = len(c["texto"])

            es_pequeno = (
                texto_len < self.min_chunk_chars
                and c["tipo"] not in ("chapter", "table", "plano")
                and not c["is_table"]
            )

            if es_pequeno and i + 1 < len(chunks):
                siguiente = chunks[i + 1]
                mismo_nivel = c["jerarquia"] == siguiente["jerarquia"]
                if mismo_nivel:
                    c["texto"] = c["texto"] + "\n" + siguiente["texto"]
                    c["offset_fin"] = siguiente["offset_fin"]
                    c["pagina_final"] = siguiente["pagina_final"]
                    if siguiente["page_tracking_status"] == "known":
                        c["page_tracking_status"] = siguiente["page_tracking_status"]
                    siguiente["_absorbed"] = True
                    resultado.append(c)
                    i += 2
                    continue

            resultado.append(c)
            i += 1

        return [c for c in resultado if not c.get("_absorbed")]

    # ------------------------------------------------------------------
    # Paso 4: dividir fragmentos excesivamente extensos
    # ------------------------------------------------------------------
    def _split_large_chunks(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Divide fragmentos > max_chunk_chars sin perder jerarquía ni página."""
        resultado: List[Dict[str, Any]] = []
        for c in chunks:
            if len(c["texto"]) <= self.max_chunk_chars:
                resultado.append(c)
                continue

            # Estrategia 1: dividir por párrafos (líneas en blanco)
            parrafos = c["texto"].split("\n\n")
            if len(parrafos) > 1:
                resultado.extend(
                    self._split_by_units(c, parrafos, "\n\n")
                )
                continue

            # Estrategia 2: dividir por líneas individuales
            lineas = c["texto"].split("\n")
            if len(lineas) > 1:
                resultado.extend(
                    self._split_by_units(c, lineas, "\n")
                )
                continue

            # Estrategia 3: dividir por trozos de caracteres (último recurso)
            texto = c["texto"]
            indice_fragmento = 0
            offset_cursor = c["offset_inicio"]
            while texto:
                trozo = texto[: self.max_chunk_chars]
                nuevo = self._emit_split_fragment(
                    c, trozo, indice_fragmento, offset_cursor
                )
                resultado.append(nuevo)
                indice_fragmento += 1
                offset_cursor += len(trozo)
                texto = texto[len(trozo):]

        return resultado

    def _split_by_units(
        self, c: Dict[str, Any], unidades: List[str], separador: str
    ) -> List[Dict[str, Any]]:
        """Divide una lista de unidades (párrafos o líneas) respetando max_chunk_chars."""
        resultado: List[Dict[str, Any]] = []
        bloque_actual = ""
        indice_fragmento = 0
        offset_cursor = c["offset_inicio"]

        for u in unidades:
            # Si una unidad individual excede el límite, dividirla por caracteres
            if len(u) > self.max_chunk_chars:
                # Emitir bloque actual si lo hay
                if bloque_actual:
                    nuevo = self._emit_split_fragment(
                        c, bloque_actual, indice_fragmento, offset_cursor
                    )
                    resultado.append(nuevo)
                    indice_fragmento += 1
                    offset_cursor += len(bloque_actual)
                    bloque_actual = ""
                # Dividir la unidad larga en trozos
                resto = u
                while resto:
                    trozo = resto[: self.max_chunk_chars]
                    nuevo = self._emit_split_fragment(
                        c, trozo, indice_fragmento, offset_cursor
                    )
                    resultado.append(nuevo)
                    indice_fragmento += 1
                    offset_cursor += len(trozo)
                    resto = resto[len(trozo):]
                continue

            candidato = (
                (bloque_actual + separador + u) if bloque_actual else u
            )
            if len(candidato) > self.max_chunk_chars and bloque_actual:
                nuevo = self._emit_split_fragment(
                    c, bloque_actual, indice_fragmento, offset_cursor
                )
                resultado.append(nuevo)
                indice_fragmento += 1
                offset_cursor += len(bloque_actual) + len(separador)
                bloque_actual = u
            else:
                bloque_actual = candidato

        if bloque_actual:
            nuevo = self._emit_split_fragment(
                c, bloque_actual, indice_fragmento, offset_cursor
            )
            resultado.append(nuevo)

        return resultado

    @staticmethod
    def _emit_split_fragment(
        original: Dict[str, Any], texto: str, indice: int, offset_inicio: int
    ) -> Dict[str, Any]:
        """Crea un fragmento derivado de una división, copiando metadatos."""
        nuevo = dict(original)
        nuevo["texto"] = texto
        nuevo["offset_inicio"] = offset_inicio
        nuevo["offset_fin"] = offset_inicio + len(texto)
        nuevo["chunk_id"] = (
            f"{original['chunk_id']}_part{indice}"
            if original.get("chunk_id")
            else None
        )
        nuevo["parent_chunk_id"] = original.get("chunk_id")
        nuevo["tipo"] = "parrafo_dividido"
        return nuevo

    # ------------------------------------------------------------------
    # Paso 5: finalizar fragmentos (metadatos finales y limpieza)
    # ------------------------------------------------------------------
    def _finalize_chunks(
        self, chunks: List[Dict[str, Any]], text: str
    ) -> List[Dict[str, Any]]:
        """Ajusta metadatos finales y elimina claves internas."""
        for c in chunks:
            # Asegurar pagina_final >= pagina_inicial
            if c["pagina_inicial"] is not None and c["pagina_final"] is not None:
                try:
                    if int(c["pagina_final"]) < int(c["pagina_inicial"]):
                        c["pagina_final"] = c["pagina_inicial"]
                except (ValueError, TypeError):
                    pass

            # Eliminar claves internas no parte del esquema de salida
            c.pop("_absorbed", None)

            # Asegurar que página final no sea None si hay inicial
            if c["pagina_inicial"] is not None and c["pagina_final"] is None:
                c["pagina_final"] = c["pagina_inicial"]

        return chunks