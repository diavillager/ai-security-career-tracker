from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from ai_security_career_tracker import notion_options, notion_properties
from ai_security_career_tracker.classification import TrendSourceType
from ai_security_career_tracker.job_discovery import (
    EmploymentType,
    ExperienceLevel,
    JobSourceType,
    PostingStatus,
    ReviewStatus,
    WorkMode,
)
from ai_security_career_tracker.role_discovery import RoleStatus


ROOT = Path(__file__).resolve().parents[1]


class ProjectFoundationTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        required = (
            "SKILL.md",
            "agents/openai.yaml",
            "config.example.toml",
            "references/product-requirements.md",
            "references/classification-relations.md",
            "src/ai_security_career_tracker/classification.py",
            "src/ai_security_career_tracker/notion_options.py",
            "src/ai_security_career_tracker/notion_properties.py",
        )

        for relative_path in required:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_skill_frontmatter_uses_expected_name(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertTrue(content.startswith("---\n"))
        self.assertIn("\nname: ai-security-career-tracker\n", content)
        self.assertIn("\ndescription:", content)

    def test_ui_metadata_routes_every_supported_workflow(self) -> None:
        content = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn('display_name: "AI Security Career Tracker"', content)
        self.assertIn("$ai-security-career-tracker", content)
        for workflow in ("채용 공고", "최신 동향"):
            with self.subTest(workflow=workflow):
                self.assertIn(workflow, content)

    def test_skill_reference_links_resolve_inside_package(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        referenced_paths = (
            "references/product-requirements.md",
            "references/notion-databases.md",
            "references/job-discovery-redesign.md",
            "references/job-discovery-agent-contract.md",
            "references/job-evidence-reviewer-contract.md",
            "references/notion-job-discovery-migration-plan.md",
            "references/trend-update.md",
        )

        for relative_path in referenced_paths:
            with self.subTest(reference=relative_path):
                self.assertIn(f"]({relative_path})", content)
                self.assertTrue((ROOT / relative_path).is_file())

    def test_default_configuration_matches_confirmed_decisions(self) -> None:
        with (ROOT / "config.example.toml").open("rb") as config_file:
            config = tomllib.load(config_file)

        self.assertEqual(config["project"]["timezone"], "Asia/Seoul")
        self.assertEqual(config["project"]["default_search_days"], 7)
        self.assertEqual(config["search"]["provider"], "codex_web")

    def test_database_identifiers_are_not_in_example_config(self) -> None:
        with (ROOT / "config.example.toml").open("rb") as config_file:
            notion = tomllib.load(config_file)["notion"]

        self.assertEqual(notion["jobs_database_id"], "")
        self.assertEqual(notion["trends_database_id"], "")

    def test_private_local_config_is_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

        self.assertIn(".env", ignored)
        self.assertIn("config.toml", ignored)

    def test_notion_property_names_cover_jobs_and_target_trends(self) -> None:
        jobs = {
            value
            for name, value in vars(notion_properties).items()
            if name.startswith("JOB_") and isinstance(value, str)
        }
        self.assertEqual(len(jobs), 26)
        self.assertIn("공고명", jobs)
        self.assertIn("회사명", jobs)
        self.assertIn("인식한 직무", jobs)
        self.assertIn("검토 상태", jobs)
        self.assertIn("원문 URL", jobs)
        self.assertIn("검토 메모", jobs)

        target_trends = {
            notion_properties.TREND_TITLE,
            notion_properties.TREND_SUMMARY,
            notion_properties.TREND_CAREER_INSIGHT,
            notion_properties.TREND_SOURCE_TYPE,
            notion_properties.TREND_SOURCE_NAME,
            notion_properties.TREND_ORIGINAL_URL,
            notion_properties.TREND_PUBLISHED_DATE,
            notion_properties.TREND_COLLECTED_DATE,
            notion_properties.TREND_RELATED_ROLES,
            notion_properties.TREND_DOMAIN,
            notion_properties.TREND_TECHNOLOGY_KEYWORDS,
            notion_properties.TREND_TYPE,
            notion_properties.TREND_REGION_SCOPE,
        }
        self.assertEqual(
            target_trends,
            {
                "제목",
                "요약",
                "취업 시사점",
                "출처 유형",
                "출처명",
                "원문 URL",
                "게시일",
                "수집일",
                "관련 직무",
                "관련 분야",
                "기술 키워드",
                "동향 유형",
                "지역 범위",
            },
        )

    def test_notion_options_are_localized_without_changing_internal_enums(self) -> None:
        self.assertEqual(
            notion_options.JOB_REVIEW_STATUS_TO_NOTION,
            {
                ReviewStatus.ELIGIBLE: "적합",
                ReviewStatus.NEEDS_REVIEW: "검토 필요",
            },
        )
        self.assertEqual(
            notion_options.JOB_EXPERIENCE_LEVEL_TO_NOTION[ExperienceLevel.BOTH],
            "신입·경력",
        )
        self.assertEqual(
            notion_options.JOB_EMPLOYMENT_TYPE_TO_NOTION[EmploymentType.FULL_TIME],
            "정규직",
        )
        self.assertEqual(
            notion_options.JOB_WORK_MODE_TO_NOTION[WorkMode.HYBRID],
            "하이브리드",
        )
        self.assertEqual(
            notion_options.JOB_POSTING_STATUS_TO_NOTION[PostingStatus.OPEN],
            "모집 중",
        )
        self.assertEqual(
            notion_options.JOB_SOURCE_TYPE_TO_NOTION[JobSourceType.SARAMIN],
            "Saramin",
        )
        self.assertEqual(
            notion_options.ROLE_STATUS_TO_NOTION,
            {
                RoleStatus.CANDIDATE: "후보",
                RoleStatus.APPROVED: "승인",
                RoleStatus.REJECTED: "거절",
            },
        )
        self.assertEqual(
            notion_options.TREND_SOURCE_TYPE_TO_NOTION,
            {
                TrendSourceType.NEWS: "뉴스",
                TrendSourceType.INDUSTRY_MEDIA: "업계 매체",
                TrendSourceType.COMPANY_BLOG: "기업 블로그",
                TrendSourceType.ENGINEERING_BLOG: "기술 블로그",
                TrendSourceType.PRESS_RELEASE: "보도자료",
                TrendSourceType.JOB_POSTING: "채용 공고",
                TrendSourceType.OFFICIAL_DOCUMENTATION: "공식 문서",
                TrendSourceType.RESEARCH_REPORT: "연구 보고서",
                TrendSourceType.NEWSLETTER: "뉴스레터",
                TrendSourceType.GITHUB: "GitHub",
                TrendSourceType.PAPER: "논문",
                TrendSourceType.CONFERENCE: "컨퍼런스",
                TrendSourceType.GOVERNMENT: "정부",
                TrendSourceType.OTHER: "기타",
            },
        )
        self.assertEqual(
            notion_options.role_status_from_notion("승인"),
            RoleStatus.APPROVED,
        )
        self.assertEqual(
            notion_options.role_status_from_notion("Approved"),
            RoleStatus.APPROVED,
        )
        self.assertEqual(
            notion_options.trend_source_type_from_notion("GitHub"),
            TrendSourceType.GITHUB,
        )
        self.assertEqual(
            notion_options.trend_source_type_from_notion("Research Report"),
            TrendSourceType.RESEARCH_REPORT,
        )


if __name__ == "__main__":
    unittest.main()
