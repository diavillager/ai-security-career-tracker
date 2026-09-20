from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.job_discovery import (
    DuplicateJob,
    DuplicateReason,
    EmploymentType,
    ExperienceLevel,
    JobDiscoveryPlan,
    JobDomain,
    JobAssessment,
    JobObservation,
    JobSourceType,
    PlannedJob,
    PostingStatus,
    ReviewReason,
    ReviewStatus,
    WorkMode,
)
from ai_security_career_tracker.job_notion_write import (
    EXPECTED_JOBS_PROPERTY_TYPES,
    JobNotionApplyError,
    JobNotionWriteError,
    JobsDatabaseSnapshot,
    apply_job_discovery_plan,
    build_notion_job_pages,
)
from ai_security_career_tracker.notion_databases import NotionDatabaseConfig
from ai_security_career_tracker.notion_properties import (
    JOB_ORIGINAL_URL,
    JOB_REVIEW_STATUS,
    JOB_TECHNOLOGY_KEYWORDS,
)


def observation(
    *,
    url: str = "https://careers.example/jobs/1",
    canonical_url: str | None = None,
    title: str = "AI Security Engineer",
    keyword: str = "IAM",
) -> JobObservation:
    return JobObservation(
        source_name="Example Careers",
        source_type=JobSourceType.EMPLOYER,
        source_url=url,
        employer_name="Example",
        original_title=title,
        recognized_role="AI Security Engineer",
        domain=JobDomain.AI_SECURITY,
        classification_basis="AI 시스템의 보안 업무를 담당합니다.",
        responsibilities=("AI 서비스 위협 모델링",),
        requirements=("보안 엔지니어링 경험",),
        technology_keywords=(keyword,),
        location="서울",
        job_market="South Korea",
        experience_level=ExperienceLevel.EXPERIENCED,
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        published_on=date(2026, 9, 20),
        deadline=None,
        posting_status=PostingStatus.OPEN,
        collected_on=date(2026, 9, 20),
        search_routes=(JobDomain.AI_SECURITY,),
        canonical_url=canonical_url,
    )


def planned(
    item: JobObservation | None = None,
    status: ReviewStatus = ReviewStatus.ELIGIBLE,
) -> PlannedJob:
    return PlannedJob(
        observation=item or observation(),
        status=status,
        reasons=(
            (ReviewReason.MISSING_PUBLISHED_DATE,)
            if status is ReviewStatus.NEEDS_REVIEW
            else ()
        ),
    )


CONFIG = NotionDatabaseConfig(
    project_page_url="https://www.notion.so/project",
    jobs_database_id="jobs-data-source",
    trends_database_id="trends-data-source",
)


def target(*, keyword_options: frozenset[str] = frozenset({"IAM"})) -> JobsDatabaseSnapshot:
    option_names: dict[str, frozenset[str]] = {}
    for name, property_type in EXPECTED_JOBS_PROPERTY_TYPES.items():
        if property_type in {"select", "multi_select"}:
            option_names[name] = frozenset()
    option_names.update(
        {
            "직무 분야": frozenset({"AI", "Security", "AI × Security"}),
            "검토 상태": frozenset({"적합", "검토 필요"}),
            "경력 수준": frozenset({"신입", "경력", "신입·경력", "미확인"}),
            JOB_TECHNOLOGY_KEYWORDS: keyword_options,
            "고용 형태": frozenset({"정규직", "계약직", "인턴", "기타", "미확인"}),
            "근무 방식": frozenset({"출근", "하이브리드", "원격", "미확인"}),
            "모집 상태": frozenset({"모집 중", "마감", "미확인"}),
            "관심 상태": frozenset({"신규", "관심", "지원 예정", "지원", "제외"}),
            "출처 유형": frozenset({"기업 공식", "Saramin", "JobKorea", "Wanted", "Jumpit", "기타"}),
            "게시일 상태": frozenset({"확인", "미확인"}),
            "검색 경로": frozenset({"AI", "Security", "AI × Security"}),
            "변경 상태": frozenset({"신규", "변경됨", "변경 없음"}),
        }
    )
    return JobsDatabaseSnapshot(
        data_source_id="jobs-data-source",
        property_types=dict(EXPECTED_JOBS_PROPERTY_TYPES),
        options=option_names,
    )


class JobNotionWriteTests(unittest.TestCase):
    def test_only_eligible_and_needs_review_jobs_are_written(self) -> None:
        review_item = replace(
            observation(url="https://careers.example/jobs/2", title="Security Engineer"),
            published_on=None,
        )
        plan = JobDiscoveryPlan(
            eligible=(planned(),),
            needs_review=(planned(review_item, ReviewStatus.NEEDS_REVIEW),),
            excluded=(
                JobAssessment(
                    observation(url="https://careers.example/jobs/overseas"),
                    ReviewStatus.EXCLUDED,
                    (ReviewReason.OVERSEAS,),
                ),
            ),
            duplicates=(
                DuplicateJob(
                    observation(url="https://careers.example/jobs/duplicate"),
                    DuplicateReason.URL,
                    existing_page_id="existing-page",
                ),
            ),
        )
        calls: list[tuple[str, dict[str, object]]] = []

        result = apply_job_discovery_plan(
            plan,
            CONFIG,
            target(),
            lambda db, props: calls.append((db, props)),
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual({call[0] for call in calls}, {"jobs-data-source"})
        self.assertEqual(result.eligible_created, 1)
        self.assertEqual(result.needs_review_created, 1)
        self.assertEqual(result.excluded_not_written, 1)
        self.assertEqual(result.duplicates_not_written, 1)
        self.assertEqual(
            calls[1][1][JOB_REVIEW_STATUS],
            {"select": {"name": "검토 필요"}},
        )

    def test_configured_identifier_must_match_live_snapshot(self) -> None:
        mismatched = replace(target(), data_source_id="different-data-source")
        calls: list[dict[str, object]] = []

        with self.assertRaisesRegex(JobNotionWriteError, "does not match"):
            apply_job_discovery_plan(
                JobDiscoveryPlan((planned(),), (), (), ()),
                CONFIG,
                mismatched,
                lambda _db, props: calls.append(props),
            )

        self.assertEqual(calls, [])

    def test_wrong_property_type_prevents_every_write(self) -> None:
        property_types = dict(EXPECTED_JOBS_PROPERTY_TYPES)
        property_types["공고명"] = "rich_text"
        changed = replace(target(), property_types=property_types)
        calls: list[dict[str, object]] = []

        with self.assertRaisesRegex(JobNotionWriteError, "공고명"):
            apply_job_discovery_plan(
                JobDiscoveryPlan((planned(),), (), (), ()),
                CONFIG,
                changed,
                lambda _db, props: calls.append(props),
            )

        self.assertEqual(calls, [])

    def test_live_notion_text_schema_is_accepted_for_rich_text_payloads(self) -> None:
        live_property_types = {
            name: ("text" if property_type == "rich_text" else property_type)
            for name, property_type in EXPECTED_JOBS_PROPERTY_TYPES.items()
        }
        live_target = replace(target(), property_types=live_property_types)
        calls: list[dict[str, object]] = []

        result = apply_job_discovery_plan(
            JobDiscoveryPlan((planned(),), (), (), ()),
            CONFIG,
            live_target,
            lambda _db, props: calls.append(props),
        )

        self.assertEqual(result.created_urls, ("https://careers.example/jobs/1",))
        self.assertEqual(len(calls), 1)

    def test_missing_keyword_option_prevents_every_write(self) -> None:
        plan = JobDiscoveryPlan(
            eligible=(planned(observation(keyword="Model Security")),),
            needs_review=(),
            excluded=(),
            duplicates=(),
        )
        calls: list[dict[str, object]] = []

        with self.assertRaisesRegex(JobNotionWriteError, "Model Security"):
            apply_job_discovery_plan(
                plan,
                CONFIG,
                target(),
                lambda _db, props: calls.append(props),
            )

        self.assertEqual(calls, [])

    def test_all_pages_are_validated_before_first_write(self) -> None:
        plan = JobDiscoveryPlan(
            eligible=(
                planned(),
                planned(observation(url="https://careers.example/jobs/2", keyword="RAG")),
            ),
            needs_review=(),
            excluded=(),
            duplicates=(),
        )
        calls: list[dict[str, object]] = []

        with self.assertRaises(JobNotionWriteError):
            apply_job_discovery_plan(
                plan,
                CONFIG,
                target(),
                lambda _db, props: calls.append(props),
            )

        self.assertEqual(calls, [])

    def test_misgrouped_status_prevents_every_write(self) -> None:
        plan = JobDiscoveryPlan(
            eligible=(planned(status=ReviewStatus.NEEDS_REVIEW),),
            needs_review=(),
            excluded=(),
            duplicates=(),
        )
        calls: list[dict[str, object]] = []

        with self.assertRaisesRegex(JobNotionWriteError, "eligible group"):
            apply_job_discovery_plan(
                plan,
                CONFIG,
                target(),
                lambda _db, props: calls.append(props),
            )

        self.assertEqual(calls, [])

    def test_apply_failure_reports_created_and_failed_urls(self) -> None:
        second_url = "https://careers.example/jobs/2"
        plan = JobDiscoveryPlan(
            eligible=(planned(), planned(observation(url=second_url))),
            needs_review=(),
            excluded=(),
            duplicates=(),
        )

        def fail_second(_database_id: str, properties: dict[str, object]) -> None:
            if properties[JOB_ORIGINAL_URL]["url"] == second_url:  # type: ignore[index]
                raise RuntimeError("Notion write failed")

        with self.assertRaises(JobNotionApplyError) as context:
            apply_job_discovery_plan(plan, CONFIG, target(), fail_second)

        self.assertEqual(context.exception.failed_url, second_url)
        self.assertEqual(
            context.exception.created_urls,
            ("https://careers.example/jobs/1",),
        )

    def test_verified_canonical_url_is_written_and_reported(self) -> None:
        canonical = "https://careers.example/jobs/canonical"
        plan = JobDiscoveryPlan(
            eligible=(planned(observation(canonical_url=canonical)),),
            needs_review=(),
            excluded=(),
            duplicates=(),
        )

        pages = build_notion_job_pages(plan)
        result = apply_job_discovery_plan(plan, CONFIG, target(), lambda _db, _props: None)

        self.assertEqual(pages[0].source_url, canonical)
        self.assertEqual(pages[0].properties[JOB_ORIGINAL_URL], {"url": canonical})
        self.assertEqual(result.created_urls, (canonical,))

    def test_tracking_variants_cannot_be_written_twice(self) -> None:
        plan = JobDiscoveryPlan(
            eligible=(
                planned(observation(url="https://careers.example/jobs/1?id=42")),
                planned(
                    observation(
                        url=(
                            "https://CAREERS.example/jobs/1"
                            "?utm_source=search&id=42#details"
                        )
                    )
                ),
            ),
            needs_review=(),
            excluded=(),
            duplicates=(),
        )

        with self.assertRaisesRegex(JobNotionWriteError, "duplicate stored URL"):
            build_notion_job_pages(plan)

    def test_long_rich_text_is_split_without_losing_content(self) -> None:
        long_text = "가" * 4500
        item = replace(observation(), responsibilities=(long_text,))
        page = build_notion_job_pages(
            JobDiscoveryPlan((planned(item),), (), (), ())
        )[0]
        fragments = page.properties["주요 업무"]["rich_text"]  # type: ignore[index]

        self.assertEqual(
            [len(part["text"]["content"]) for part in fragments],
            [2000, 2000, 500],
        )
        self.assertEqual(
            "".join(part["text"]["content"] for part in fragments),
            long_text,
        )

    def test_skill_documents_approval_and_requery_boundary(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        reference = (ROOT / "references" / "notion-databases.md").read_text(
            encoding="utf-8"
        )

        for requirement in (
            "JobsDatabaseSnapshot",
            "사용자에게 보여주고 승인을 받습니다",
            "apply_job_discovery_plan",
            "자동 삭제하지 않습니다",
        ):
            with self.subTest(skill_requirement=requirement):
                self.assertIn(requirement, skill)
        for requirement in (
            "26개 속성명·유형",
            "쓰기를 시작하지 않는다",
            "생성된 행을 다시 조회",
        ):
            with self.subTest(reference_requirement=requirement):
                self.assertIn(requirement, reference)


if __name__ == "__main__":
    unittest.main()
