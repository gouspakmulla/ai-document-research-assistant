import re
from dataclasses import dataclass
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.services.pdf_service import ExtractedPage


@dataclass
class DocumentChunkData:
    """Represents a chunk generated from a document page."""
    chunk_index: int  # 0-indexed sequential index across the entire document
    page_number: int  # 1-indexed source page number
    content: str
    token_count: int
    char_count: int


class ChunkingService:
    """Page-aware recursive chunking service that maintains document provenance."""

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
        min_chunk_size: int = settings.MIN_CHUNK_SIZE,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative.")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_pages(self, pages: List[ExtractedPage]) -> List[DocumentChunkData]:
        """Split a list of extracted pages into chunks while preserving page provenance."""
        chunks: List[DocumentChunkData] = []
        global_chunk_index = 0

        for page in pages:
            raw_text = page.text or ""
            clean_text = raw_text.strip()

            # Empty or whitespace-only pages yield 0 chunks, but page indexing remains intact
            if not clean_text:
                continue

            page_chunks = self.chunk_text(
                text=clean_text,
                page_number=page.page_number,
                start_chunk_index=global_chunk_index,
            )

            chunks.extend(page_chunks)
            global_chunk_index += len(page_chunks)

        return chunks

    def chunk_text(
        self,
        text: str,
        page_number: int = 1,
        start_chunk_index: int = 0,
    ) -> List[DocumentChunkData]:
        """Split text belonging to a single page into chunks."""
        clean_text = text.strip()
        if not clean_text:
            return []

        text_pieces = self._recursive_split(
            text=clean_text,
            separators=self.DEFAULT_SEPARATORS,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        result_chunks: List[DocumentChunkData] = []
        for idx, piece in enumerate(text_pieces):
            content = piece.strip()
            if not content:
                continue

            # Estimate token count (standard ~4 chars per token)
            token_count = max(1, len(content) // 4)

            result_chunks.append(
                DocumentChunkData(
                    chunk_index=start_chunk_index + idx,
                    page_number=page_number,
                    content=content,
                    token_count=token_count,
                    char_count=len(content),
                )
            )

        return result_chunks

    def _recursive_split(
        self,
        text: str,
        separators: List[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[str]:
        """Internal recursive splitting algorithm across linguistic boundaries."""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chosen_sep = ""
        for sep in separators:
            if sep in text:
                chosen_sep = sep
                break

        # Fallback to hard character-level slicing if no separator is present
        if chosen_sep == "":
            step = max(1, chunk_size - chunk_overlap)
            slices = []
            for i in range(0, len(text), step):
                chunk = text[i : i + chunk_size].strip()
                if chunk:
                    slices.append(chunk)
            return slices

        # Split text by chosen separator
        raw_splits = text.split(chosen_sep)
        sep_index = separators.index(chosen_sep)
        next_separators = separators[sep_index + 1 :]

        atomic_segments: List[str] = []
        for part in raw_splits:
            part_stripped = part.strip()
            if not part_stripped:
                continue

            if len(part_stripped) > chunk_size and next_separators:
                sub_segments = self._recursive_split(
                    text=part_stripped,
                    separators=next_separators,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                atomic_segments.extend(sub_segments)
            else:
                atomic_segments.append(part_stripped)

        # Merge atomic segments into target chunks with overlap
        chunks: List[str] = []
        current_segments: List[str] = []
        current_len = 0
        join_delimiter = chosen_sep if chosen_sep in ["\n\n", "\n", " "] else " "

        for segment in atomic_segments:
            seg_len = len(segment)
            delimiter_len = len(join_delimiter) if current_segments else 0
            tentative_len = current_len + delimiter_len + seg_len

            if tentative_len > chunk_size and current_segments:
                assembled_chunk = join_delimiter.join(current_segments).strip()
                if assembled_chunk:
                    chunks.append(assembled_chunk)

                # Extract overlap tail from the previous chunk
                overlap_text = (
                    assembled_chunk[-chunk_overlap:]
                    if len(assembled_chunk) > chunk_overlap
                    else assembled_chunk
                )
                # Attempt to snap overlap start to nearest word boundary
                space_pos = overlap_text.find(" ")
                if space_pos != -1 and space_pos < len(overlap_text) - 15:
                    overlap_text = overlap_text[space_pos + 1 :]

                current_segments = [overlap_text, segment] if overlap_text else [segment]
                current_len = sum(len(s) for s in current_segments) + (
                    len(join_delimiter) if len(current_segments) > 1 else 0
                )
            else:
                current_segments.append(segment)
                current_len = tentative_len

        if current_segments:
            final_chunk = join_delimiter.join(current_segments).strip()
            if final_chunk:
                chunks.append(final_chunk)

        return chunks


chunking_service = ChunkingService()
