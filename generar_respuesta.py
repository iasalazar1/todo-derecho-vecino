"""Generación de respuestas legales con citas rastreables para el MVP Todo Derecho Vecino.

No realiza escrituras en Aurora. Reutiliza el recuperador existente y hace una única
llamada al modelo generativo configurado mediante BEDROCK_MODEL_ID.
"""
from __future__ import annotations

import json
import os
import re
import logging
from pathlib import Path
from typing import Any, Callable

from retriever import (
    MissingStructuredParameters,
    StructuredRetrievalError,
    Table22NoRecords,
)


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "respuesta_legal.txt"
CITATION_PATTERN = re.compile(r"\[(F\d+)\]")

ASTERISK_MARK = "*"
NOTA_PENDIENTE_ADVERTENCIA = (
    "Advertencia: el estado contiene un asterisco (*) que remite a una nota "
    "de la Tabla 22; la nota asociada no está disponible en la tabla "
    "estructurada y su condición está pendiente de interpretación. No debe "
    "interpretarse como autorización incondicional."
)


class CitationIntegrityError(ValueError):
    """El modelo citó una fuente que no se le proporcionó."""


def _load_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"No se pudo leer el prompt legal: {PROMPT_PATH}") from exc


def _normalize_results(results: Any) -> list[dict[str, Any]]:
    """Normaliza el resultado del retriever sin inventar campos de fuente."""
    if results is None:
        return []
    if isinstance(results, str):
        try:
            results = json.loads(results)
        except json.JSONDecodeError as exc:
            raise ValueError("El recuperador devolvió texto que no es JSON válido.") from exc
    if isinstance(results, dict):
        # Admite un objeto individual, pero no interpreta arbitrariamente sus campos.
        results = [results]
    if not isinstance(results, list):
        raise ValueError("El recuperador debe devolver una lista de resultados.")
    normalized = []
    for item in results:
        if isinstance(item, dict):
            normalized.append(item)
    return normalized


def _source_label(item: dict[str, Any]) -> str:
    parts = []
    for key, label in (
        ("documento", "Documento"),
        ("articulo", "Artículo"),
        ("cita_legal", "Cita legal"),
        ("segmento", "Segmento"),
    ):
        value = item.get(key)
        if value not in (None, ""):
            parts.append(f"{label}: {value}")
    return " | ".join(parts) if parts else "Metadatos de fuente no disponibles"


def _is_structured_row(item: dict[str, Any]) -> bool:
    """Determina si un resultado es una fila puntual de Tabla 22 (actividad + zonificación)."""
    return item.get("tipo_evidencia") == "structured_row"


def _is_table_summary(item: dict[str, Any]) -> bool:
    """Determina si un resultado es un resumen general de Tabla 22 (una entrada por actividad)."""
    return item.get("tipo_evidencia") == "structured_table_summary"


def _is_structured_evidence(item: dict[str, Any]) -> bool:
    """Cubre ambas modalidades de evidencia estructurada de Tabla 22."""
    return _is_structured_row(item) or _is_table_summary(item)


def _format_paginas(paginas: Any) -> str:
    """Formatea fuente_paginas como texto legible sin alterar los valores."""
    if paginas in (None, "", []):
        return ""
    if isinstance(paginas, list):
        return ", ".join(str(p) for p in paginas if p not in (None, ""))
    return str(paginas)


def _estado_tiene_asterisco(estado: Any) -> bool:
    """Detecta referencias a notas por asterisco en el estado literal.

    Los estados válidos incluyen, p. ej., 'permitido (*)' y 'permitido (**)';
    cualquier asterisco presente en el estado indica una remisión a nota.
    """
    return isinstance(estado, str) and ASTERISK_MARK in estado


def _format_estados_por_zonificacion(estados: Any) -> str:
    """Formatea los estados por zonificación con valores literales.

    Formato nuevo (jsonb_agg con procedencia): lista de objetos, cada uno con
    zonificacion, estado_original, fuente_archivo, fuente_paginas y
    needs_review propios.
    Formato legado (dict zonificacion -> estado): se acepta por robustez,
    pero sin procedencia propia.
    En ambos casos los estados no se corrigen ni reinterpretan.
    """
    if isinstance(estados, list) and estados and all(isinstance(e, dict) for e in estados):
        partes = []
        for celda in estados:
            zona = celda.get("zonificacion")
            estado = celda.get("estado_original", "")
            sufijo = ""
            if celda.get("needs_review"):
                sufijo = " [pendiente de revisión]"
            if estado not in (None, ""):
                partes.append(f"{zona}: {estado}{sufijo}")
        return "; ".join(partes)
    if isinstance(estados, dict) and estados:
        partes = [
            f"{zona}: {estado}"
            for zona, estado in sorted(estados.items(), key=lambda par: str(par[0]))
            if estado not in (None, "")
        ]
        return "; ".join(partes)
    return ""


def _zona_incluye_nota(celda: dict[str, Any]) -> str:
    """Nota de la celda, únicamente si existe en los datos fuente."""
    nota = celda.get("nota")
    if isinstance(nota, str) and nota.strip():
        return nota.strip()
    return ""


def _render_estados_detallados(estados: Any) -> tuple[list[str], list[str], list[str]]:
    """Renderiza por zonificación: estado literal, fuente y páginas propias.

    Devuelve (lineas_de_texto, notas_disponibles, marcas_asterisco_sin_nota).
    Las notas solo se incluyen si existen en el registro; los asteriscos sin
    nota recuperable se reportan como pendientes de interpretación, nunca
    silenciosos ni reinterpretados.
    """
    lineas = []
    notas = []
    asteriscos_sin_nota = []

    if isinstance(estados, list) and estados and all(isinstance(e, dict) for e in estados):
        for celda in estados:
            zona = celda.get("zonificacion", "")
            estado = celda.get("estado_original", "")
            if estado in (None, ""):
                continue
            fuente = celda.get("fuente_archivo", "")
            paginas = _format_paginas(celda.get("fuente_paginas"))
            pieza = f"Zonificación {zona} — Estado (literal): {estado}"
            if fuente:
                pieza += f" | Fuente: {fuente}"
            if paginas:
                pieza += f" | Páginas: {paginas}"
            if celda.get("needs_review"):
                pieza += " | Pendiente de revisión: sí"
            nota = _zona_incluye_nota(celda)
            if nota:
                pieza += f" | Nota: {nota}"
                notas.append(nota)
            elif _estado_tiene_asterisco(estado):
                asteriscos_sin_nota.append(str(zona))
            lineas.append(pieza)
        return lineas, notas, asteriscos_sin_nota

    # Formato legado sin procedencia por celda
    texto = _format_estados_por_zonificacion(estados)
    if texto:
        lineas.append(texto)
    if isinstance(estados, dict):
        for zona, estado in estados.items():
            if _estado_tiene_asterisco(estado):
                asteriscos_sin_nota.append(str(zona))
    return lineas, notas, asteriscos_sin_nota


def _get_nota(item: dict[str, Any]) -> str:
    """Devuelve la nota del registro solo si existe y es texto con contenido.

    No se incorporan notas cuando no hay relación comprobable con el registro
    (ausencia de la clave o valor vacío).
    """
    nota = item.get("nota")
    if isinstance(nota, str) and nota.strip():
        return nota.strip()
    return ""


def _structured_row_fragment(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Construye la representación textual de una fila puntual de Tabla 22.

    Devuelve (texto_del_fragmento, metadatos_extra_para_la_cita).
    """
    actividad = item.get("actividad", "")
    zonificacion = item.get("zonificacion", "")
    estado = item.get("estado_original", "")
    categoria = item.get("categoria", "")
    subcategoria = item.get("subcategoria", "")
    fuente = item.get("fuente_archivo", "")
    paginas = _format_paginas(item.get("fuente_paginas"))
    nota = _get_nota(item)
    advertencia_nota = False

    # Los estados se presentan literalmente: permitido, prohibido, por validar,
    # permitido (*), permitido (**), etc.
    fragment_parts = []
    if actividad:
        fragment_parts.append(f"Actividad: {actividad}")
    if categoria:
        fragment_parts.append(f"Categoría: {categoria}")
    if subcategoria:
        fragment_parts.append(f"Subcategoría: {subcategoria}")
    if zonificacion:
        fragment_parts.append(f"Zonificación: {zonificacion}")
    if estado:
        fragment_parts.append(f"Estado (literal): {estado}")
    if fuente:
        fragment_parts.append(f"Fuente: {fuente}")
    if paginas:
        fragment_parts.append(f"Páginas: {paginas}")
    if nota:
        fragment_parts.append(f"Nota: {nota}")

    extra_source = {
        "actividad": actividad,
        "categoria": categoria,
        "subcategoria": subcategoria,
        "zonificacion": zonificacion,
        "estado_original": estado,
        "fuente_archivo": fuente,
        "fuente_paginas": item.get("fuente_paginas"),
    }
    if nota:
        extra_source["nota"] = nota
    elif _estado_tiene_asterisco(estado):
        # Asterisco sin nota recuperable: advertencia explícita en el
        # fragmento (contexto de Claude) y en la cita.
        extra_source["advertencia_nota_pendiente"] = True
        fragment_parts.append(NOTA_PENDIENTE_ADVERTENCIA)

    return " | ".join(fragment_parts), extra_source


def _table_summary_fragment(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Construye la representación textual de un resumen general de Tabla 22.

    Un registro por actividad; cada zonificación conserva su propia
    procedencia (estado literal, fuente, páginas, marca de revisión y nota
    si existiera). No convierte celdas ausentes en permisos ni prohibiciones.
    """
    actividad = item.get("actividad", "")
    categoria = item.get("categoria", "")
    subcategoria = item.get("subcategoria", "")
    estados = item.get("estados_por_zonificacion")
    nota = _get_nota(item)

    lineas_estados, notas_celdas, asteriscos_sin_nota = (
        _render_estados_detallados(estados)
    )

    fragment_parts = []
    if actividad:
        fragment_parts.append(f"Actividad: {actividad}")
    if categoria:
        fragment_parts.append(f"Categoría: {categoria}")
    if subcategoria:
        fragment_parts.append(f"Subcategoría: {subcategoria}")
    if lineas_estados:
        # Multilínea: una línea por zonificación con su procedencia propia.
        fragment_parts.append(
            "Estados por zonificación (literales, con procedencia):\n"
            + "\n".join(f"  - {linea}" for linea in lineas_estados)
        )
    if nota:
        fragment_parts.append(f"Nota: {nota}")
    if asteriscos_sin_nota:
        # Remisión por asterisco sin nota recuperable en los datos estructurados.
        fragment_parts.append(NOTA_PENDIENTE_ADVERTENCIA)

    extra_source = {
        "actividad": actividad,
        "categoria": categoria,
        "subcategoria": subcategoria,
        "estados_por_zonificacion": estados,
        "estados_claves_con_asterisco_sin_nota": asteriscos_sin_nota,
    }
    if nota:
        extra_source["nota"] = nota
    if asteriscos_sin_nota:
        extra_source["advertencia_nota_pendiente"] = True

    return " | ".join(fragment_parts), extra_source


def _build_context(results: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    sources = []
    blocks = []
    for index, item in enumerate(results, start=1):
        source_id = f"F{index}"
        source = {
            "id": source_id,
            "documento": item.get("documento"),
            "articulo": item.get("articulo"),
            "cita_legal": item.get("cita_legal"),
            "segmento": item.get("segmento"),
            "pendiente_revision": bool(item.get("pendiente_revision", False)),
        }
        # Construir representación textual según el tipo de evidencia
        if _is_structured_row(item):
            # --- Evidencia estructurada puntual (fila de land_use_compatibility) ---
            fragment, extra_source = _structured_row_fragment(item)
            source.update(extra_source)
            # Trazabilidad documental de la fila estructurada
            if not source.get("articulo"):
                source["articulo"] = "Tabla 22"
            if not source.get("cita_legal"):
                referencia = (
                    f"PPCU Hipódromo, Tabla 22 — {extra_source['actividad']} "
                    f"({extra_source['zonificacion']})"
                    if extra_source.get("actividad")
                    else "PPCU Hipódromo, Tabla 22"
                )
                source["cita_legal"] = referencia
        elif _is_table_summary(item):
            # --- Evidencia estructurada general (resumen de Tabla 22 por actividad) ---
            fragment, extra_source = _table_summary_fragment(item)
            source.update(extra_source)
            if not source.get("articulo"):
                source["articulo"] = "Tabla 22"
            if not source.get("cita_legal"):
                referencia = (
                    "PPCU Hipódromo, Tabla 22 — "
                    + str(extra_source.get("actividad") or "")
                    if extra_source.get("actividad")
                    else "PPCU Hipódromo, Tabla 22"
                )
                source["cita_legal"] = referencia
        else:
            # --- Evidencia semántica (fragmento jurídico del corpus) ---
            # Comportamiento conservador: utilizar el texto del fragmento y su procedencia
            fragment = item.get("fragmento") or item.get("texto") or item.get("segmento_texto", "")
        # Metadatos de documento y tabla para evidencia estructurada
        if _is_structured_evidence(item):
            if item.get("documento_id"):
                source["documento_id"] = item.get("documento_id")
            if item.get("tabla_id"):
                source["tabla_id"] = item.get("tabla_id")
        source["fragmento"] = str(fragment or "")
        sources.append(source)
        # Construir bloque de contexto para el modelo
        metadatos = f"Metadatos: {_source_label(item)}\n"
        revisión = ""
        if source["pendiente_revision"]:
            revisión = "Pendiente de revisión: sí\n"
        fragment_text = source["fragmento"]
        blocks.append(
            f"[{source_id}]\n"
            f"{revisión}{metadatos}"
            f"Fragmento recuperado:\n{fragment_text}"
        )
    return "\n\n---\n\n".join(blocks), sources


def _extract_text(response: dict[str, Any]) -> str:
    try:
        content = response["output"]["message"]["content"]
        text_parts = [part["text"] for part in content if isinstance(part, dict) and "text" in part]
    except (KeyError, TypeError) as exc:
        raise ValueError("La respuesta de Bedrock no tiene el formato Converse esperado.") from exc
    text = "\n".join(text_parts).strip()
    if not text:
        raise ValueError("El modelo devolvió una respuesta vacía.")
    return text


def _validate_citations(answer: str, sources: list[dict[str, Any]]) -> list[str]:
    allowed = {source["id"] for source in sources}
    found = list(dict.fromkeys(CITATION_PATTERN.findall(answer)))
    unknown = [source_id for source_id in found if source_id not in allowed]
    if unknown:
        raise CitationIntegrityError(
            "El modelo citó identificadores no proporcionados: " + ", ".join(unknown)
        )
    return found


def answer_question(
    question: str,
    top_k: int = 5,
    model_id: str | None = None,
    retriever_fn: Callable[..., Any] | None = None,
    bedrock_client: Any | None = None,
    region_name: str = "us-east-1",
) -> dict[str, Any]:
    """Recupera evidencia y genera una respuesta; permite inyectar dependencias para tests."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("La pregunta no puede estar vacía.")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k debe ser un entero positivo.")

    chosen_model = model_id or os.getenv("BEDROCK_MODEL_ID")
    if not chosen_model:
        return {
            "status": "error",
            "question": question.strip(),
            "answer": "",
            "citations": [],
            "limitations": ["Falta configurar la variable de entorno BEDROCK_MODEL_ID."],
            "model_id": None,
        }

    try:
        if retriever_fn is None:
            from retriever import retrieve
            retriever_fn = retrieve

        raw_results = retriever_fn(question.strip(), top_k=top_k)
        results = _normalize_results(raw_results)
        context, sources = _build_context(results)

        if not sources or not any(source["fragmento"].strip() for source in sources):
            return {
                "status": "insufficient_evidence",
                "question": question.strip(),
                "answer": (
                    "No encontré fragmentos recuperados con contenido suficiente para "
                    "fundamentar una respuesta. No puedo concluir qué permite o prohíbe "
                    "la normativa con la evidencia disponible."
                ),
                "citations": [],
                "limitations": ["La recuperación no proporcionó fragmentos con contenido utilizable."],
                "model_id": chosen_model,
            }

        if bedrock_client is None:
            import boto3
            region_name = os.getenv("AWS_REGION", region_name)
            bedrock_client = boto3.client("bedrock-runtime", region_name=region_name)

        system_prompt = _load_prompt()
        user_message = (
            f"PREGUNTA DEL USUARIO:\n{question.strip()}\n\n"
            f"EVIDENCIA RECUPERADA:\n{context}\n\n"
            "Redacta la respuesta en español y cita las fuentes usando exactamente los "
            "identificadores [F1], [F2], etc. No uses fuentes externas."
        )
        response = bedrock_client.converse(
            modelId=chosen_model,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_message}]}],
            inferenceConfig={"maxTokens": 1200, "temperature": 0.1},
        )
        answer = _extract_text(response)
        cited_ids = _validate_citations(answer, sources)
        source_by_id = {source["id"]: source for source in sources}
        citations = [source_by_id[source_id] for source_id in cited_ids]

        limitations = []
        if any(source["pendiente_revision"] for source in citations):
            limitations.append(
                "Al menos una fuente citada está marcada como pendiente de revisión; "
                "su contenido requiere validación jurídica."
            )
        if any(
            source.get("advertencia_nota_pendiente") for source in citations
        ):
            limitations.append(
                "Al menos una fuente citada contiene un estado con asterisco "
                "(*) cuya nota asociada no está disponible en la tabla "
                "estructurada; su condición está pendiente de interpretación "
                "y no debe tratarse como autorización incondicional."
            )
        if not cited_ids:
            limitations.append(
                "La respuesta generada no contiene identificadores de cita verificables."
            )

        status = "answered" if cited_ids else "insufficient_evidence"
        if not cited_ids:
            answer = (
                "La evidencia recuperada no quedó vinculada a citas verificables en la "
                "respuesta generada. No debe tomarse como una conclusión jurídica."
            )

        return {
            "status": status,
            "question": question.strip(),
            "answer": answer,
            "citations": citations,
            "limitations": limitations,
            "model_id": chosen_model,
        }

    except MissingStructuredParameters as exc:
        # Consulta de compatibilidad de uso de suelo sin actividad y
        # zonificación explícitas: no se invoca al modelo ni se usa
        # evidencia semántica como sustituto; se solicitan únicamente
        # los datos faltantes. HTTP 200 (estado en el cuerpo, igual
        # contrato que los demás estados controlados).
        logging.getLogger(__name__).info(
            "Consulta de compatibilidad sin parámetros estructurados: %s",
            exc,
        )
        return {
            "status": "missing_structured_parameters",
            "question": question.strip(),
            "answer": "",
            "citations": [],
            "missing_fields": list(exc.missing_fields),
            "limitations": [
                str(exc),
                (
                    "Para consultar la Tabla 22 de usos de suelo del PPCU "
                    "Hipódromo, reenvíe la consulta incluyendo el campo "
                    "'activity' (nombre de la actividad) y el campo "
                    "'zonification' (una de: H, HC, HO, HM, HCS, E, EA)."
                ),
            ],
            "model_id": chosen_model,
        }

    except Table22NoRecords as exc:
        logging.getLogger(__name__).info(
            "Consulta estructurada sin coincidencias: %s", exc
        )
        return {
            "status": "table_22_no_matches",
            "question": question.strip(),
            "answer": str(exc),
            "citations": [],
            "limitations": [
                str(exc),
                (
                    "La consulta estructurada se ejecutó correctamente sin "
                    "coincidencias; esto no implica permiso ni prohibición."
                ),
            ],
            "model_id": chosen_model,
        }

    except StructuredRetrievalError as exc:
        logging.getLogger(__name__).exception(
            "Fallo técnico de recuperación estructurada de Tabla 22: %s", exc
        )
        return {
            "status": "structured_retrieval_error",
            "question": question.strip(),
            "answer": "",
            "citations": [],
            "limitations": [
                str(exc),
                (
                    "No fue posible consultar la evidencia estructurada "
                    "necesaria; no se generó una conclusión jurídica "
                    "sustitutiva y la recuperación semántica no se usó como "
                    "sustituto."
                ),
            ],
            "model_id": chosen_model,
        }

    except CitationIntegrityError as exc:
        logging.getLogger(__name__).exception(
            "Error de integridad de citas: %s", exc
        )
        return {
            "status": "error",
            "question": question.strip(),
            "answer": "",
            "citations": [],
            "limitations": [str(exc)],
            "model_id": chosen_model,
        }

    except Exception as exc:
        logging.getLogger(__name__).exception(
            "Error al recuperar información o generar respuesta"
        )
        return {
            "status": "error",
            "question": question.strip(),
            "answer": "",
            "citations": [],
            "limitations": [
                f"No fue posible completar la generación ({type(exc).__name__})."
            ],
            "model_id": chosen_model,
        }