import abc
import os
import re
import uuid
from contextlib import asynccontextmanager
from typing import Optional, Dict, Tuple, AsyncIterator
import httpx
from backend.app.core.config import settings


class StorageError(Exception):
    """Base exception for all storage-related errors."""
    pass


class StorageFileNotFoundError(StorageError):
    """Raised when an object or file cannot be located in the storage system."""
    pass


class StorageValidationError(StorageError):
    """Raised when a storage path or object key violates security constraints."""
    pass


class StorageConfigurationError(StorageError):
    """Raised when the storage provider lacks required credentials or environment configuration."""
    pass


class BaseStorageProvider(abc.ABC):
    """Abstract interface defining the contract for all persistent document storage providers."""

    @abc.abstractmethod
    async def upload_file(
        self,
        destination_path: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload file bytes to the storage backend.

        Args:
            destination_path: Destination path or object key within the storage provider.
            content: Raw binary content to persist.
            content_type: MIME content type of the file.

        Returns:
            The canonical storage path / URI identifier to store in the database.
        """
        pass

    @abc.abstractmethod
    async def download_file(self, storage_path: str) -> bytes:
        """Retrieve file bytes from the storage backend.

        Args:
            storage_path: Storage path or URI identifying the file.

        Returns:
            Raw bytes of the document.

        Raises:
            StorageFileNotFoundError: If the document is not found.
            StorageError: If download fails due to network or provider errors.
        """
        pass

    @abc.abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """Delete a file from the storage backend.

        Args:
            storage_path: Storage path or URI identifying the file.

        Returns:
            True if deleted or already absent, False if nonexistent.
        """
        pass

    @abc.abstractmethod
    async def file_exists(self, storage_path: str) -> bool:
        """Check whether a file exists in the storage backend."""
        pass


class LocalStorageProvider(BaseStorageProvider):
    """Local filesystem storage provider for offline development, staging, and legacy records."""

    def __init__(self, base_dir: Optional[str] = None):
        self._custom_base_dir = base_dir

    @property
    def base_dir(self) -> str:
        """Dynamically evaluate storage directory to support runtime overrides in tests."""
        d = self._custom_base_dir or settings.STORAGE_DIR
        return os.path.abspath(d)

    def _resolve_safe_path(self, destination_path: str) -> str:
        """Resolve path ensuring it stays strictly within the configured storage directory."""
        if not destination_path or not destination_path.strip():
            raise StorageValidationError("Storage path cannot be empty.")

        clean = destination_path.strip().replace("\\", "/").lstrip("/")
        if ".." in clean.split("/"):
            raise StorageValidationError(f"Path traversal detected in destination path: {destination_path}")

        target = os.path.abspath(os.path.join(self.base_dir, clean))
        base = self.base_dir

        if os.path.commonpath([base, target]) != base:
            raise StorageValidationError(f"Path traversal detected outside storage root: {destination_path}")

        return target

    async def upload_file(
        self,
        destination_path: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        target = self._resolve_safe_path(destination_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(content)
        return target

    async def download_file(self, storage_path: str) -> bytes:
        if not storage_path or not storage_path.strip():
            raise StorageFileNotFoundError("Empty storage path.")

        # 1. Direct path check (handles absolute paths and relative paths matching working directory)
        if os.path.exists(storage_path) and os.path.isfile(storage_path):
            with open(storage_path, "rb") as f:
                return f.read()

        # 2. Check within base_dir
        try:
            target = self._resolve_safe_path(storage_path)
            if os.path.exists(target) and os.path.isfile(target):
                with open(target, "rb") as f:
                    return f.read()
        except StorageValidationError:
            pass

        # 3. Check filename only inside base_dir (for legacy records)
        filename_only = os.path.basename(storage_path)
        legacy_target = os.path.join(self.base_dir, filename_only)
        if os.path.exists(legacy_target) and os.path.isfile(legacy_target):
            with open(legacy_target, "rb") as f:
                return f.read()

        raise StorageFileNotFoundError(f"Local storage file not found at: {storage_path}")

    async def delete_file(self, storage_path: str) -> bool:
        if not storage_path or not storage_path.strip():
            return False

        path_to_try = storage_path
        if not (os.path.exists(path_to_try) and os.path.isfile(path_to_try)):
            try:
                target = self._resolve_safe_path(storage_path)
                if os.path.exists(target) and os.path.isfile(target):
                    path_to_try = target
            except StorageValidationError:
                filename_only = os.path.basename(storage_path)
                legacy_target = os.path.join(self.base_dir, filename_only)
                if os.path.exists(legacy_target) and os.path.isfile(legacy_target):
                    path_to_try = legacy_target
                else:
                    return False

        if os.path.exists(path_to_try) and os.path.isfile(path_to_try):
            try:
                os.remove(path_to_try)
                return True
            except OSError as exc:
                raise StorageError(f"Failed to delete local file '{path_to_try}': {exc}") from exc

        return False

    async def file_exists(self, storage_path: str) -> bool:
        if not storage_path or not storage_path.strip():
            return False
        if os.path.exists(storage_path) and os.path.isfile(storage_path):
            return True
        try:
            target = self._resolve_safe_path(storage_path)
            if os.path.exists(target) and os.path.isfile(target):
                return True
        except StorageValidationError:
            pass
        legacy_target = os.path.join(self.base_dir, os.path.basename(storage_path))
        return os.path.exists(legacy_target) and os.path.isfile(legacy_target)


class SupabaseStorageProvider(BaseStorageProvider):
    """Production persistent storage provider using private Supabase Storage buckets.

    Accesses Supabase Storage via server-side credentials only (SUPABASE_SERVICE_ROLE_KEY).
    Never exposes credentials or direct bucket URLs to frontend or client applications.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.supabase_url = (supabase_url or settings.SUPABASE_URL or "").rstrip("/")
        self.service_role_key = service_role_key or settings.SUPABASE_SERVICE_ROLE_KEY or ""
        self.bucket_name = bucket_name or settings.SUPABASE_STORAGE_BUCKET or "documents"
        self.timeout = timeout_seconds or settings.SUPABASE_STORAGE_TIMEOUT_SECONDS
        self._external_client = client

        if not self.supabase_url or not self.service_role_key:
            raise StorageConfigurationError(
                "SupabaseStorageProvider requires both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                "to be configured in the backend environment."
            )

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._external_client is not None:
            yield self._external_client
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                yield client

    def _get_headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apiKey": self.service_role_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _parse_path(self, storage_path: str) -> Tuple[str, str]:
        """Extract bucket name and sanitized object path from storage path or URI."""
        if not storage_path or not storage_path.strip():
            raise StorageValidationError("Storage path cannot be empty.")

        clean = storage_path.strip()
        if clean.startswith("supabase://"):
            raw = clean[len("supabase://"):]
            parts = raw.split("/", 1)
            if len(parts) == 2:
                bucket, obj_key = parts[0], parts[1].lstrip("/")
            else:
                bucket, obj_key = self.bucket_name, parts[0].lstrip("/")
        else:
            clean_rel = clean.replace("\\", "/").lstrip("/")
            parts = clean_rel.split("/", 1)
            if len(parts) == 2 and parts[0] == self.bucket_name:
                bucket, obj_key = parts[0], parts[1].lstrip("/")
            else:
                bucket, obj_key = self.bucket_name, clean_rel

        # Guard against path traversal in object key
        if ".." in obj_key.split("/"):
            raise StorageValidationError(f"Path traversal detected in Supabase object key: {storage_path}")

        return bucket, obj_key

    async def upload_file(
        self,
        destination_path: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        clean_path = destination_path.replace("\\", "/").lstrip("/")
        if ".." in clean_path.split("/"):
            raise StorageValidationError(f"Path traversal detected in destination path: {destination_path}")

        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{clean_path}"
        headers = self._get_headers(content_type=content_type)
        headers["x-upsert"] = "false"

        async with self._get_client() as client:
            try:
                res = await client.post(url, content=content, headers=headers)
            except httpx.RequestError as exc:
                raise StorageError(f"Network error communicating with Supabase Storage: {exc}") from exc

            if res.status_code in (200, 201):
                return f"supabase://{self.bucket_name}/{clean_path}"
            elif res.status_code == 404:
                raise StorageError(
                    f"Supabase Storage bucket '{self.bucket_name}' not found. "
                    "Ensure the private bucket exists in the Supabase dashboard."
                )
            elif res.status_code in (401, 403):
                raise StorageError(
                    "Supabase Storage authentication failed. Check SUPABASE_SERVICE_ROLE_KEY."
                )
            elif res.status_code == 409:
                raise StorageError(
                    f"Object already exists in Supabase bucket '{self.bucket_name}': {clean_path}"
                )
            else:
                raise StorageError(
                    f"Supabase Storage upload failed with status {res.status_code}: {res.text}"
                )

    async def download_file(self, storage_path: str) -> bytes:
        bucket, obj_key = self._parse_path(storage_path)
        headers = self._get_headers()

        async with self._get_client() as client:
            # 1. Try authenticated download endpoint (for private buckets)
            auth_url = f"{self.supabase_url}/storage/v1/object/authenticated/{bucket}/{obj_key}"
            try:
                res = await client.get(auth_url, headers=headers)
                if res.status_code == 200:
                    return res.content
                if res.status_code == 404:
                    # 2. Fallback to standard object endpoint
                    std_url = f"{self.supabase_url}/storage/v1/object/{bucket}/{obj_key}"
                    std_res = await client.get(std_url, headers=headers)
                    if std_res.status_code == 200:
                        return std_res.content
                    if std_res.status_code == 404:
                        raise StorageFileNotFoundError(
                            f"Document object not found in Supabase Storage: {bucket}/{obj_key}"
                        )
                    raise StorageError(
                        f"Supabase Storage download failed with status {std_res.status_code}: {std_res.text}"
                    )
                elif res.status_code in (401, 403):
                    raise StorageError(
                        "Supabase Storage authentication failed. Check SUPABASE_SERVICE_ROLE_KEY."
                    )
                else:
                    raise StorageError(
                        f"Supabase Storage download failed with status {res.status_code}: {res.text}"
                    )
            except httpx.RequestError as exc:
                raise StorageError(f"Network error downloading from Supabase Storage: {exc}") from exc

    async def delete_file(self, storage_path: str) -> bool:
        bucket, obj_key = self._parse_path(storage_path)
        headers = self._get_headers(content_type="application/json")

        async with self._get_client() as client:
            # Standard batch delete endpoint
            batch_url = f"{self.supabase_url}/storage/v1/object/{bucket}"
            try:
                res = await client.request(
                    "DELETE",
                    batch_url,
                    json={"prefixes": [obj_key]},
                    headers=headers,
                )
                if res.status_code in (200, 204, 404):
                    return True

                # Fallback to direct path delete
                direct_url = f"{self.supabase_url}/storage/v1/object/{bucket}/{obj_key}"
                fallback_res = await client.delete(direct_url, headers=headers)
                if fallback_res.status_code in (200, 204, 404):
                    return True

                raise StorageError(
                    f"Supabase Storage delete failed with status {res.status_code}: {res.text}"
                )
            except httpx.RequestError as exc:
                raise StorageError(f"Network error deleting from Supabase Storage: {exc}") from exc

    async def file_exists(self, storage_path: str) -> bool:
        bucket, obj_key = self._parse_path(storage_path)
        headers = self._get_headers()

        async with self._get_client() as client:
            auth_url = f"{self.supabase_url}/storage/v1/object/authenticated/{bucket}/{obj_key}"
            try:
                res = await client.head(auth_url, headers=headers)
                if res.status_code == 200:
                    return True
                if res.status_code == 404:
                    return False
                # If HEAD is not allowed, check via GET
                get_res = await client.get(auth_url, headers=headers)
                return get_res.status_code == 200
            except httpx.RequestError:
                return False


class MockStorageProvider(BaseStorageProvider):
    """In-memory storage provider for fast, deterministic unit tests."""

    def __init__(self):
        self.storage: Dict[str, bytes] = {}

    def clear(self) -> None:
        self.storage.clear()

    async def upload_file(
        self,
        destination_path: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        clean = destination_path.replace("\\", "/").lstrip("/")
        key = f"mock://documents/{clean}"
        self.storage[key] = bytes(content)
        return key

    async def download_file(self, storage_path: str) -> bytes:
        if storage_path in self.storage:
            return self.storage[storage_path]

        clean = storage_path.replace("\\", "/").lstrip("/")
        # Check by matching suffix or key
        for k, v in self.storage.items():
            if k.endswith(clean) or clean in k:
                return v

        raise StorageFileNotFoundError(f"Mock storage object not found: {storage_path}")

    async def delete_file(self, storage_path: str) -> bool:
        if storage_path in self.storage:
            del self.storage[storage_path]
            return True

        clean = storage_path.replace("\\", "/").lstrip("/")
        found_keys = [k for k in self.storage if k.endswith(clean) or clean in k]
        if found_keys:
            for k in found_keys:
                del self.storage[k]
            return True

        return False

    async def file_exists(self, storage_path: str) -> bool:
        if storage_path in self.storage:
            return True
        clean = storage_path.replace("\\", "/").lstrip("/")
        return any(k.endswith(clean) or clean in k for k in self.storage)


class StorageService:
    """High-level storage service facade managing tenant isolation, security, and provider dispatch."""

    def __init__(
        self,
        default_provider: Optional[BaseStorageProvider] = None,
        local_provider: Optional[LocalStorageProvider] = None,
        supabase_provider: Optional[SupabaseStorageProvider] = None,
    ):
        self._default_provider = default_provider
        self._local_provider = local_provider
        self._supabase_provider = supabase_provider

    @property
    def local_provider(self) -> LocalStorageProvider:
        if self._local_provider is None:
            self._local_provider = LocalStorageProvider()
        return self._local_provider

    @property
    def supabase_provider(self) -> SupabaseStorageProvider:
        if self._supabase_provider is None:
            self._supabase_provider = SupabaseStorageProvider()
        return self._supabase_provider

    @supabase_provider.setter
    def supabase_provider(self, provider: SupabaseStorageProvider) -> None:
        self._supabase_provider = provider

    def get_provider(self) -> BaseStorageProvider:
        """Get the active storage provider based on configuration or explicit injection."""
        if self._default_provider is not None:
            return self._default_provider

        backend = settings.STORAGE_BACKEND.lower()
        if backend == "local":
            return self.local_provider
        elif backend == "supabase":
            return self.supabase_provider
        elif backend == "mock":
            return MockStorageProvider()
        else:
            raise StorageConfigurationError(
                f"Unsupported STORAGE_BACKEND: '{settings.STORAGE_BACKEND}'. Must be 'local', 'supabase', or 'mock'."
            )

    def build_safe_object_path(self, user_id: str, original_filename: Optional[str] = None) -> str:
        """Construct a secure, tenant-isolated destination path for storage.

        Guarantees:
        - Strict user folder partitioning ({user_id}/...)
        - Safe random UUID filename to prevent collision and overwrites
        - Path traversal prevention
        """
        if not user_id or not str(user_id).strip():
            raise StorageValidationError("User ID is required for storage path construction.")

        # Whitelist safe characters for user folder (alphanumeric, hyphens, underscores)
        safe_uid = re.sub(r"[^a-zA-Z0-9_-]", "", str(user_id).strip())
        if not safe_uid:
            raise StorageValidationError("Invalid user_id characters for storage path.")

        # Cryptographically strong UUID for stored file name
        unique_name = f"{uuid.uuid4().hex}.pdf"
        target_path = f"{safe_uid}/{unique_name}"

        # Double check traversal
        if ".." in target_path.split("/"):
            raise StorageValidationError("Path traversal detected in generated object path.")

        return target_path

    async def upload_document_file(
        self,
        user_id: str,
        filename: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        """Generate safe path and persist document via the configured storage provider."""
        safe_path = self.build_safe_object_path(user_id=user_id, original_filename=filename)
        provider = self.get_provider()
        return await provider.upload_file(
            destination_path=safe_path,
            content=content,
            content_type=content_type,
        )

    async def download_file(self, storage_path: str) -> bytes:
        """Retrieve document bytes, intelligently handling Supabase, local files, and legacy paths."""
        if not storage_path or not storage_path.strip():
            raise StorageFileNotFoundError("Empty storage path.")

        clean = storage_path.strip()

        # 1. Supabase URI
        if clean.startswith("supabase://"):
            return await self.supabase_provider.download_file(clean)

        # 2. Mock URI
        if clean.startswith("mock://"):
            provider = self.get_provider()
            return await provider.download_file(clean)

        # 3. Check if file exists directly on disk (preserving existing local documents!)
        if os.path.exists(clean) and os.path.isfile(clean):
            return await self.local_provider.download_file(clean)

        # 4. Check if file exists in STORAGE_DIR by basename (for legacy records)
        legacy_local = os.path.join(self.local_provider.base_dir, os.path.basename(clean))
        if os.path.exists(legacy_local) and os.path.isfile(legacy_local):
            return await self.local_provider.download_file(legacy_local)

        # 5. If current backend is supabase and path is a relative key
        if settings.STORAGE_BACKEND.lower() == "supabase":
            return await self.supabase_provider.download_file(clean)

        # 6. Fallback to active provider
        return await self.get_provider().download_file(clean)

    async def delete_file(self, storage_path: str) -> bool:
        """Delete document file, intelligently handling Supabase and local files."""
        if not storage_path or not storage_path.strip():
            return False

        clean = storage_path.strip()

        # 1. Supabase URI
        if clean.startswith("supabase://"):
            return await self.supabase_provider.delete_file(clean)

        # 2. Mock URI
        if clean.startswith("mock://"):
            provider = self.get_provider()
            return await provider.delete_file(clean)

        # 3. Direct local disk path
        if os.path.exists(clean) and os.path.isfile(clean):
            return await self.local_provider.delete_file(clean)

        # 4. Check legacy local directory
        legacy_local = os.path.join(self.local_provider.base_dir, os.path.basename(clean))
        if os.path.exists(legacy_local) and os.path.isfile(legacy_local):
            return await self.local_provider.delete_file(legacy_local)

        # 5. If configured as supabase
        if settings.STORAGE_BACKEND.lower() == "supabase":
            return await self.supabase_provider.delete_file(clean)

        # 6. Fallback to active provider
        return await self.get_provider().delete_file(clean)

    async def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in either Supabase or local storage."""
        if not storage_path or not storage_path.strip():
            return False

        clean = storage_path.strip()
        if clean.startswith("supabase://"):
            return await self.supabase_provider.file_exists(clean)
        if clean.startswith("mock://"):
            return await self.get_provider().file_exists(clean)
        if os.path.exists(clean) and os.path.isfile(clean):
            return True
        legacy_local = os.path.join(self.local_provider.base_dir, os.path.basename(clean))
        if os.path.exists(legacy_local) and os.path.isfile(legacy_local):
            return True
        if settings.STORAGE_BACKEND.lower() == "supabase":
            return await self.supabase_provider.file_exists(clean)
        return await self.get_provider().file_exists(clean)


# Global singleton service
storage_service = StorageService()


def get_storage_service() -> StorageService:
    return storage_service
