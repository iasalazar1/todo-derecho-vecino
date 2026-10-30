"""Interfaz de terminal para probar la generación de respuestas legales."""

import argparse
import json
import sys

from generar_respuesta import answer_question


def main():
    parser = argparse.ArgumentParser(
        description="Genera una respuesta legal con citas."
    )
    parser.add_argument("pregunta", help="Pregunta legal en español.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Número máximo de fragmentos recuperados.",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Identificador de un modelo de Bedrock habilitado.",
    )
    args = parser.parse_args()

    resultado = answer_question(
        args.pregunta,
        top_k=args.top_k,
        model_id=args.model_id,
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado.get("status") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
