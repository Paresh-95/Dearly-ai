"""fix memory_chunks content hash uniqueness

Revision ID: 0002
Revises: 0001
"""
from alembic import op


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The original constraint scoped uniqueness to (person_profile_id, content_hash), meant
    # to stop a retried re-chunk/re-embed of the SAME memory from duplicating work. As written
    # it also rejected two DIFFERENT memories that happen to share identical chunk text under
    # the same profile (e.g. both quoting the same family saying verbatim) -- a real content
    # coincidence, not a retry, so it should not be rejected. Idempotency on retry is instead
    # handled by comparing content_hash per (memory_id, chunk_index) in application code (see
    # app/repositories/memory_chunks.py) before deciding whether to re-embed a chunk; the
    # column itself remains, just no longer DB-unique. See docs/decisions/0004.
    op.drop_constraint(
        "uq_memory_chunks_profile_content_hash", "memory_chunks", type_="unique"
    )
    op.create_index(
        "ix_memory_chunks_content_hash", "memory_chunks", ["person_profile_id", "content_hash"]
    )


def downgrade() -> None:
    op.drop_index("ix_memory_chunks_content_hash", table_name="memory_chunks")
    op.create_unique_constraint(
        "uq_memory_chunks_profile_content_hash", "memory_chunks", ["person_profile_id", "content_hash"]
    )
