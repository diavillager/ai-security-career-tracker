from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.candidate_review import (
    CandidateReviewApplyError,
    CandidateReviewError,
    ReviewAction,
    ReviewDecision,
    ReviewPlan,
    RoleRecord,
    apply_candidate_review_plan,
    build_notion_role_updates,
    plan_candidate_reviews,
)
from ai_security_career_tracker.role_discovery import RoleStatus


class CandidateReviewTests(unittest.TestCase):
    def test_candidate_can_be_approved(self) -> None:
        plan = plan_candidate_reviews(
            (
                RoleRecord(
                    "page-1",
                    "Staff, Detection Platform Engineer",
                    RoleStatus.CANDIDATE,
                ),
            ),
            (
                ReviewDecision(
                    "staff, detection platform engineer",
                    RoleStatus.APPROVED,
                ),
            ),
            date(2026, 9, 16),
        )

        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].record_id, "page-1")
        self.assertEqual(plan.actions[0].previous_status, RoleStatus.CANDIDATE)
        self.assertEqual(plan.actions[0].target_status, RoleStatus.APPROVED)
        self.assertEqual(plan.actions[0].reviewed_on, date(2026, 9, 16))
        self.assertEqual(plan.unchanged, ())

    def test_candidate_can_be_rejected_with_trimmed_note(self) -> None:
        plan = plan_candidate_reviews(
            (
                RoleRecord(
                    "page-2",
                    "Unsupported Security Role",
                    RoleStatus.CANDIDATE,
                ),
            ),
            (
                ReviewDecision(
                    "Unsupported Security Role",
                    RoleStatus.REJECTED,
                    "  근거가 부족함  ",
                ),
            ),
            date(2026, 9, 16),
        )

        self.assertEqual(plan.actions[0].target_status, RoleStatus.REJECTED)
        self.assertEqual(plan.actions[0].note, "근거가 부족함")

    def test_rejected_candidate_requires_a_review_note(self) -> None:
        with self.assertRaises(CandidateReviewError):
            ReviewDecision(
                "Unsupported Security Role",
                RoleStatus.REJECTED,
                "   ",
            )

    def test_same_final_status_is_an_unchanged_result(self) -> None:
        plan = plan_candidate_reviews(
            (
                RoleRecord(
                    "page-3",
                    "Approved Role",
                    RoleStatus.APPROVED,
                ),
            ),
            (
                ReviewDecision(
                    "Approved Role",
                    RoleStatus.APPROVED,
                ),
            ),
            date(2026, 9, 16),
        )

        self.assertEqual(plan.actions, ())
        self.assertEqual(len(plan.unchanged), 1)
        self.assertEqual(plan.unchanged[0].status, RoleStatus.APPROVED)

    def test_opposite_final_status_requires_separate_reconsideration(self) -> None:
        with self.assertRaises(CandidateReviewError):
            plan_candidate_reviews(
                (
                    RoleRecord(
                        "page-4",
                        "Rejected Role",
                        RoleStatus.REJECTED,
                    ),
                ),
                (
                    ReviewDecision(
                        "Rejected Role",
                        RoleStatus.APPROVED,
                    ),
                ),
                date(2026, 9, 16),
            )

    def test_unknown_role_is_rejected(self) -> None:
        with self.assertRaises(CandidateReviewError):
            plan_candidate_reviews(
                (),
                (
                    ReviewDecision(
                        "Unknown Role",
                        RoleStatus.APPROVED,
                    ),
                ),
                date(2026, 9, 16),
            )

    def test_ambiguous_existing_role_names_are_rejected(self) -> None:
        with self.assertRaises(CandidateReviewError):
            plan_candidate_reviews(
                (
                    RoleRecord(
                        "page-5",
                        "Agent Security Engineer",
                        RoleStatus.CANDIDATE,
                    ),
                    RoleRecord(
                        "page-6",
                        " agent  security engineer ",
                        RoleStatus.CANDIDATE,
                    ),
                ),
                (
                    ReviewDecision(
                        "Agent Security Engineer",
                        RoleStatus.APPROVED,
                    ),
                ),
                date(2026, 9, 16),
            )

    def test_conflicting_duplicate_decisions_are_rejected(self) -> None:
        with self.assertRaises(CandidateReviewError):
            plan_candidate_reviews(
                (
                    RoleRecord(
                        "page-7",
                        "AI Security Engineer",
                        RoleStatus.CANDIDATE,
                    ),
                ),
                (
                    ReviewDecision(
                        "AI Security Engineer",
                        RoleStatus.APPROVED,
                    ),
                    ReviewDecision(
                        "ai security engineer",
                        RoleStatus.REJECTED,
                    ),
                ),
                date(2026, 9, 16),
            )

    def test_duplicate_matching_decisions_create_one_action(self) -> None:
        plan = plan_candidate_reviews(
            (
                RoleRecord(
                    "page-8",
                    "AI Platform Security",
                    RoleStatus.CANDIDATE,
                ),
            ),
            (
                ReviewDecision(
                    "AI Platform Security",
                    RoleStatus.APPROVED,
                ),
                ReviewDecision(
                    "ai platform security",
                    RoleStatus.APPROVED,
                ),
            ),
            date(2026, 9, 16),
        )

        self.assertEqual(len(plan.actions), 1)

    def test_duplicate_decisions_with_different_notes_are_rejected(self) -> None:
        with self.assertRaises(CandidateReviewError):
            plan_candidate_reviews(
                (
                    RoleRecord(
                        "page-8",
                        "AI Platform Security",
                        RoleStatus.CANDIDATE,
                    ),
                ),
                (
                    ReviewDecision(
                        "AI Platform Security",
                        RoleStatus.APPROVED,
                        "첫 번째 메모",
                    ),
                    ReviewDecision(
                        "ai platform security",
                        RoleStatus.APPROVED,
                        "두 번째 메모",
                    ),
                ),
                date(2026, 9, 16),
            )

    def test_candidate_is_not_a_valid_review_target(self) -> None:
        with self.assertRaises(CandidateReviewError):
            ReviewDecision(
                "Agent Security Engineer",
                RoleStatus.CANDIDATE,
            )

    def test_empty_decision_list_is_rejected(self) -> None:
        with self.assertRaises(CandidateReviewError):
            plan_candidate_reviews((), (), date(2026, 9, 16))

    def test_notion_update_contains_status_date_and_trimmed_note(self) -> None:
        plan = plan_candidate_reviews(
            (
                RoleRecord(
                    "page-9",
                    "Unsupported Security Role",
                    RoleStatus.CANDIDATE,
                ),
            ),
            (
                ReviewDecision(
                    "Unsupported Security Role",
                    RoleStatus.REJECTED,
                    "  근거가 부족함  ",
                ),
            ),
            date(2026, 9, 16),
        )

        updates = build_notion_role_updates(plan)

        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0].record_id, "page-9")
        self.assertEqual(
            updates[0].properties,
            {
                "상태": {"select": {"name": "거절"}},
                "최근 검토일": {"date": {"start": "2026-09-16"}},
                "메모": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "근거가 부족함"},
                        }
                    ]
                },
            },
        )

    def test_approval_without_note_preserves_existing_notion_notes(self) -> None:
        plan = plan_candidate_reviews(
            (
                RoleRecord(
                    "page-10",
                    "Agent Security Engineer",
                    RoleStatus.CANDIDATE,
                ),
            ),
            (
                ReviewDecision(
                    "Agent Security Engineer",
                    RoleStatus.APPROVED,
                ),
            ),
            date(2026, 9, 16),
        )

        properties = build_notion_role_updates(plan)[0].properties

        self.assertEqual(properties["상태"], {"select": {"name": "승인"}})
        self.assertNotIn("메모", properties)

    def test_apply_candidate_review_plan_updates_every_planned_record(self) -> None:
        plan = plan_candidate_reviews(
            (
                RoleRecord("page-11", "AI Role", RoleStatus.CANDIDATE),
                RoleRecord("page-12", "Security Role", RoleStatus.CANDIDATE),
                RoleRecord("page-13", "Existing Role", RoleStatus.APPROVED),
            ),
            (
                ReviewDecision("AI Role", RoleStatus.APPROVED),
                ReviewDecision("Security Role", RoleStatus.REJECTED, "근거 부족"),
                ReviewDecision("Existing Role", RoleStatus.APPROVED),
            ),
            date(2026, 9, 16),
        )
        calls: list[tuple[str, dict[str, object]]] = []

        result = apply_candidate_review_plan(
            plan,
            lambda record_id, properties: calls.append((record_id, properties)),
        )

        self.assertEqual([record_id for record_id, _ in calls], ["page-11", "page-12"])
        self.assertEqual(result.applied_record_ids, ("page-11", "page-12"))
        self.assertEqual(result.unchanged_record_ids, ("page-13",))

    def test_apply_failure_reports_completed_and_failed_record_ids(self) -> None:
        plan = ReviewPlan(
            actions=(
                ReviewAction(
                    "page-14",
                    "AI Role",
                    RoleStatus.CANDIDATE,
                    RoleStatus.APPROVED,
                    date(2026, 9, 16),
                    "",
                ),
                ReviewAction(
                    "page-15",
                    "Security Role",
                    RoleStatus.CANDIDATE,
                    RoleStatus.REJECTED,
                    date(2026, 9, 16),
                    "근거 부족",
                ),
            ),
            unchanged=(),
        )

        def fail_second_update(
            record_id: str,
            properties: dict[str, object],
        ) -> None:
            if record_id == "page-15":
                raise RuntimeError("Notion write failed")

        with self.assertRaises(CandidateReviewApplyError) as context:
            apply_candidate_review_plan(plan, fail_second_update)

        self.assertEqual(context.exception.failed_record_id, "page-15")
        self.assertEqual(context.exception.applied_record_ids, ("page-14",))

    def test_invalid_later_action_prevents_every_notion_write(self) -> None:
        plan = ReviewPlan(
            actions=(
                ReviewAction(
                    "page-16",
                    "AI Role",
                    RoleStatus.CANDIDATE,
                    RoleStatus.APPROVED,
                    date(2026, 9, 16),
                    "",
                ),
                ReviewAction(
                    "page-17",
                    "Already Approved Role",
                    RoleStatus.APPROVED,
                    RoleStatus.REJECTED,
                    date(2026, 9, 16),
                    "재검토",
                ),
            ),
            unchanged=(),
        )
        calls: list[str] = []

        with self.assertRaises(CandidateReviewError):
            apply_candidate_review_plan(
                plan,
                lambda record_id, properties: calls.append(record_id),
            )

        self.assertEqual(calls, [])

    def test_skill_does_not_route_new_jobs_into_legacy_candidate_workflow(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("새 workflow에서 실행하거나 Roles DB를 다시 만들지 않습니다", skill)
        self.assertNotIn("plan_candidate_reviews", skill)
        self.assertNotIn("build_notion_role_updates", skill)


if __name__ == "__main__":
    unittest.main()
