import io
from fastapi import HTTPException


def parse_file(filename: str, content: bytes) -> str:
    name = filename.lower()

    if name.endswith(".txt"):
        return content.decode("utf-8", errors="replace")

    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            raise HTTPException(status_code=500, detail="pypdf not installed")
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if name.endswith(".docx"):
        try:
            from docx import Document
        except ImportError:
            raise HTTPException(status_code=500, detail="python-docx not installed")
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported file type. Upload a .txt, .pdf, or .docx file.",
    )
