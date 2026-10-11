from pathlib import Path

from app.services.storage.base import ObjectStorage


class LocalFileStorage(ObjectStorage):
    """Default, zero-config backend: writes under a local directory. Used in dev and tests;
    `S3Storage` is the one actually suited to a multi-instance deployment."""

    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # `key` is always a server-generated UUID-based path (see app.services.ingestion.keys),
        # never a user-supplied filename, so there is no path-traversal input to sanitise here.
        path = (self._root / key).resolve()
        if self._root.resolve() not in path.parents and path != self._root.resolve():
            raise ValueError(f"Refusing to write outside storage root: {key}")
        return path

    def save(self, key: str, data: bytes, content_type: str | None) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
