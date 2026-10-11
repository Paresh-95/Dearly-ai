# ADR 0007 — Message timestamps are set in Python, not left to the DB default

**Status:** accepted (Milestone 6)

`TimestampMixin`'s `created_at` uses `server_default=func.now()`. That works fine for every
table created so far, because nothing else creates two rows of the same table in the same
database transaction where their relative order matters. A chat turn breaks that assumption:
answering one question inserts the user's message and the assistant's reply in the *same*
transaction (one request, one commit), and Postgres's `now()` returns the transaction's
start time for every statement inside it — both rows got an identical `created_at`, so
`ORDER BY created_at` could return them in either order. A test asserting conversation
history order (`tests/test_conversations.py`) caught this immediately.

**Decision:** `app/repositories/messages.py#create` sets `created_at` explicitly from
`datetime.now(UTC)` (Python, not SQL) before inserting, so the user message and the
assistant's reply get distinct, correctly-ordered microsecond timestamps even within one
transaction. The sort in `list_for_conversation`/`recent_history` also adds `Message.id` as
a tiebreaker for determinism, though with the Python timestamp fix a real tie should not
happen in practice.

This is scoped to `messages` only. No other table in this schema inserts multiple rows of
itself within one transaction in an order-sensitive way yet; if one starts to, it needs the
same treatment.
