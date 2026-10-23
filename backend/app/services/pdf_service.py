import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pymupdf as fitz
from backend.app.core.config import settings


class PDFExtractionError(Exception):
    """Base exception for PDF extraction issues."""
    pass


class PDFPasswordProtectedError(PDFExtractionError):
    """Raised when PDF is encrypted or requires a password."""
    pass


class PDFCorruptedError(PDFExtractionError):
    """Raised when PDF file is invalid, truncated, or unreadable."""
    pass


@dataclass
class ExtractedPage:
    """Represents text extracted from a single PDF page."""
    page_number: int  # 1-indexed
    text: str
    char_count: int


@dataclass
class PDFExtractionResult:
    """Full extraction outcome across all pages in a PDF."""
    pages: List[ExtractedPage]
    total_pages: int
    total_chars: int
    is_scanned: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class PDFService:
    """Service for extracting page-by-page text, metadata, and detecting scanned PDFs."""

    def __init__(
        self,
        min_extractable_text_chars: int = settings.MIN_EXTRACTABLE_TEXT_CHARS,
        scanned_page_min_chars: int = settings.SCANNED_PAGE_MIN_CHARS,
    ):
        self.min_extractable_text_chars = min_extractable_text_chars
        self.scanned_page_min_chars = scanned_page_min_chars

    def extract_text_from_path(self, file_path: str) -> PDFExtractionResult:
        """Extract text page by page from a file on disk."""
        if not os.path.exists(file_path):
            raise PDFCorruptedError(f"PDF file not found at path: {file_path}")

        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            raise PDFCorruptedError(f"Failed to open PDF document: {exc}") from exc

        return self._process_doc(doc)

    def extract_text_from_bytes(self, content: bytes) -> PDFExtractionResult:
        """Extract text page by page from raw bytes."""
        if not content:
            raise PDFCorruptedError("PDF content is empty.")

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise PDFCorruptedError(f"Failed to open PDF from byte stream: {exc}") from exc

        return self._process_doc(doc)

    def _process_doc(self, doc: fitz.Document) -> PDFExtractionResult:
        """Internal helper to process an opened fitz Document."""
        try:
            # Check for encryption or password protection
            if doc.is_encrypted or doc.needs_pass:
                raise PDFPasswordProtectedError("PDF is password-protected and cannot be extracted.")

            total_pages = doc.page_count
            if total_pages == 0:
                raise PDFCorruptedError("PDF document contains 0 pages.")

            pages: List[ExtractedPage] = []
            total_chars = 0

            for page_idx in range(total_pages):
                try:
                    page = doc.load_page(page_idx)
                    raw_text = page.get_text("text") or ""
                except Exception as exc:
                    raise PDFCorruptedError(
                        f"Error reading page {page_idx + 1} of PDF: {exc}"
                    ) from exc

                # Normalize text by stripping null bytes and non-printable noise
                cleaned_text = raw_text.replace("\x00", "")
                stripped_len = len(cleaned_text.strip())
                total_chars += stripped_len

                pages.append(
                    ExtractedPage(
                        page_number=page_idx + 1,
                        text=cleaned_text,
                        char_count=stripped_len,
                    )
                )

            # Heuristic for scanned PDF detection:
            # Insufficient extractable text overall or average per page
            is_scanned = (
                total_chars < self.min_extractable_text_chars
                or (total_pages > 0 and (total_chars / total_pages) < self.scanned_page_min_chars and total_chars < 100)
            )

            meta: Dict[str, Any] = {}
            if doc.metadata:
                meta = {
                    "title": doc.metadata.get("title") or "",
                    "author": doc.metadata.get("author") or "",
                    "subject": doc.metadata.get("subject") or "",
                    "creator": doc.metadata.get("creator") or "",
                    "producer": doc.metadata.get("producer") or "",
                }

            return PDFExtractionResult(
                pages=pages,
                total_pages=total_pages,
                total_chars=total_chars,
                is_scanned=is_scanned,
                metadata=meta,
            )
        finally:
            doc.close()


pdf_service = PDFService()
