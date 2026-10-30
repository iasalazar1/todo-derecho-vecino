"""Generación de respuestas legales con citas rastreables para el MVP Todo Derecho Vecino.

No realiza escrituras en Aurora. Reutiliza el recuperador existente y hace una única
llamada al modelo generativo configurado mediante BEDROCK_MODEL_ID.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "respuesta_legal.txt"
CITATION_PATTERN = re.compile(r"\[(F\d+)\]")


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
        # No se inventan URL, número de artículo ni otros datos ausentes.
        fragment = item.get("fragmento")
        if fragment in (None, ""):
            fragment = item.get("texto", "")
        if fragment in (None, ""):
            fragment = item.get("segmento_texto", "")
        source["fragmento"] = str(fragment or "")
        sources.append(source)
        blocks.append(
            f"[{source_id}]\n"
            f"Metadatos: {_source_label(item)}\n"
            f"Pendiente de revisión: {'sí' if source['pendiente_revision'] else 'no indicado'}\n"
            f"Fragmento recuperado:\n{source['fragmento']}"
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
    except CitationIntegrityError as exc:
        return {
            "status": "error",
            "question": question.strip(),
            "answer": "",
            "citations": [],
            "limitations": [str(exc)],
            "model_id": chosen_model,
        }
    except Exception as exc:
        # La API devuelve un estado controlado; el detalle técnico no se expone como fundamento legal.
        return {
            "status": "error",
            "question": question.strip(),
            "answer": "",
            "citations": [],
            "limitations": [f"No fue posible completar la generación ({type(exc).__name__})."],
            "model_id": chosen_model,
        }
