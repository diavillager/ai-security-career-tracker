from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.classification import (
    ClassificationValidationError,
    TrendSourceType,
    resolve_related_roles,
    validate_classification_fields,
    validate_domain_role_support,
)
from ai_security_career_tracker.role_discovery import Category


@dataclass(frozen=True)
class Role:
    record_id: str
    role_name: str
    category: Category


class ClassificationRelationTests(unittest.TestCase):
    def test_documentation_uses_independent_trend_multi_selects(self) -> None:
        reference = (ROOT / "references" / "classification-relations.md").read_text(
            encoding="utf-8"
        )
        database_reference = (ROOT / "references" / "notion-databases.md").read_text(
            encoding="utf-8"
        )

        for requirement in (
            "Multi-select",
            "제목 exact match만",
            "요약",
            "취업 시사점",
            "Jobs의 상태나 레거시 Roles workflow를 분류 근거로 사용하지 않습니다",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, reference)
        for requirement in (
            "`관련 직무`는 Jobs relation이 아니라 직무 유형을 담는 Multi-select",
            "Jobs와 Trends는 서로 독립적",
            "AI × Security",
        ):
            with self.subTest(database_requirement=requirement):
                self.assertIn(requirement, database_reference)

    def test_every_prd_source_type_is_supported(self) -> None:
        self.assertEqual(
            {source_type.value for source_type in TrendSourceType},
            {
                "News",
                "Industry Media",
                "Company Blog",
                "Engineering Blog",
                "Press Release",
                "Job Posting",
                "Official Documentation",
                "Research Report",
                "Newsletter",
                "GitHub",
                "Paper",
                "Conference",
                "Government",
                "Other",
            },
        )

    def test_multiple_unique_domains_and_roles_are_valid(self) -> None:
        validate_classification_fields(
            source_type=TrendSourceType.RESEARCH_REPORT,
            domains=(Category.AI, Category.SECURITY),
            related_role_names=("AI Engineer", "Security Engineer"),
            summary="원문에서 발표한 사실을 요약합니다.",
            key_insight="두 직무가 협업해야 하는 이유를 설명합니다.",
            classification_basis="본문의 책임과 기술 범위를 근거로 분류했습니다.",
        )

    def test_empty_or_duplicate_domains_are_rejected(self) -> None:
        for domains in ((), (Category.AI, Category.AI)):
            with self.subTest(domains=domains), self.assertRaises(
                ClassificationValidationError
            ):
                validate_classification_fields(
                    source_type=TrendSourceType.NEWS,
                    domains=domains,
                    related_role_names=("AI Engineer",),
                    summary="사실 요약",
                    key_insight="직무 관련 해석",
                    classification_basis="본문의 AI 책임을 근거로 분류했습니다.",
                )

    def test_duplicate_related_role_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            ClassificationValidationError,
            "duplicate role names",
        ):
            validate_classification_fields(
                source_type=TrendSourceType.NEWS,
                domains=(Category.AI,),
                related_role_names=("AI Engineer", " ai engineer "),
                summary="사실 요약",
                key_insight="직무 관련 해석",
                classification_basis="본문의 AI 책임을 근거로 분류했습니다.",
            )

    def test_summary_and_key_insight_cannot_be_identical(self) -> None:
        with self.assertRaisesRegex(
            ClassificationValidationError,
            "separate values",
        ):
            validate_classification_fields(
                source_type=TrendSourceType.PAPER,
                domains=(Category.AI,),
                related_role_names=("AI Engineer",),
                summary="같은 문장",
                key_insight="같은 문장",
                classification_basis="본문의 연구 내용을 근거로 분류했습니다.",
            )

    def test_classification_basis_is_required(self) -> None:
        with self.assertRaisesRegex(
            ClassificationValidationError,
            "classification basis",
        ):
            validate_classification_fields(
                source_type=TrendSourceType.NEWS,
                domains=(Category.AI,),
                related_role_names=("AI Engineer",),
                summary="사실 요약",
                key_insight="직무 관련 해석",
                classification_basis=" ",
            )

    def test_related_roles_resolve_only_from_approved_snapshot(self) -> None:
        roles = {
            "ai engineer": Role("role-1", "AI Engineer", Category.AI),
        }

        self.assertEqual(
            resolve_related_roles(("AI Engineer",), roles),
            (roles["ai engineer"],),
        )
        with self.assertRaisesRegex(
            ClassificationValidationError,
            "must be Approved",
        ):
            resolve_related_roles(("Security Engineer",), roles)

    def test_ai_security_role_supports_all_three_domains(self) -> None:
        validate_domain_role_support(
            (Category.AI, Category.SECURITY, Category.AI_SECURITY),
            (Category.AI_SECURITY,),
        )

    def test_ai_and_security_roles_support_cross_domain(self) -> None:
        validate_domain_role_support(
            (Category.AI_SECURITY,),
            (Category.AI, Category.SECURITY),
        )

    def test_unrelated_domain_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ClassificationValidationError,
            "must be supported",
        ):
            validate_domain_role_support(
                (Category.SECURITY,),
                (Category.AI,),
            )


if __name__ == "__main__":
    unittest.main()
