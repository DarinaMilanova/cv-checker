import io
from pdfminer.high_level import extract_text as pdf_text
from docx import Document
from striprtf.striprtf import rtf_to_text


def extract_text_any(uploaded_file) -> str:
    name = (uploaded_file.name or "").lower()
    data = uploaded_file.read()
    uploaded_file.seek(0)

    if name.endswith(".pdf"):
        return pdf_text(io.BytesIO(data))

    if name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)

    if name.endswith(".rtf"):
        raw = data.decode("utf-8", errors="ignore")
        return rtf_to_text(raw)

    return data.decode("utf-8", errors="ignore")
