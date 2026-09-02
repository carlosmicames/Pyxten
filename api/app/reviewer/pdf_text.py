"""
Reading PDFs: hashing, page counting, and per-page text extraction.

Everything here is deterministic. No model is involved, which matters because
these are the signals the confidence band is later derived from - if the band
were itself a model output it would be worth nothing.
"""
from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

# A page with fewer characters than this is treated as having no usable text.
# Scanned pages typically yield a handful of stray characters, not zero.
MIN_CHARS_FOR_TEXT_PAGE = 40

# Share of pages that must carry text before we call the whole document
# text-bearing rather than partial.
TEXT_PAGE_RATIO_FOR_FULL = 0.8


@dataclass
class PageText:
    page_no: int  # 1-indexed, matching how a person cites a page
    text: str
    char_count: int
    extraction_method: str  # 'pdf_text' | 'ninguno'


@dataclass
class PdfAnalysis:
    sha256: str
    page_count: Optional[int]
    pages: List[PageText] = field(default_factory=list)
    total_chars: int = 0
    # 'texto_incrustado' | 'parcial' | 'sin_texto' | 'error'
    ocr_status: str = "pendiente"
    error: Optional[str] = None

    @property
    def readable(self) -> bool:
        """Is there enough text to classify from, without rendering the pages?"""
        return self.ocr_status in ("texto_incrustado", "parcial") and self.total_chars > 0

    def combined_text(self, max_chars: int = 60_000) -> str:
        """
        All page text, page-delimited so a model's answer can cite a page number.
        Truncated at the end rather than the middle - the first pages of a permit
        document carry the identifying content.
        """
        chunks = []
        used = 0
        for page in self.pages:
            if not page.text.strip():
                continue
            header = f"\n--- Pagina {page.page_no} ---\n"
            piece = header + page.text
            if used + len(piece) > max_chars:
                chunks.append(header + page.text[: max(0, max_chars - used - len(header))])
                break
            chunks.append(piece)
            used += len(piece)
        return "".join(chunks).strip()

    def first_page_text(self) -> str:
        for page in self.pages:
            if page.text.strip():
                return f"--- Pagina {page.page_no} ---\n{page.text}"
        return ""

    def first_text_page_no(self) -> Optional[int]:
        for page in self.pages:
            if page.text.strip():
                return page.page_no
        return None


def sha256_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def analyze_pdf(content: bytes) -> PdfAnalysis:
    """
    Hash, count pages, and pull embedded text page by page.

    A PDF that cannot be parsed is reported as an error rather than raised: one
    bad file in a five-file upload should not lose the other four.
    """
    digest = sha256_of(content)

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:  # pypdf raises a variety of parse errors
        logger.warning("Could not parse PDF: %s", exc)
        return PdfAnalysis(
            sha256=digest,
            page_count=None,
            ocr_status="error",
            error=f"No se pudo leer el PDF: {exc}",
        )

    # An encrypted file may still open with an empty password.
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:
            return PdfAnalysis(
                sha256=digest,
                page_count=None,
                ocr_status="error",
                error="El PDF esta protegido con contrasena.",
            )

    pages: List[PageText] = []
    total_chars = 0
    text_pages = 0

    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            logger.warning("Text extraction failed on page %s: %s", index, exc)
            text = ""

        text = text.strip()
        char_count = len(text)
        has_text = char_count >= MIN_CHARS_FOR_TEXT_PAGE

        if has_text:
            text_pages += 1
        total_chars += char_count

        pages.append(
            PageText(
                page_no=index,
                text=text,
                char_count=char_count,
                extraction_method="pdf_text" if has_text else "ninguno",
            )
        )

    page_count = len(pages)

    if page_count == 0:
        ocr_status = "error"
    elif text_pages == 0:
        ocr_status = "sin_texto"
    elif text_pages / page_count >= TEXT_PAGE_RATIO_FOR_FULL:
        ocr_status = "texto_incrustado"
    else:
        ocr_status = "parcial"

    return PdfAnalysis(
        sha256=digest,
        page_count=page_count,
        pages=pages,
        total_chars=total_chars,
        ocr_status=ocr_status,
        error=None if page_count else "El PDF no contiene paginas.",
    )


def first_pages_pdf(content: bytes, page_limit: int = 4) -> Optional[bytes]:
    """
    A new PDF containing only the first few pages of `content`.

    Used when a document has no extractable text: the opening pages go to the
    model as an image-bearing PDF so a scan can still be classified, without
    sending a 200-page package for a question the cover page answers.
    Returns None if the file cannot be rewritten.
    """
    try:
        reader = PdfReader(io.BytesIO(content))
        writer = PdfWriter()
        for page in reader.pages[:page_limit]:
            writer.add_page(page)

        buffer = io.BytesIO()
        writer.write(buffer)
        return buffer.getvalue()
    except Exception as exc:
        logger.warning("Could not slice PDF to first %s pages: %s", page_limit, exc)
        return None
