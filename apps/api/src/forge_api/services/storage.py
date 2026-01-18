from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Protocol

import boto3
from botocore.exceptions import ClientError

from forge_api.settings import get_settings


class StorageDriver(Protocol):
    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        ...

    def get_bytes(self, key: str) -> bytes:
        ...

    def open_stream(self, key: str) -> BytesIO:
        ...

    def exists(self, key: str) -> bool:
        ...


@dataclass
class LocalStorageDriver:
    root: Path

    def ensure_root(self) -> None:
        self.root = self.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_join(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError("Invalid storage key")
        return candidate

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        path = self._safe_join(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get_bytes(self, key: str) -> bytes:
        return self._safe_join(key).read_bytes()

    def open_stream(self, key: str) -> BytesIO:
        return BytesIO(self.get_bytes(key))

    def get_path(self, key: str) -> str:
        return str(self._safe_join(key))

    def exists(self, key: str) -> bool:
        return self._safe_join(key).exists()


@dataclass
class S3StorageDriver:
    bucket: str
    prefix: str | None
    client: boto3.client

    def _resolve_key(self, key: str) -> str:
        if self.prefix:
            clean_prefix = self.prefix.strip("/")
            return f"{clean_prefix}/{key}"
        return key

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        params = {
            "Bucket": self.bucket,
            "Key": self._resolve_key(key),
            "Body": data,
        }
        if content_type:
            params["ContentType"] = content_type
        self.client.put_object(**params)
        return key

    def get_bytes(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._resolve_key(key))
            return response["Body"].read()
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"NoSuchKey", "404"} or exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                raise FileNotFoundError("Object not found") from exc
            raise

    def open_stream(self, key: str) -> BytesIO:
        return BytesIO(self.get_bytes(key))

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._resolve_key(key))
            return True
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"NoSuchKey", "404"} or exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return False
            raise


def _build_s3_driver() -> S3StorageDriver:
    settings = get_settings()
    client = boto3.client(
        "s3",
        region_name=settings.FORGE_S3_REGION,
        endpoint_url=settings.FORGE_S3_ENDPOINT,
        aws_access_key_id=settings.FORGE_S3_ACCESS_KEY,
        aws_secret_access_key=settings.FORGE_S3_SECRET_KEY,
    )
    return S3StorageDriver(
        bucket=settings.FORGE_S3_BUCKET,
        prefix=settings.FORGE_S3_PREFIX,
        client=client,
    )


def get_storage() -> StorageDriver:
    settings = get_settings()
    if settings.FORGE_STORAGE_DRIVER.lower() == "s3":
        return _build_s3_driver()
    driver = LocalStorageDriver(Path(settings.FORGE_STORAGE_LOCAL_DIR))
    driver.ensure_root()
    return driver


def get_patch_storage() -> StorageDriver:
    settings = get_settings()
    driver_name = (settings.FORGE_PATCH_STORE_DRIVER or settings.FORGE_STORAGE_DRIVER).lower()
    if driver_name == "s3":
        return _build_s3_driver()
    driver = LocalStorageDriver(Path(settings.FORGE_STORAGE_LOCAL_DIR))
    driver.ensure_root()
    return driver
