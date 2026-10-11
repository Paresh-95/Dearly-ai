import pytest

from app.domain.enums import MemoryStatus
from app.domain.memory_rules import (
    InvalidTransition,
    ensure_transition_allowed,
    next_status_on_update,
)

S = MemoryStatus


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.DRAFT, S.AWAITING_REVIEW),
        (S.DRAFT, S.APPROVED),
        (S.DRAFT, S.REJECTED),
        (S.AWAITING_REVIEW, S.APPROVED),
        (S.AWAITING_REVIEW, S.REJECTED),
        (S.AWAITING_REVIEW, S.DRAFT),
        (S.APPROVED, S.AWAITING_REVIEW),
        (S.APPROVED, S.REJECTED),
        (S.REJECTED, S.DRAFT),
        (S.DRAFT, S.DRAFT),  # no-op is always fine
    ],
)
def test_allowed_transitions(current, target):
    ensure_transition_allowed(current, target)  # must not raise


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.APPROVED, S.DRAFT),  # must go through awaiting_review first
        (S.REJECTED, S.APPROVED),  # must be revised (-> draft) before resubmission
        (S.REJECTED, S.AWAITING_REVIEW),
    ],
)
def test_disallowed_transitions(current, target):
    with pytest.raises(InvalidTransition):
        ensure_transition_allowed(current, target)


def test_editing_approved_memory_reverts_to_review():
    assert (
        next_status_on_update(S.APPROVED, requested_status=None, changed_fields={"title"})
        == S.AWAITING_REVIEW
    )


def test_editing_approved_memory_without_content_change_stays_approved():
    result = next_status_on_update(S.APPROVED, requested_status=None, changed_fields=set())
    assert result == S.APPROVED


def test_explicit_status_wins_over_auto_revert():
    assert (
        next_status_on_update(S.APPROVED, requested_status=S.DRAFT, changed_fields={"title"})
        == S.DRAFT
    )


def test_editing_non_approved_memory_keeps_its_status():
    result = next_status_on_update(S.DRAFT, requested_status=None, changed_fields={"title"})
    assert result == S.DRAFT
