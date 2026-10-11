"""The memory review status machine.

draft --------> awaiting_review --------> approved -----> awaiting_review
  |                 |      ^                  |
  |                 v      |__________________|
  +------------> approved
  |
  +------------> rejected <---- awaiting_review
                    |
                    v
                  draft

Only `approved` memories are ever chunked/embedded/retrieved (enforced elsewhere, not here).
Editing an approved memory's content pulls it back to `awaiting_review` so stale, unreviewed
wording is never served from the index — see `CONTENT_FIELDS` and its use in
`app.repositories.memories.update`.
"""

from app.domain.enums import MemoryStatus

_ALLOWED_TRANSITIONS: dict[MemoryStatus, set[MemoryStatus]] = {
    MemoryStatus.DRAFT: {
        MemoryStatus.AWAITING_REVIEW,
        MemoryStatus.APPROVED,
        MemoryStatus.REJECTED,
    },
    MemoryStatus.AWAITING_REVIEW: {
        MemoryStatus.APPROVED,
        MemoryStatus.REJECTED,
        MemoryStatus.DRAFT,
    },
    MemoryStatus.APPROVED: {MemoryStatus.AWAITING_REVIEW, MemoryStatus.REJECTED},
    MemoryStatus.REJECTED: {MemoryStatus.DRAFT},
}

# Fields whose change on an approved memory requires re-review before it counts as approved
# again. Deliberately includes the uncertainty flag: lowering confidence in an already-indexed
# memory is exactly the kind of change that should not take effect silently.
CONTENT_FIELDS = frozenset(
    {
        "title",
        "description",
        "category",
        "date_text",
        "date_start",
        "date_end",
        "location",
        "is_uncertain",
        "uncertainty_note",
        "people",
    }
)


class InvalidTransition(ValueError):
    def __init__(self, current: MemoryStatus, target: MemoryStatus) -> None:
        super().__init__(f"Cannot move a memory from '{current}' to '{target}'")
        self.current = current
        self.target = target


def ensure_transition_allowed(current: MemoryStatus, target: MemoryStatus) -> None:
    if target == current:
        return
    if target not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidTransition(current, target)


def next_status_on_update(
    current: MemoryStatus,
    *,
    requested_status: MemoryStatus | None,
    changed_fields: set[str],
) -> MemoryStatus:
    """What status a PATCH should result in, given which fields changed."""
    if requested_status is not None:
        return requested_status
    if current == MemoryStatus.APPROVED and changed_fields & CONTENT_FIELDS:
        return MemoryStatus.AWAITING_REVIEW
    return current
