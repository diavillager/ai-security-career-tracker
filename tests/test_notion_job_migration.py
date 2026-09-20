from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.job_discovery import (
    ExperienceLevel,
    JobDomain,
    JobSourceType,
)
from ai_security_career_tracker.notion_job_migration import (
    LegacyRoleMigrationInput,
    NotionJobMigrationError,
    jobs_schema_ddl,
    plan_notion_job_migration,
    trends_schema_migration_statements,
)
from ai_security_career_tracker import notion_properties


def legacy_role(*, source_url: str | None = "https://m.saramin.co.kr/job-search/view?rec_idx=54978708") -> LegacyRoleMigrationInput:
    return LegacyRoleMigrationInput(
        page_id="legacy-page-1",
        role_name="기술 보안 엔지니어 채용",
        employer_name="피아스페이스(주)",
        recognized_role="기술 보안 엔지니어",
        domain=JobDomain.SECURITY,
        experience_level=ExperienceLevel.EXPERIENCED,
        responsibilities=("클라우드 기술 보안 체계 설계", "보안 이벤트 분석·대응"),
        technology_keywords=("VPN", "Firewall", "IAM", "Endpoint Security"),
        location="서울 서초구",
        source_type=JobSourceType.SARAMIN,
        source_url=source_url,
        related_urls=("https://www.mt.co.kr/industry/example",),
        posting_id="54978708",
        published_on=date(2026, 9, 8),
        first_discovered_on=date(2026, 9, 18),
        last_reviewed_on=date(2026, 9, 18),
        role_description="AI 인프라 환경의 기술 보안을 담당합니다.",
        evidence_sources="기존 Saramin 공고와 보조 기사 URL 전문",
        legacy_notes="게시일 확인 충돌과 원문 전문 재확인 경고",
        search_routes=(JobDomain.SECURITY,),
    )


class NotionJobSchemaTests(unittest.TestCase):
    def test_jobs_schema_contains_every_approved_property_and_option(self) -> None:
        schema = jobs_schema_ddl()
        expected = {
            value
            for name, value in vars(notion_properties).items()
            if name.startswith("JOB_") and isinstance(value, str)
        }

        self.assertEqual(len(expected), 26)
        for property_name in expected:
            with self.subTest(property_name=property_name):
                self.assertIn(f'"{property_name}"', schema)
        for option in (
            "AI × Security",
            "검토 필요",
            "신입·경력",
            "Saramin",
            "지원 예정",
            "변경 없음",
            "Endpoint Security",
            "보안 운영",
        ):
            self.assertIn(option, schema)

    def test_trends_migration_removes_relation_and_adds_new_fields(self) -> None:
        statements = trends_schema_migration_statements()

        self.assertIn('RENAME COLUMN "핵심 시사점" TO "취업 시사점"', statements)
        self.assertIn('DROP COLUMN "관련 직무"', statements)
        self.assertIn('ADD COLUMN "관련 직무" MULTI_SELECT()', statements)
        for name in ("기술 키워드", "동향 유형", "지역 범위"):
            self.assertIn(f'ADD COLUMN "{name}"', statements)


class LegacyRoleMigrationTests(unittest.TestCase):
    def test_verified_role_becomes_one_needs_review_job_without_writing(self) -> None:
        plan = plan_notion_job_migration((legacy_role(),), trends_row_count=0)

        self.assertEqual(len(plan.job_pages), 1)
        self.assertEqual(plan.archived_role_page_ids, ())
        properties = plan.job_pages[0].properties
        self.assertEqual(
            properties[notion_properties.JOB_TITLE]["title"][0]["text"]["content"],
            "기술 보안 엔지니어 채용",
        )
        self.assertEqual(
            properties[notion_properties.JOB_REVIEW_STATUS],
            {"select": {"name": "검토 필요"}},
        )
        self.assertEqual(
            properties[notion_properties.JOB_PUBLISHED_DATE_STATUS],
            {"select": {"name": "미확인"}},
        )
        self.assertEqual(
            properties[notion_properties.JOB_SOURCE_TYPE],
            {"select": {"name": "Saramin"}},
        )
        self.assertEqual(
            properties[notion_properties.JOB_ORIGINAL_URL]["url"],
            "https://m.saramin.co.kr/job-search/view?rec_idx=54978708",
        )
        related_text = properties[notion_properties.JOB_RELATED_URLS]["rich_text"][0]["text"]["content"]
        self.assertIn("https://www.mt.co.kr/industry/example", related_text)
        note = properties[notion_properties.JOB_REVIEW_NOTES]["rich_text"][0]["text"]["content"]
        self.assertIn("게시일 확인 충돌", note)
        self.assertIn("기존 Saramin 공고", note)
        self.assertEqual(properties[notion_properties.JOB_REQUIREMENTS], {"rich_text": []})

    def test_concept_only_role_is_archived_without_jobs_row(self) -> None:
        plan = plan_notion_job_migration(
            (legacy_role(source_url=None),), trends_row_count=0
        )

        self.assertEqual(plan.job_pages, ())
        self.assertEqual(plan.archived_role_page_ids, ("legacy-page-1",))

    def test_nonempty_trends_blocks_relation_conversion(self) -> None:
        with self.assertRaisesRegex(NotionJobMigrationError, "empty data source"):
            plan_notion_job_migration((legacy_role(),), trends_row_count=1)

    def test_duplicate_legacy_page_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(NotionJobMigrationError, "unique"):
            plan_notion_job_migration(
                (legacy_role(), legacy_role()), trends_row_count=0
            )


if __name__ == "__main__":
    unittest.main()
