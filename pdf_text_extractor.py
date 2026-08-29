import os
import re

import PyPDF2


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF while preserving page boundaries."""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ''
                text += f"\n\n--- PAGE {page_num} ---\n\n{page_text}"
    except FileNotFoundError:
        print(f"Error: The file '{pdf_path}' was not found.")
    except Exception as error:
        print(f"An error occurred during PDF extraction: {error}")
    return text


def clean_text(text):
    """Normalize whitespace while retaining the extracted text for review."""
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def prepare_reviewed_text(pdf_path):
    """Create the raw extraction and reviewed-text files for a PDF."""
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text:
        return None

    extracted_text_path = os.path.splitext(pdf_path)[0] + '_extracted.txt'
    with open(extracted_text_path, 'w', encoding='utf-8') as output_file:
        output_file.write(raw_text)

    reviewed_text_path = os.path.splitext(pdf_path)[0] + '_reviewed.txt'
    if not os.path.exists(reviewed_text_path):
        with open(reviewed_text_path, 'w', encoding='utf-8') as output_file:
            output_file.write(clean_text(raw_text))
        print(f"Review the extracted text here: {reviewed_text_path}")
        print("Correct OCR errors, save the file, and run this script again.")
        return None

    return reviewed_text_path


if __name__ == '__main__':
    pdf_path = '/home/ismael/todo-derecho-vecino/leyes_cdmx/LEY_AMBIENTAL_DE_LA_CDMX_1.2.pdf'
    print(f'Processing PDF: {pdf_path}')
    reviewed_text_path = prepare_reviewed_text(pdf_path)
    if reviewed_text_path:
        print(f'Reviewed text ready for analysis: {reviewed_text_path}')
