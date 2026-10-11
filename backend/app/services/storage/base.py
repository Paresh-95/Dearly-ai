"""Private object storage for uploaded originals. There is no endpoint that serves a key
directly or publicly — the only access path is `GET /api/v1/sources/{id}/download`, which
requires a bearer token and ownership check before it streams bytes through the API."""

from abc import ABC, abstractmethod


class ObjectStorage(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str | None) -> None: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...
