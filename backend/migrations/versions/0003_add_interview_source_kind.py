"""add interview source kind

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

# Raw SQL, not op.create_check_constraint/op.drop_constraint: with a naming-convention-bound
# MetaData configured in migrations/env.py, those ops re-ran the "ck_sources_" prefix through
# the convention a second time (producing "ck_sources_ck_sources_kind_valid") instead of using
# the literal name given, for both drop and create. Plain SQL has no such ambiguity.
_OLD_KINDS = "'manual','text','pdf','docx','whatsapp','image','audio','video'"
_NEW_KINDS = _OLD_KINDS + ",'interview'"


def upgrade() -> None:
    op.execute("ALTER TABLE sources DROP CONSTRAINT ck_sources_kind_valid")
    op.execute(f"ALTER TABLE sources ADD CONSTRAINT ck_sources_kind_valid CHECK (kind IN ({_NEW_KINDS}))")


def downgrade() -> None:
    op.execute("ALTER TABLE sources DROP CONSTRAINT ck_sources_kind_valid")
    op.execute(f"ALTER TABLE sources ADD CONSTRAINT ck_sources_kind_valid CHECK (kind IN ({_OLD_KINDS}))")
