import hashlib
import os
import re
import uuid
from typing import List, Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.services.pdf_service import (
    pdf_service,
    PDFService,
    PDFCorruptedError,
    PDFPasswordProtectedError,
    PDFExtractionError,
)
from backend.app.services.chunking_service import chunking_service, ChunkingService
from backend.app.services.embedding_service import embedding_service, EmbeddingService
from backend.app.services.storage_service import (
    storage_service,
    StorageService,
    StorageError,
    StorageFileNotFoundError,
    StorageValidationError,
)


class DocumentValidationError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class DocumentService:
    def __init__(
        self,
        pdf_svc: PDFService = pdf_service,
        chunk_svc: ChunkingService = chunking_service,
        emb_svc: EmbeddingService = embedding_service,
        storage_svc: StorageService = storage_service,
    ):
        self.pdf_service = pdf_svc
        self.chunking_service = chunk_svc
        self.embedding_service = emb_svc
        self.storage_service = storage_svc

    def sanitize_filename(self, filename: Optional[str]) -> str:
        """Sanitize client-supplied filename to prevent path traversal and shell exploits."""
        if not filename or not filename.strip():
            return "document.pdf"

        # Extract only the base name (strip directory components)
        base = os.path.basename(filename.strip())
        # Remove null bytes and control characters
        base = re.sub(r"[\x00-\x1f\x7f]", "", base)
        # Replace dangerous path characters
        base = re.sub(r'[\\/:*?"<>|]', "_", base)
        # Prevent hidden files
        base = base.lstrip(".")
        # Truncate length
        if len(base) > 250:
            name, ext = os.path.splitext(base)
            base = name[:240] + ext

        return base or "document.pdf"

    def validate_file(
        self,
        filename: str,
        content: bytes,
        content_type: Optional[str] = None,
    ) -> None:
        """Validate PDF file extension, MIME type, magic bytes, and file size."""
        # 1. Extension check
        _, ext = os.path.splitext(filename.lower())
        allowed_exts = [e.lower() for e in settings.ALLOWED_EXTENSIONS]
        if ext != ".pdf" or ext not in allowed_exts:
            raise DocumentValidationError("Invalid file extension. Only .pdf files are supported.")

        # 2. MIME type check
        if content_type:
            normalized_mime = content_type.lower().split(";")[0].strip()
            if normalized_mime not in settings.ALLOWED_MIME_TYPES:
                raise DocumentValidationError(
                    f"Unsupported MIME type '{normalized_mime}'. Allowed types: {', '.join(settings.ALLOWED_MIME_TYPES)}"
                )

        # 3. Magic bytes check (%PDF-)
        if not content.startswith(b"%PDF-"):
            raise DocumentValidationError(
                "Invalid PDF file header. File does not start with standard %PDF- magic bytes."
            )

        # 4. File size limit
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            too_large_code = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)
            raise DocumentValidationError(
                f"File size ({len(content) / (1024 * 1024):.2f}MB) exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_MB}MB.",
                status_code=too_large_code,
            )

    async def ingest_uploaded_file(
        self,
        file: UploadFile,
        user_id: str,
        db: AsyncSession,
    ) -> Document:
        """Full pipeline: Validate -> Store -> Extract -> Scanned check -> Chunk -> Index."""
        content = await file.read()
        raw_filename = file.filename or "document.pdf"

        # Validate file before sanitizing
        self.validate_file(
            filename=raw_filename,
            content=content,
            content_type=file.content_type,
        )

        sanitized_name = self.sanitize_filename(raw_filename)

        # Upload file through persistent storage provider
        try:
            storage_path = await self.storage_service.upload_document_file(
                user_id=user_id,
                filename=sanitized_name,
                content=content,
                content_type=file.content_type or "application/pdf",
            )
        except StorageValidationError as exc:
            raise DocumentValidationError(str(exc))
        except StorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Storage upload failed: {str(exc)}",
            )

        # Calculate SHA256 checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Create initial Document record in DB with rollback/cleanup guard
        doc = Document(
            id=str(uuid.uuid4()),
            user_id=user_id,
            filename=sanitized_name,
            storage_path=storage_path,
            file_size_bytes=len(content),
            mime_type=file.content_type or "application/pdf",
            page_count=0,
            processing_status="PENDING",
            checksum_sha256=checksum,
        )
        try:
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
        except Exception as exc:
            await db.rollback()
            try:
                await self.storage_service.delete_file(storage_path)
            except Exception:
                pass
            raise exc

        # Run extraction & chunking pipeline
        await self.process_document_pipeline(doc, db)
        return doc

    async def process_document_pipeline(
        self,
        doc: Document,
        db: AsyncSession,
    ) -> Document:
        """Executes the extraction and chunking pipeline with error recovery."""
        try:
            # 1. Extraction Stage
            doc.processing_status = "EXTRACTING"
            await db.commit()

            # Retrieve content from persistent storage backend
            try:
                pdf_bytes = await self.storage_service.download_file(doc.storage_path)
            except StorageFileNotFoundError as exc:
                doc.processing_status = "FAILED"
                doc.error_message = f"PDF file not found in storage: {str(exc)}"
                await db.commit()
                await db.refresh(doc)
                return doc
            except Exception as exc:
                doc.processing_status = "FAILED"
                doc.error_message = f"Failed to retrieve PDF from storage: {str(exc)}"
                await db.commit()
                await db.refresh(doc)
                return doc

            extraction_result = self.pdf_service.extract_text_from_bytes(pdf_bytes)
            doc.page_count = extraction_result.total_pages

            # 2. Scanned PDF Check
            if extraction_result.is_scanned:
                doc.processing_status = "OCR_REQUIRED"
                doc.error_message = (
                    "Scanned PDF detected. Insufficient extractable text; OCR is required."
                )
                await db.commit()
                await db.refresh(doc)
                return doc

            # 3. Chunking Stage
            doc.processing_status = "CHUNKING"
            await db.commit()

            chunks_data = self.chunking_service.chunk_pages(extraction_result.pages)

            # 4. Embedding Stage
            doc.processing_status = "EMBEDDING"
            await db.commit()

            chunk_texts = [c.content for c in chunks_data]
            embeddings = await self.embedding_service.embed_chunks(chunk_texts)

            # 5. Persist chunks with embeddings in a single transaction
            for chunk_data, emb in zip(chunks_data, embeddings):
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc.id,
                    user_id=doc.user_id,
                    chunk_index=chunk_data.chunk_index,
                    page_number=chunk_data.page_number,
                    content=chunk_data.content,
                    token_count=chunk_data.token_count,
                    embedding=emb,
                )
                db.add(chunk)

            # 6. Ready Stage
            doc.processing_status = "READY"
            doc.error_message = None
            await db.commit()
            await db.refresh(doc)
            return doc

        except PDFPasswordProtectedError as exc:
            doc.processing_status = "FAILED"
            doc.error_message = str(exc)
            await db.commit()
            await db.refresh(doc)
            return doc

        except PDFCorruptedError as exc:
            doc.processing_status = "FAILED"
            doc.error_message = str(exc)
            await db.commit()
            await db.refresh(doc)
            return doc

        except Exception as exc:
            await db.rollback()
            # Clean up any partial chunks created
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
            )
            doc.processing_status = "FAILED"
            doc.error_message = f"Processing pipeline failed: {str(exc)}"
            await db.commit()
            await db.refresh(doc)
            return doc

    async def get_user_document(
        self,
        document_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> Document:
        """Fetch a single document strictly verifying tenant ownership."""
        query = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        res = await db.execute(query)
        doc = res.scalars().first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied.",
            )
        return doc

    async def delete_user_document(
        self,
        document_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> None:
        """Delete document record and associated storage file."""
        doc = await self.get_user_document(document_id, user_id, db)

        # Remove physical / cloud storage file
        if doc.storage_path:
            try:
                await self.storage_service.delete_file(doc.storage_path)
            except Exception:
                pass  # Do not block database record deletion if storage delete errors

        await db.delete(doc)
        await db.commit()

    async def get_document_content(
        self,
        document_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> Tuple[Document, bytes]:
        """Get document and downloaded content bytes for authenticated streaming."""
        doc = await self.get_user_document(document_id, user_id, db)
        if not doc.storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document has no storage path.",
            )
        try:
            content = await self.storage_service.download_file(doc.storage_path)
            return doc, content
        except StorageFileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF storage file not found on server.",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve PDF from storage: {str(exc)}",
            )

    async def get_document_pdf_path(
        self,
        document_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> Tuple[Document, str]:
        """Get document and validated disk path for local PDF streaming."""
        doc = await self.get_user_document(document_id, user_id, db)
        if not doc.storage_path or not os.path.exists(doc.storage_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF storage file not found on server.",
            )
        return doc, doc.storage_path

    async def get_document_chunks(
        self,
        document_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> List[DocumentChunk]:
        """Retrieve chunks belonging to user document ordered by index."""
        # Ensure user owns document
        await self.get_user_document(document_id, user_id, db)

        query = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.user_id == user_id,
            )
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())


document_service = DocumentService()
