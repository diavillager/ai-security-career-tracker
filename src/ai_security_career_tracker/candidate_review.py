"""Plan explicit Candidate approval and rejection changes safely."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from .role_discovery import RoleStatus, normalize_role_name


class CandidateReviewError(ValueError):
    """Raised when a requested review cannot be applied unambiguously."""


class CandidateReviewApplyError(RuntimeError):
    """Raised when a validated Notion update fails during application."""

    def __init__(
        self,
        failed_record_id: str,
        applied_record_ids: tuple[str, ...],
    ) -> None:
        super().__init__(
            "Notion update failed after applying "
            f"{len(applied_record_ids)} record(s); failed record: {failed_record_id}"
        )
        self.failed_record_id = failed_record_id
        self.applied_record_ids = applied_record_ids


@dataclass(frozen=True)
class RoleRecord:
    record_id: str
    role_name: str
    status: RoleStatus

    def __post_init__(self) -> None:
        if not self.record_id.strip() or not self.role_name.strip():
            raise CandidateReviewError("Record ID and Role Name are required.")


@dataclass(frozen=True)
class ReviewDecision:
    role_name: str
    target_status: RoleStatus
    note: str = ""

    def __post_init__(self) -> None:
        if not self.role_name.strip():
            raise CandidateReviewError("A review decision needs a Role Name.")
        if self.target_status not in {
            RoleStatus.APPROVED,
            RoleStatus.REJECTED,
        }:
            raise CandidateReviewError(
                "A Candidate review can only target Approved or Rejected."
            )
        if self.target_status is RoleStatus.REJECTED and not self.note.strip():
            raise CandidateReviewError("A rejected Candidate needs a review note.")


@dataclass(frozen=True)
class ReviewAction:
    record_id: str
    role_name: str
    previous_status: RoleStatus
    target_status: RoleStatus
    reviewed_on: date
    note: str


@dataclass(frozen=True)
class UnchangedReview:
    record_id: str
    role_name: str
    status: RoleStatus


@dataclass(frozen=True)
class ReviewPlan:
    actions: tuple[ReviewAction, ...]
    unchanged: tuple[UnchangedReview, ...]


@dataclass(frozen=True)
class NotionRoleUpdate:
    record_id: str
    role_name: str
    properties: dict[str, object]


@dataclass(frozen=True)
class ReviewApplicationResult:
    applied_record_ids: tuple[str, ...]
    unchanged_record_ids: tuple[str, ...]


def plan_candidate_reviews(
    records: tuple[RoleRecord, ...],
    decisions: tuple[ReviewDecision, ...],
    reviewed_on: date,
) -> ReviewPlan:
    """Return an atomic review plan without changing Notion records."""
    if not decisions:
        raise CandidateReviewError(
            "At least one explicit approval or rejection decision is required."
        )
    if type(reviewed_on) is not date:
        raise CandidateReviewError("Last Reviewed must be a valid date.")

    records_by_name: dict[str, RoleRecord] = {}
    record_ids: set[str] = set()
    for record in records:
        normalized_name = normalize_role_name(record.role_name)
        if normalized_name in records_by_name:
            raise CandidateReviewError(
                f"Multiple Roles DB records match Role Name: {record.role_name}"
            )
        if record.record_id in record_ids:
            raise CandidateReviewError(
                f"Duplicate Roles DB record ID: {record.record_id}"
            )
        records_by_name[normalized_name] = record
        record_ids.add(record.record_id)

    decisions_by_name: dict[str, ReviewDecision] = {}
    decision_order: list[str] = []
    for decision in decisions:
        normalized_name = normalize_role_name(decision.role_name)
        previous = decisions_by_name.get(normalized_name)
        if previous is not None:
            if previous.target_status is not decision.target_status:
                raise CandidateReviewError(
                    f"Conflicting review decisions for Role Name: "
                    f"{decision.role_name}"
                )
            if previous.note.strip() != decision.note.strip():
                raise CandidateReviewError(
                    f"Conflicting review notes for Role Name: {decision.role_name}"
                )
            continue
        decisions_by_name[normalized_name] = decision
        decision_order.append(normalized_name)

    actions: list[ReviewAction] = []
    unchanged: list[UnchangedReview] = []
    for normalized_name in decision_order:
        decision = decisions_by_name[normalized_name]
        record = records_by_name.get(normalized_name)
        if record is None:
            raise CandidateReviewError(
                f"No Roles DB record matches Role Name: {decision.role_name}"
            )

        if record.status is RoleStatus.CANDIDATE:
            actions.append(
                ReviewAction(
                    record_id=record.record_id,
                    role_name=record.role_name,
                    previous_status=record.status,
                    target_status=decision.target_status,
                    reviewed_on=reviewed_on,
                    note=decision.note.strip(),
                )
            )
            continue

        if record.status is decision.target_status:
            unchanged.append(
                UnchangedReview(
                    record_id=record.record_id,
                    role_name=record.role_name,
                    status=record.status,
                )
            )
            continue

        raise CandidateReviewError(
            f"Role is already finalized as {record.status.value}; "
            f"do not change it to {decision.target_status.value} automatically: "
            f"{record.role_name}"
        )

    return ReviewPlan(actions=tuple(actions), unchanged=tuple(unchanged))


def build_notion_role_updates(
    plan: ReviewPlan,
) -> tuple[NotionRoleUpdate, ...]:
    """Translate a validated review plan into exact Notion property updates."""
    updates: list[NotionRoleUpdate] = []
    record_ids: set[str] = set()
    for action in plan.actions:
        if action.record_id in record_ids:
            raise CandidateReviewError(
                f"Duplicate review action for record ID: {action.record_id}"
            )
        if action.previous_status is not RoleStatus.CANDIDATE:
            raise CandidateReviewError(
                f"Only Candidate records can be updated: {action.role_name}"
            )
        if action.target_status not in {
            RoleStatus.APPROVED,
            RoleStatus.REJECTED,
        }:
            raise CandidateReviewError(
                f"Invalid review target for record: {action.role_name}"
            )
        if type(action.reviewed_on) is not date:
            raise CandidateReviewError(
                f"Last Reviewed must be a valid date: {action.role_name}"
            )
        note = action.note.strip()
        if action.target_status is RoleStatus.REJECTED and not note:
            raise CandidateReviewError(
                f"A rejected Candidate needs a review note: {action.role_name}"
            )

        properties: dict[str, object] = {
            "Status": {"select": {"name": action.target_status.value}},
            "Last Reviewed": {"date": {"start": action.reviewed_on.isoformat()}},
        }
        if note:
            properties["Notes"] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": note},
                    }
                ]
            }
        updates.append(
            NotionRoleUpdate(
                record_id=action.record_id,
                role_name=action.role_name,
                properties=properties,
            )
        )
        record_ids.add(action.record_id)
    return tuple(updates)


def apply_candidate_review_plan(
    plan: ReviewPlan,
    update_page: Callable[[str, dict[str, object]], None],
) -> ReviewApplicationResult:
    """Apply prevalidated updates through a caller-provided Notion page updater."""
    updates = build_notion_role_updates(plan)
    applied_record_ids: list[str] = []
    for update in updates:
        try:
            update_page(update.record_id, update.properties)
        except Exception as error:
            raise CandidateReviewApplyError(
                failed_record_id=update.record_id,
                applied_record_ids=tuple(applied_record_ids),
            ) from error
        applied_record_ids.append(update.record_id)

    return ReviewApplicationResult(
        applied_record_ids=tuple(applied_record_ids),
        unchanged_record_ids=tuple(item.record_id for item in plan.unchanged),
    )
