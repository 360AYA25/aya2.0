import io
import PyPDF2


def read_txt(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def read_pdf(data: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(data))
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n".join(pages)

