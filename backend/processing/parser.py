import fitz # PyMuPDF
import docx
import os
import re

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), max(1, chunk_size - overlap)):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def extract_text_from_pdf(filepath: str) -> str:
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(filepath: str) -> str:
    doc = docx.Document(filepath)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_text_from_txt(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def process_files(files):
    chunks = []
    for file in files:
        filepath = file['path']
        mime_type = file['mimeType']
        ext = os.path.splitext(filepath)[1].lower()

        try:
            text = ""
            if ext == '.pdf':
                text = extract_text_from_pdf(filepath)
            elif ext == '.docx':
                text = extract_text_from_docx(filepath)
            elif ext == '.txt':
                text = extract_text_from_txt(filepath)
            else:
                print(f"Unsupported file extension: {ext}")
                continue

            cleaned_text = clean_text(text)
            if not cleaned_text:
                continue

            file_chunks = chunk_text(cleaned_text, chunk_size=500, overlap=50)
            for i, c in enumerate(file_chunks):
                chunks.append({
                    "id": f"{file['id']}_chunk_{i}",
                    "doc_id": file['id'],
                    "text": c
                })
        except Exception as e:
            print(f"Error processing file {filepath}: {e}")

    return chunks
