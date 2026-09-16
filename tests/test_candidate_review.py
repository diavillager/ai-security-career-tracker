from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.candidate_review import (
    CandidateReviewError,
    ReviewDecision,
    RoleRecord,
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

    def test_candidate_is_not_a_valid_review_target(self) -> None:
        with self.assertRaises(CandidateReviewError):
            ReviewDecision(
                "Agent Security Engineer",
                RoleStatus.CANDIDATE,
            )

    def test_empty_decision_list_is_rejected(self) -> None:
        with self.assertRaises(CandidateReviewError):
            plan_candidate_reviews((), (), date(2026, 9, 16))


if __name__ == "__main__":
    unittest.main()
