from uuid import UUID


def storage_key(source_id: UUID) -> str:
    """One object per source. The id is server-generated, so this is never built from a
    user-supplied filename (no path-traversal input)."""
    return f"sources/{source_id}"
