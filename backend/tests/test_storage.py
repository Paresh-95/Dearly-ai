import os

import pytest

from app.services.storage.local import LocalFileStorage


class TestLocalFileStorage:
    def test_round_trips_bytes(self, tmp_path):
        storage = LocalFileStorage(str(tmp_path))
        storage.save("sources/abc", b"hello world", "text/plain")
        assert storage.read("sources/abc") == b"hello world"

    def test_delete_is_idempotent(self, tmp_path):
        storage = LocalFileStorage(str(tmp_path))
        storage.save("sources/abc", b"x", None)
        storage.delete("sources/abc")
        storage.delete("sources/abc")  # must not raise on a missing file
        with pytest.raises(FileNotFoundError):
            storage.read("sources/abc")

    def test_rejects_keys_that_escape_the_storage_root(self, tmp_path):
        storage = LocalFileStorage(str(tmp_path))
        with pytest.raises(ValueError):
            storage.save("../../etc/passwd", b"x", None)


@pytest.mark.skipif(
    os.environ.get("MC_RUN_S3_TESTS") != "1",
    reason="needs a live MinIO container; set MC_RUN_S3_TESTS=1 and `docker compose up -d minio`",
)
class TestS3Storage:
    def test_round_trips_bytes_against_minio(self):
        from app.services.storage.s3 import S3Storage

        storage = S3Storage(
            endpoint_url=os.environ.get("MC_S3_ENDPOINT_URL", "http://localhost:9100"),
            access_key="minioadmin",
            secret_key="minioadmin",
            bucket="memory-companion-test",
            region="us-east-1",
        )
        storage.save("sources/test-key", b"hello minio", "text/plain")
        assert storage.read("sources/test-key") == b"hello minio"
        storage.delete("sources/test-key")
