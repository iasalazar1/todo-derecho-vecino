import os
import re
from collections import Counter


PROCEDURE_KEYWORDS = (
    'proceso',
    'procesos',
    'procedimiento',
    'procedimientos',
)


def normalize_text(value):
    """Normalize spaces and basic separators in extracted text."""
    return re.sub(r'\s+', ' ', value or '').strip()


def extract_procedure_mentions(text):
    """Return the sentences mentioning legal processes or procedures."""
    sentences = re.split(r'(?<=[.;])\s+|\n+', text)
    matches = []

    for sentence in sentences:
        clean_sentence = normalize_text(sentence)
        if not clean_sentence:
            continue
        if not re.search(r'\b(?:' + '|'.join(PROCEDURE_KEYWORDS) + r')\b', clean_sentence, re.IGNORECASE):
            continue
        if len(clean_sentence.split()) < 4:
            continue
        matches.append(clean_sentence)

    return matches


def summarize_procedure_mentions(text, top_n=20):
    """Summarize repeated process/procedure phrases and return the most frequent ones."""
    mentions = extract_procedure_mentions(text)
    counts = Counter()

    for sentence in mentions:
        phrase_match = re.search(
            r'(?i)(?:[A-ZÁÉÍÓÚÑ][^.;\n]*?\s+)?(?:procesos?|procedimientos?)\b(?:\s+(?:de|del|para|por|administrativo|administrativos|ordinario|ordinarios|informativo|informativos|vecinal|vecinales|previa|previas|de evaluación|de consulta|de vigilancia|de inspección|de mediación|de revisión|de autorización|de acreditación|de resolución|de sanción|de cumplimiento|y|o))*(?:\s+[^.;\n]{0,220})?',
            sentence,
        )
        phrase = normalize_text(phrase_match.group(0)) if phrase_match else normalize_text(sentence)
        counts[phrase] += 1

    return counts.most_common(top_n)


if __name__ == '__main__':
    reviewed_text_path = 'leyes_cdmx/LEY_AMBIENTAL_DE_LA_CDMX_1.2_reviewed.txt'

    if not os.path.exists(reviewed_text_path):
        print(f'Reviewed text not found: {reviewed_text_path}')
        print('Run pdf_text_extractor.py first.')
        raise SystemExit(1)

    with open(reviewed_text_path, 'r', encoding='utf-8') as input_file:
        reviewed_text = input_file.read()

    print('\n--- Identifying legal processes and procedures ---')
    procedures = summarize_procedure_mentions(reviewed_text, top_n=20)

    if not procedures:
        print('No process/procedure references were found in the reviewed text.')
    else:
        for phrase, count in procedures:
            print(f'- {phrase}: {count}')
