from functools import lru_cache

from app.core.config import get_settings
from app.services.storage.base import ObjectStorage
from app.services.storage.local import LocalFileStorage
from app.services.storage.s3 import S3Storage

__all__ = ["ObjectStorage", "LocalFileStorage", "S3Storage", "get_storage"]


@lru_cache
def get_storage() -> ObjectStorage:
    s = get_settings()
    if s.storage_backend == "s3":
        return S3Storage(
            endpoint_url=s.s3_endpoint_url,
            access_key=s.s3_access_key,
            secret_key=s.s3_secret_key,
            bucket=s.s3_bucket,
            region=s.s3_region,
        )
    return LocalFileStorage(s.storage_local_dir)
