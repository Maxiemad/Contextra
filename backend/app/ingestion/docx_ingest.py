"""Extract text from DOCX."""
from pathlib import Path

from docx import Document as DocxDocument


def extract_docx_text(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
