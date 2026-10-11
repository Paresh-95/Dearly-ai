# ADR 0002 — Postgres RLS deferred, not shipped as decoration

**Status:** accepted (Milestone 2)

The blueprint (ADR 0001, M2 row) planned Postgres row-level security as defense-in-depth on
top of the repository-layer scoping shipped in Milestone 1. Investigating it for M2 surfaced
a real blocker, so it is deferred rather than shipped half-working:

- RLS policies are **always bypassed by the table owner** unless the table uses `FORCE ROW
  LEVEL SECURITY`, and are **always bypassed by a superuser or a role with `BYPASSRLS`**
  regardless of `FORCE`. The official `postgres` Docker image makes `POSTGRES_USER` the
  cluster's bootstrap superuser, and that is the only role this project connects as
  (migrations, the API, and tests all share it). Enabling RLS under this setup would add
  policies that are silently bypassed on every request — a false sense of security, which is
  worse than no RLS at all.
- Making RLS actually bind requires a second, non-superuser database role for runtime queries,
  distinct from the migration-owning role. That in turn runs into `CREATE ROLE` being
  cluster-global while Alembic migrations are per-database — the dev and test databases share
  one local Postgres instance/cluster in this setup, so role creation/teardown in migrations
  needs care not to break the other database's grants. Solvable, but a non-trivial, separate
  piece of infrastructure work.

**Decision:** keep tenant isolation enforced at the repository layer (every query scoped by
`user_id`, every table additionally constrained by the composite FK to
`person_profiles(id, user_id)` — see ADR 0001), which is what the Milestone 1 and 2 test
suites actually verify (cross-user access returns 404 on every resource, including the new
memories and consents endpoints in M2). Real RLS, with a dedicated non-superuser application
role, is tracked as follow-up infrastructure work rather than bundled into M2 under time
pressure.

**Why this is a reasonable interim position:** the composite FK means the database itself
already refuses to let a row claim a `person_profile_id` it doesn't own, which closes the
most dangerous class of bug (a write silently attaching data to someone else's profile). What
RLS would add on top is protection against a *read* query that forgets its `WHERE user_id =
...` filter — a real gap, but one the test suite's cross-user assertions catch for every
shipped endpoint today.
