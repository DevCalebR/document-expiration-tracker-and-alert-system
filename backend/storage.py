import tempfile
from pathlib import Path
from typing import Optional

from config import settings


class StorageError(Exception):
    pass


class BaseStorageClient:
    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        raise NotImplementedError

    def download_to_path(self, key: str, path: Path) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError


class FilesystemStorageClient(BaseStorageClient):
    def __init__(self) -> None:
        self._root = settings.FILESYSTEM_STORAGE_ROOT.resolve()

    def _path_for_key(self, key: str) -> Path:
        candidate = (self._root / key).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise StorageError("Invalid storage key") from exc
        return candidate

    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def download_to_path(self, key: str, path: Path) -> None:
        source = self._path_for_key(key)
        if not source.exists():
            raise StorageError("Object not found")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(source.read_bytes())

    def delete(self, key: str) -> None:
        target = self._path_for_key(key)
        if target.exists():
            target.unlink()
        parent = target.parent
        while parent != self._root and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


class S3StorageClient(BaseStorageClient):
    def __init__(self) -> None:
        import boto3

        if not settings.STORAGE_BUCKET:
            raise StorageError("STORAGE_BUCKET is required for S3 storage")
        self._client = boto3.client(
            "s3",
            region_name=settings.STORAGE_REGION or None,
            endpoint_url=settings.STORAGE_ENDPOINT_URL or None,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY or None,
            aws_secret_access_key=settings.STORAGE_SECRET_KEY or None,
        )
        self._bucket = settings.STORAGE_BUCKET

    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        params = {"Bucket": self._bucket, "Key": key}
        if content_type:
            params["ContentType"] = content_type
        self._client.put_object(Body=data, **params)

    def download_to_path(self, key: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._client.download_file(self._bucket, key, str(path))

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


class GCSStorageClient(BaseStorageClient):
    def __init__(self) -> None:
        from google.cloud import storage

        if not settings.STORAGE_BUCKET:
            raise StorageError("STORAGE_BUCKET is required for GCS storage")
        self._client = storage.Client()
        self._bucket = self._client.bucket(settings.STORAGE_BUCKET)

    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        blob = self._bucket.blob(key)
        blob.upload_from_string(data, content_type=content_type)

    def download_to_path(self, key: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = self._bucket.blob(key)
        blob.download_to_filename(str(path))

    def delete(self, key: str) -> None:
        blob = self._bucket.blob(key)
        blob.delete()


class AzureStorageClient(BaseStorageClient):
    def __init__(self) -> None:
        from azure.storage.blob import BlobServiceClient

        if not settings.STORAGE_BUCKET:
            raise StorageError("STORAGE_BUCKET is required for Azure storage")
        if settings.AZURE_STORAGE_CONNECTION_STRING:
            service = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
        else:
            account_url = settings.AZURE_STORAGE_ACCOUNT_URL
            if not account_url:
                raise StorageError("Azure storage account URL is required")
            service = BlobServiceClient(
                account_url=account_url,
                credential=settings.AZURE_STORAGE_ACCOUNT_KEY,
            )
        self._container = service.get_container_client(settings.STORAGE_BUCKET)

    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        from azure.storage.blob import ContentSettings

        content_settings = ContentSettings(content_type=content_type) if content_type else None
        self._container.upload_blob(
            name=key,
            data=data,
            overwrite=True,
            content_settings=content_settings,
        )

    def download_to_path(self, key: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        blob_client = self._container.get_blob_client(key)
        with open(path, "wb") as handle:
            handle.write(blob_client.download_blob().readall())

    def delete(self, key: str) -> None:
        self._container.delete_blob(key)


class MemoryStorageClient(BaseStorageClient):
    _store: dict[str, bytes] = {}

    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        self._store[key] = data

    def download_to_path(self, key: str, path: Path) -> None:
        if key not in self._store:
            raise StorageError("Object not found")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(self._store[key])

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


_STORAGE_CLIENT: Optional[BaseStorageClient] = None


def get_storage_client() -> BaseStorageClient:
    global _STORAGE_CLIENT
    if _STORAGE_CLIENT:
        return _STORAGE_CLIENT

    provider = settings.STORAGE_PROVIDER.lower()
    if provider == "filesystem":
        _STORAGE_CLIENT = FilesystemStorageClient()
    elif provider == "s3":
        _STORAGE_CLIENT = S3StorageClient()
    elif provider == "gcs":
        _STORAGE_CLIENT = GCSStorageClient()
    elif provider == "azure":
        _STORAGE_CLIENT = AzureStorageClient()
    elif provider == "memory":
        _STORAGE_CLIENT = MemoryStorageClient()
    else:
        raise StorageError(f"Unsupported storage provider: {settings.STORAGE_PROVIDER}")

    return _STORAGE_CLIENT


def build_object_key(user_id: int, filename: str) -> str:
    prefix = settings.STORAGE_PREFIX.strip("/") if settings.STORAGE_PREFIX else ""
    parts = [part for part in [prefix, str(user_id), filename] if part]
    return "/".join(parts)


def create_temp_file(suffix: str) -> Path:
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(delete=False, dir=settings.TEMP_DIR, suffix=suffix)
    handle.close()
    return Path(handle.name)
