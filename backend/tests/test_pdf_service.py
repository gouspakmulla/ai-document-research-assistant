import os
import tempfile
import pytest
import pymupdf as fitz
from backend.app.services.pdf_service import (
    PDFService,
    PDFCorruptedError,
    PDFPasswordProtectedError,
)


@pytest.fixture
def temp_pdf_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_pdf_extraction_page_by_page(temp_pdf_dir):
    """Test extracting text page by page with accurate page numbering and metadata."""
    pdf_path = os.path.join(temp_pdf_dir, "test_multi_page.pdf")
    doc = fitz.open()

    page1 = doc.new_page()
    page1.insert_text((50, 72), "This is page one discussing deep learning theory.")

    page2 = doc.new_page()
    page2.insert_text((50, 72), "This is page two detailing optimization techniques and adam optimizer.")

    doc.set_metadata({"title": "Deep Learning Research", "author": "Research Assistant"})
    doc.save(pdf_path)
    doc.close()

    service = PDFService(min_extractable_text_chars=20)
    result = service.extract_text_from_path(pdf_path)

    assert result.total_pages == 2
    assert len(result.pages) == 2
    assert not result.is_scanned
    assert result.pages[0].page_number == 1
    assert "page one" in result.pages[0].text
    assert result.pages[1].page_number == 2
    assert "page two" in result.pages[1].text
    assert result.metadata.get("title") == "Deep Learning Research"
    assert result.metadata.get("author") == "Research Assistant"


def test_pdf_scanned_detection(temp_pdf_dir):
    """Test that a PDF with negligible/empty text is detected as scanned."""
    pdf_path = os.path.join(temp_pdf_dir, "scanned_doc.pdf")
    doc = fitz.open()
    # Add a blank page with no text (representing a scanned image without OCR)
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    service = PDFService(min_extractable_text_chars=50)
    result = service.extract_text_from_path(pdf_path)

    assert result.total_pages == 1
    assert result.is_scanned is True
    assert result.total_chars == 0


def test_pdf_corrupted_file_handling(temp_pdf_dir):
    """Invalid or truncated PDF bytes must raise PDFCorruptedError."""
    corrupted_path = os.path.join(temp_pdf_dir, "corrupt.pdf")
    with open(corrupted_path, "wb") as f:
        f.write(b"%PDF-1.5 this is not a valid pdf structure at all")

    service = PDFService()
    with pytest.raises(PDFCorruptedError):
        service.extract_text_from_path(corrupted_path)


def test_pdf_password_protected_handling(temp_pdf_dir):
    """Password-protected PDFs must raise PDFPasswordProtectedError."""
    encrypted_path = os.path.join(temp_pdf_dir, "secret.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Top secret content.")
    doc.save(
        encrypted_path,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="secret123",
        owner_pw="owner123",
    )
    doc.close()

    service = PDFService()
    with pytest.raises(PDFPasswordProtectedError):
        service.extract_text_from_path(encrypted_path)


def test_pdf_bytes_extraction():
    """Verify extraction directly from in-memory byte buffer."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "In-memory buffer extraction verification.")
    pdf_bytes = doc.tobytes()
    doc.close()

    service = PDFService(min_extractable_text_chars=10)
    result = service.extract_text_from_bytes(pdf_bytes)

    assert result.total_pages == 1
    assert not result.is_scanned
    assert "In-memory buffer" in result.pages[0].text
