import pytest
from backend.app.services.chunking_service import ChunkingService, DocumentChunkData
from backend.app.services.pdf_service import ExtractedPage


def test_chunking_service_parameter_validation():
    """Ensure invalid parameters are rejected with ValueError."""
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        ChunkingService(chunk_size=0)

    with pytest.raises(ValueError, match="chunk_overlap cannot be negative"):
        ChunkingService(chunk_size=500, chunk_overlap=-1)

    with pytest.raises(ValueError, match="chunk_overlap must be strictly less than chunk_size"):
        ChunkingService(chunk_size=500, chunk_overlap=500)


def test_chunking_single_page_under_limit():
    """Short text under chunk_size should produce exactly one chunk."""
    service = ChunkingService(chunk_size=500, chunk_overlap=50)
    text = "This is a concise research summary on transformer architectures."
    chunks = service.chunk_text(text, page_number=1)

    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == text
    assert chunks[0].char_count == len(text)
    assert chunks[0].token_count > 0


def test_chunking_boundaries_and_overlap():
    """Ensure multi-paragraph text is split cleanly with overlap preserved."""
    service = ChunkingService(chunk_size=200, chunk_overlap=40)
    paragraphs = [
        "Paragraph One discusses the foundational premise of deep retrieval engines.",
        "Paragraph Two outlines vector similarity search using hierarchical navigable small worlds.",
        "Paragraph Three describes reranking strategies using cross-encoders.",
        "Paragraph Four summarizes empirical evaluations across benchmark datasets.",
    ]
    full_text = "\n\n".join(paragraphs)
    chunks = service.chunk_text(full_text, page_number=2, start_chunk_index=5)

    assert len(chunks) > 1
    assert chunks[0].page_number == 2
    assert chunks[0].chunk_index == 5
    assert chunks[1].chunk_index == 6

    # Verify that consecutive chunks share overlap content
    # The start of chunk 1 should contain content from the end of chunk 0
    overlap_found = False
    for i in range(len(chunks) - 1):
        c1_tail = chunks[i].content[-30:]
        c2_head = chunks[i + 1].content[:50]
        # Check for matching words in the overlap zone
        tail_words = set(c1_tail.split())
        head_words = set(c2_head.split())
        common = tail_words.intersection(head_words)
        if len(common) >= 1:
            overlap_found = True
            break

    assert overlap_found, "Consecutive chunks should exhibit textual overlap."


def test_chunking_empty_and_whitespace_pages():
    """Empty and whitespace pages must be omitted from chunks without corrupting page numbers."""
    service = ChunkingService(chunk_size=300, chunk_overlap=50)
    pages = [
        ExtractedPage(page_number=1, text="Page 1: Title and Abstract of the study.", char_count=40),
        ExtractedPage(page_number=2, text="   \n\n\t   ", char_count=0),  # Blank page
        ExtractedPage(page_number=3, text="", char_count=0),  # Completely empty
        ExtractedPage(page_number=4, text="Page 4: Empirical results and tables.", char_count=36),
    ]

    chunks = service.chunk_pages(pages)

    assert len(chunks) == 2
    # Verify page provenance
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert "Page 1" in chunks[0].content

    assert chunks[1].page_number == 4
    assert chunks[1].chunk_index == 1
    assert "Page 4" in chunks[1].content


def test_chunking_continuous_long_text_without_breaks():
    """Ensure text without whitespace or standard delimiters splits via character fallback without loops."""
    service = ChunkingService(chunk_size=100, chunk_overlap=20)
    long_unbroken = "A" * 350
    chunks = service.chunk_text(long_unbroken, page_number=1)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.page_number == 1
        assert len(chunk.content) <= 100


def test_chunk_page_number_accuracy_across_document():
    """Validate accurate 1-indexed page references for multi-page documents."""
    service = ChunkingService(chunk_size=150, chunk_overlap=30)
    pages = [
        ExtractedPage(page_number=1, text="Introduction on page one. " * 8, char_count=216),
        ExtractedPage(page_number=2, text="Methodology on page two. " * 8, char_count=208),
        ExtractedPage(page_number=3, text="Discussion on page three. " * 8, char_count=216),
    ]

    chunks = service.chunk_pages(pages)

    p1_chunks = [c for c in chunks if c.page_number == 1]
    p2_chunks = [c for c in chunks if c.page_number == 2]
    p3_chunks = [c for c in chunks if c.page_number == 3]

    assert len(p1_chunks) >= 2
    assert len(p2_chunks) >= 2
    assert len(p3_chunks) >= 2

    # Verify indices are monotonically increasing
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
