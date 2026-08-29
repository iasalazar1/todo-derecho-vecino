from collections import Counter
import os

import spacy


def load_spanish_model():
    """Load the Spanish spaCy model, downloading it when necessary."""
    try:
        return spacy.load('es_core_news_sm')
    except OSError:
        print("SpaCy 'es_core_news_sm' model not found. Downloading...")
        spacy.cli.download('es_core_news_sm')
        return spacy.load('es_core_news_sm')


def extract_actor_entities(reviewed_text, nlp_model):
    """Return the most frequent people, organizations, and locations."""
    document = nlp_model(reviewed_text)
    entity_names = [
        entity.text
        for entity in document.ents
        if entity.label_ in ['ORG', 'PER', 'GPE', 'LOC']
    ]
    return Counter(entity_names).most_common(20)


if __name__ == '__main__':
    reviewed_text_path = 'leyes_cdmx/LEY_AMBIENTAL_DE_LA_CDMX_1.2_reviewed.txt'

    if not os.path.exists(reviewed_text_path):
        print(f"Reviewed text not found: {reviewed_text_path}")
        print('Run pdf_text_extractor.py first.')
        raise SystemExit(1)

    with open(reviewed_text_path, 'r', encoding='utf-8') as input_file:
        reviewed_text = input_file.read()

    nlp = load_spanish_model()
    print('\n--- Extracting Actor or Government Entities (Autoridad) ---')
    actors = extract_actor_entities(reviewed_text, nlp)
    for entity, count in actors:
        print(f'- {entity}: {count}')

    print('\nTip: run procedimiento_ner.py to keep the process/procedure extraction phase separate.')
