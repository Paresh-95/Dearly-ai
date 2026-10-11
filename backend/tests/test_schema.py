"""Database-level guarantees, independent of the API layer."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def _user(conn, email="u@example.com"):
    return conn.execute(
        text("INSERT INTO users (id,email,password_hash) VALUES (:i,:e,'x') RETURNING id"),
        {"i": uuid.uuid4(), "e": email},
    ).scalar_one()


def _profile(conn, user_id):
    return conn.execute(
        text(
            "INSERT INTO person_profiles (id,user_id,name,relationship) "
            "VALUES (:i,:u,'Mum','mother') RETURNING id"
        ),
        {"i": uuid.uuid4(), "u": user_id},
    ).scalar_one()


def _memory(conn, user_id, profile_id, status="draft", approved=False):
    return conn.execute(
        text(
            "INSERT INTO memories (id,user_id,person_profile_id,title,description,status,origin,"
            "approved_at) VALUES (:i,:u,:p,'t','d',:s,'user_written',"
            + ("now()" if approved else "NULL")
            + ") RETURNING id"
        ),
        {"i": uuid.uuid4(), "u": user_id, "p": profile_id, "s": status},
    ).scalar_one()


def test_extensions_and_hnsw_index_present(engine):
    with engine.connect() as c:
        assert c.execute(text("SELECT 1 FROM pg_extension WHERE extname='vector'")).scalar()
        idx = c.execute(
            text("SELECT indexdef FROM pg_indexes WHERE indexname='ix_memory_chunks_embedding'")
        ).scalar()
        assert "hnsw" in idx and "vector_cosine_ops" in idx


def test_row_cannot_reference_another_users_profile(engine):
    with engine.connect() as c:
        owner, intruder = _user(c, "a@x.com"), _user(c, "b@x.com")
        profile = _profile(c, owner)
        with pytest.raises(IntegrityError):
            _memory(c, intruder, profile)  # composite FK (profile, user) must fail
        c.rollback()


def test_status_and_approved_at_must_agree(engine):
    with engine.connect() as c:
        u = _user(c)
        p = _profile(c, u)
        _memory(c, u, p, "approved", approved=True)  # ok
        with pytest.raises(IntegrityError):
            _memory(c, u, p, "approved", approved=False)
        c.rollback()
    with engine.connect() as c:
        u = _user(c, "c@x.com")
        p = _profile(c, u)
        with pytest.raises(IntegrityError):
            _memory(c, u, p, "bogus")
        c.rollback()


def test_deleting_memory_removes_chunks_and_profile_cascades_everything(engine):
    with engine.begin() as c:
        u = _user(c)
        p = _profile(c, u)
        m = _memory(c, u, p, "approved", approved=True)
        c.execute(
            text(
                "INSERT INTO memory_chunks (id,user_id,person_profile_id,memory_id,chunk_index,"
                "text,content_hash) VALUES (:i,:u,:p,:m,0,'Sunday poha','h1')"
            ),
            {"i": uuid.uuid4(), "u": u, "p": p, "m": m},
        )
        # generated tsvector column is populated for keyword search
        assert c.execute(
            text("SELECT count(*) FROM memory_chunks WHERE tsv @@ plainto_tsquery('simple','poha')")
        ).scalar() == 1

        c.execute(text("DELETE FROM memories WHERE id=:m"), {"m": m})
        assert c.execute(text("SELECT count(*) FROM memory_chunks")).scalar() == 0

        m2 = _memory(c, u, p)
        c.execute(text("DELETE FROM person_profiles WHERE id=:p"), {"p": p})
        assert c.execute(text("SELECT count(*) FROM memories WHERE id=:m"), {"m": m2}).scalar() == 0


def test_indexed_chunk_requires_embedding(engine):
    with engine.connect() as c:
        u = _user(c)
        p = _profile(c, u)
        m = _memory(c, u, p, "approved", approved=True)
        with pytest.raises(IntegrityError):
            c.execute(
                text(
                    "INSERT INTO memory_chunks (id,user_id,person_profile_id,memory_id,"
                    "chunk_index,text,content_hash,index_status) "
                    "VALUES (:i,:u,:p,:m,0,'x','h','indexed')"
                ),
                {"i": uuid.uuid4(), "u": u, "p": p, "m": m},
            )
        c.rollback()
