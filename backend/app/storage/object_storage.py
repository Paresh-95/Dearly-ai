import uuid

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

_client = boto3.client(
    "s3",
    endpoint_url=settings.minio_endpoint_url,
    aws_access_key_id=settings.minio_access_key,
    aws_secret_access_key=settings.minio_secret_key,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)


def ensure_bucket() -> None:
    try:
        _client.head_bucket(Bucket=settings.minio_bucket)
    except ClientError:
        _client.create_bucket(Bucket=settings.minio_bucket)


def _safe_key(subdir: str, filename: str) -> str:
    safe_subdir = subdir.replace("..", "").strip("/\\")
    return f"{safe_subdir}/{filename}"


def save_bytes(subdir: str, extension: str, data: bytes) -> str:
    """Upload data under <subdir>/<generated-name>.<extension> in the private
    MinIO bucket. Returns the object key to persist in the DB (never a public
    URL — reads always go through a server-side lookup, see read_bytes)."""
    filename = f"{uuid.uuid4().hex}.{extension.lstrip('.')}"
    key = _safe_key(subdir, filename)
    _client.put_object(Bucket=settings.minio_bucket, Key=key, Body=data)
    return key


def read_bytes(key: str) -> bytes:
    if ".." in key:
        raise ValueError("invalid storage key")
    response = _client.get_object(Bucket=settings.minio_bucket, Key=key)
    return response["Body"].read()


def delete_object(key: str) -> None:
    if ".." in key:
        raise ValueError("invalid storage key")
    _client.delete_object(Bucket=settings.minio_bucket, Key=key)
