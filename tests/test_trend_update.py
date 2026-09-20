from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.classification import TrendSourceType
from ai_security_career_tracker.notion_databases import NotionDatabaseConfig
from ai_security_career_tracker.role_discovery import Category, default_period
from ai_security_career_tracker.trend_update import (
    EXPECTED_TRENDS_PROPERTY_TYPES,
    REGION_SCOPE_TO_NOTION,
    SOUTH_KOREA_JOB_MARKET,
    TREND_TYPE_TO_NOTION,
    RegionScope,
    TrendApplyError,
    TrendObservation,
    TrendType,
    TrendUpdatePlan,
    TrendValidationError,
    TrendsDatabaseSnapshot,
    apply_trend_update_plan,
    build_notion_trend_pages,
    build_trend_search_tasks,
    parse_trend_observations,
    plan_trend_update,
)

PERIOD = default_period(date(2026, 9, 17))
CONFIG = NotionDatabaseConfig("https://notion.example/project", "jobs", "trends")


def observation(
    *,
    url: str = "https://research.example/ai-security-agents",
    published_on: date = date(2026, 9, 15),
    source_type: TrendSourceType = TrendSourceType.RESEARCH_REPORT,
    domains: tuple[Category, ...] = (Category.AI_SECURITY,),
    roles: tuple[str, ...] = ("AI Security Engineer",),
    keywords: tuple[str, ...] = ("LLM", "Prompt Injection"),
    trend_type: TrendType = TrendType.RESEARCH,
    region_scope: RegionScope = RegionScope.GLOBAL,
    canonical_url: str | None = None,
    job_location: str | None = None,
    job_market: str | None = None,
) -> TrendObservation:
    return TrendObservation(
        title="Securing agentic AI systems",
        summary="새로운 에이전트 보안 통제 방법을 설명합니다.",
        career_insight="AI 보안 직무에 정책 집행과 평가 역량이 중요해집니다.",
        source_type=source_type,
        source_name="Example Research",
        original_url=url,
        published_on=published_on,
        related_roles=roles,
        domains=domains,
        technology_keywords=keywords,
        trend_type=trend_type,
        region_scope=region_scope,
        classification_basis="원문이 AI 시스템의 보안 통제를 설명합니다.",
        canonical_url=canonical_url,
        job_location=job_location,
        job_market=job_market,
    )


def target(*, extra_role: str = "AI Security Engineer",
           extra_keyword: str = "Prompt Injection") -> TrendsDatabaseSnapshot:
    options = {
        "출처 유형": frozenset({"연구 보고서", "채용 공고"}),
        "관련 직무": frozenset({extra_role}),
        "관련 분야": frozenset({"AI", "Security", "AI × Security"}),
        "기술 키워드": frozenset({"LLM", extra_keyword}),
        "동향 유형": frozenset(TREND_TYPE_TO_NOTION.values()),
        "지역 범위": frozenset(REGION_SCOPE_TO_NOTION.values()),
    }
    return TrendsDatabaseSnapshot("trends", EXPECTED_TRENDS_PROPERTY_TYPES, options)


class TrendUpdateTests(unittest.TestCase):
    def test_search_tasks_are_field_based_and_jobs_independent(self) -> None:
        tasks = build_trend_search_tasks(PERIOD)
        self.assertEqual(tuple(x.search_route for x in tasks), (
            Category.AI, Category.SECURITY, Category.AI_SECURITY,
        ))
        self.assertTrue(all("-site:reddit.com" in x.query for x in tasks))
        self.assertFalse(any(hasattr(x, "role") for x in tasks))

    def test_required_classification_values_are_validated(self) -> None:
        for change in (
            {"roles": ()}, {"keywords": ()},
            {"domains": (Category.AI, Category.AI)},
        ):
            with self.subTest(change=change), self.assertRaises(TrendValidationError):
                observation(**change)

    def test_source_outside_period_is_rejected(self) -> None:
        with self.assertRaisesRegex(TrendValidationError, "outside the search period"):
            plan_trend_update((observation(published_on=date(2026, 9, 1)),), (), PERIOD, date(2026, 9, 17))

    def test_existing_and_tracking_urls_are_skipped(self) -> None:
        item = observation(url="https://research.example/report?utm_source=x&id=42#top")
        plan = plan_trend_update((item,), ("https://RESEARCH.example/report?id=42",), PERIOD, date(2026, 9, 17))
        self.assertEqual(plan.trends, ())
        self.assertEqual(plan.skipped_existing_urls, (item.original_url,))

    def test_duplicate_urls_in_one_result_are_rejected(self) -> None:
        with self.assertRaisesRegex(TrendValidationError, "after normalization"):
            plan_trend_update((observation(url="https://example.com/a?id=1"), observation(url="https://EXAMPLE.com/a?utm_medium=x&id=1#x")), (), PERIOD, date(2026, 9, 17))

    def test_canonical_url_is_stored(self) -> None:
        canonical = "https://publisher.example/reports/security"
        plan = plan_trend_update((observation(canonical_url=canonical),), (), PERIOD, date(2026, 9, 17))
        self.assertEqual(build_notion_trend_pages(plan)[0].original_url, canonical)

    def test_community_sources_are_rejected(self) -> None:
        for url in ("https://reddit.com/r/security/1", "https://x.com/a/status/1"):
            with self.subTest(url=url), self.assertRaises(TrendValidationError):
                observation(url=url)

    def test_global_non_job_source_is_allowed(self) -> None:
        plan = plan_trend_update((observation(),), (), PERIOD, date(2026, 9, 17))
        self.assertEqual(len(plan.trends), 1)

    def test_job_posting_requires_south_korea(self) -> None:
        with self.assertRaisesRegex(TrendValidationError, "South Korea job market"):
            observation(source_type=TrendSourceType.JOB_POSTING,
                        region_scope=RegionScope.OVERSEAS,
                        job_location="San Francisco", job_market="United States")
        item = observation(source_type=TrendSourceType.JOB_POSTING,
                           region_scope=RegionScope.SOUTH_KOREA,
                           job_location="서울", job_market=SOUTH_KOREA_JOB_MARKET)
        self.assertEqual(item.job_market, SOUTH_KOREA_JOB_MARKET)

    def test_notion_page_uses_all_13_independent_properties(self) -> None:
        plan = plan_trend_update((observation(),), (), PERIOD, date(2026, 9, 17))
        properties = build_notion_trend_pages(plan)[0].properties
        self.assertEqual(set(properties), set(EXPECTED_TRENDS_PROPERTY_TYPES))
        self.assertEqual(properties["관련 직무"], {"multi_select": [{"name": "AI Security Engineer"}]})
        self.assertEqual(properties["기술 키워드"], {"multi_select": [{"name": "LLM"}, {"name": "Prompt Injection"}]})
        self.assertEqual(properties["취업 시사점"], {"rich_text": [{"type": "text", "text": {"content": "AI 보안 직무에 정책 집행과 평가 역량이 중요해집니다."}}]})

    def test_missing_live_option_prevents_every_write(self) -> None:
        plan = plan_trend_update((observation(),), (), PERIOD, date(2026, 9, 17))
        calls: list[object] = []
        with self.assertRaisesRegex(TrendValidationError, "기술 키워드"):
            apply_trend_update_plan(plan, CONFIG, target(extra_keyword="다른 값"), lambda *_: calls.append(True))
        self.assertEqual(calls, [])

    def test_wrong_data_source_prevents_every_write(self) -> None:
        plan = plan_trend_update((observation(),), (), PERIOD, date(2026, 9, 17))
        bad = TrendsDatabaseSnapshot("other", EXPECTED_TRENDS_PROPERTY_TYPES, target().options)
        with self.assertRaisesRegex(TrendValidationError, "does not match"):
            apply_trend_update_plan(plan, CONFIG, bad, lambda *_: None)

    def test_apply_failure_reports_created_and_failed_urls(self) -> None:
        second = observation(url="https://research.example/second")
        plan = plan_trend_update((observation(), second), (), PERIOD, date(2026, 9, 17))
        calls: list[str] = []
        def fail_second(_data_source: str, properties: dict[str, object]) -> None:
            url = properties["원문 URL"]["url"]  # type: ignore[index]
            calls.append(url)
            if url == second.original_url:
                raise RuntimeError("failed")
        with self.assertRaises(TrendApplyError) as context:
            apply_trend_update_plan(plan, CONFIG, target(), fail_second)
        self.assertEqual(context.exception.created_urls, (observation().original_url,))

    def test_structured_parser_builds_independent_observation(self) -> None:
        parsed = parse_trend_observations({"observations": [{
            "title": "Securing agentic AI", "summary": "사실 요약",
            "career_insight": "취업 시사점", "source_type": "Research Report",
            "source_name": "Example", "original_url": "https://example.com/report",
            "published_date": "2026-09-15", "related_roles": ["AI Security Engineer"],
            "domains": ["AI", "Security", "AI × Security"],
            "technology_keywords": ["LLM"], "trend_type": "Research",
            "region_scope": "Global", "classification_basis": "본문 근거",
        }]})
        self.assertEqual(parsed[0].technology_keywords, ("LLM",))
        self.assertEqual(parsed[0].region_scope, RegionScope.GLOBAL)

    def test_documents_activate_independent_trend_update(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        reference = (ROOT / "references" / "trend-update.md").read_text(encoding="utf-8")
        self.assertNotIn("현재 Trend Update 실행은 중단합니다", skill)
        self.assertIn("Jobs DB 상태와 무관", skill)
        self.assertIn("관련 직무", reference)
        self.assertNotIn("Approved", reference)


if __name__ == "__main__":
    unittest.main()
