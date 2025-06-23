import io
from typing import Literal

import PyPDF2
from app.openai_client import ask_gpt


def _pdf_to_text(data: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _plain_to_text(data: bytes, ext: Literal[".txt", ".md"]) -> str:
    return data.decode("utf-8", errors="ignore")


def _bytes_to_text(data: bytes, filename: str) -> str:
    filename = filename.lower()
    if filename.endswith(".pdf"):
        return _pdf_to_text(data)
    if filename.endswith((".txt", ".md")):
        return _plain_to_text(data, ".txt")
    raise ValueError("Unsupported file type for summarization")


async def summarize(file_bytes: bytes, filename: str) -> str:
    """
    Returns a concise summary (≈ 200 words) of the document.
    """
    text = _bytes_to_text(file_bytes, filename)[:10_000]  # safety cutoff
    prompt = (
        "Summarize the following document in ~200 words, preserving structure:\n\n"
        f"{text}"
    )
    # user_id is irrelevant for system-level summarization → pass placeholder
    return await ask_gpt("summary", prompt)

