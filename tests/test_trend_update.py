from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.role_discovery import (
    Category,
    RoleStatus,
    default_period,
)
from ai_security_career_tracker.trend_update import (
    ApprovedRole,
    RoleSnapshotRecord,
    SOUTH_KOREA_JOB_MARKET,
    TrendApplyError,
    TrendObservation,
    TrendSourceType,
    TrendUpdatePlan,
    TrendValidationError,
    apply_trend_update_plan,
    build_notion_trend_pages,
    build_trend_search_tasks,
    parse_trend_observations,
    plan_trend_update,
    select_approved_roles,
)


PERIOD = default_period(date(2026, 9, 17))
APPROVED = ApprovedRole("role-1", "AI Security Engineer", Category.AI_SECURITY)


def observation(
    *,
    source_type: TrendSourceType = TrendSourceType.RESEARCH,
    url: str = "https://research.example/ai-security-agents",
    published_on: date = date(2026, 9, 15),
    role_names: tuple[str, ...] = ("AI Security Engineer",),
    domain: Category = Category.AI_SECURITY,
    job_location: str | None = None,
    job_market: str | None = None,
) -> TrendObservation:
    return TrendObservation(
        title="Securing agentic AI systems",
        summary="새로운 에이전트 보안 통제 방법을 설명합니다.",
        key_insight="AI Security Engineer에게 정책 집행 역량이 중요해집니다.",
        source_type=source_type,
        source_name="Example Research",
        original_url=url,
        published_on=published_on,
        related_role_names=role_names,
        domain=domain,
        job_location=job_location,
        job_market=job_market,
    )


class TrendUpdateTests(unittest.TestCase):
    def test_only_approved_roles_are_selected(self) -> None:
        selected = select_approved_roles(
            (
                RoleSnapshotRecord(
                    "role-1",
                    "AI Security Engineer",
                    Category.AI_SECURITY,
                    RoleStatus.APPROVED,
                ),
                RoleSnapshotRecord(
                    "role-2",
                    "AI Agent Engineer",
                    Category.AI,
                    RoleStatus.CANDIDATE,
                ),
                RoleSnapshotRecord(
                    "role-3",
                    "Cloud Security Engineer",
                    Category.SECURITY,
                    RoleStatus.REJECTED,
                ),
            )
        )

        self.assertEqual(selected, (APPROVED,))

    def test_search_tasks_are_created_only_for_approved_roles(self) -> None:
        tasks = build_trend_search_tasks(
            (
                RoleSnapshotRecord(
                    "role-1",
                    "AI Security Engineer",
                    Category.AI_SECURITY,
                    RoleStatus.APPROVED,
                ),
                RoleSnapshotRecord(
                    "role-2",
                    "AI Engineer",
                    Category.AI,
                    RoleStatus.CANDIDATE,
                ),
            ),
            PERIOD,
        )

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].role.record_id, "role-1")
        self.assertIn('"AI Security Engineer"', tasks[0].query)
        self.assertIn("-site:reddit.com", tasks[0].query)

    def test_duplicate_role_snapshot_names_are_rejected(self) -> None:
        with self.assertRaises(TrendValidationError):
            select_approved_roles(
                (
                    RoleSnapshotRecord(
                        "role-1",
                        "AI Security Engineer",
                        Category.AI_SECURITY,
                        RoleStatus.APPROVED,
                    ),
                    RoleSnapshotRecord(
                        "role-2",
                        " ai security engineer ",
                        Category.AI_SECURITY,
                        RoleStatus.APPROVED,
                    ),
                )
            )

    def test_candidate_cannot_be_used_as_related_role(self) -> None:
        with self.assertRaisesRegex(TrendValidationError, "must be Approved"):
            plan_trend_update(
                (observation(role_names=("AI Agent Engineer",)),),
                (APPROVED,),
                (),
                PERIOD,
                date(2026, 9, 17),
            )

    def test_source_outside_period_is_rejected(self) -> None:
        with self.assertRaisesRegex(TrendValidationError, "outside the search period"):
            plan_trend_update(
                (observation(published_on=date(2026, 9, 10)),),
                (APPROVED,),
                (),
                PERIOD,
                date(2026, 9, 17),
            )

    def test_existing_exact_url_is_skipped(self) -> None:
        item = observation()
        plan = plan_trend_update(
            (item,),
            (APPROVED,),
            (item.original_url,),
            PERIOD,
            date(2026, 9, 17),
        )

        self.assertEqual(plan.trends, ())
        self.assertEqual(plan.skipped_existing_urls, (item.original_url,))

    def test_duplicate_url_in_same_result_is_rejected(self) -> None:
        with self.assertRaisesRegex(TrendValidationError, "Duplicate URL"):
            plan_trend_update(
                (observation(), observation()),
                (APPROVED,),
                (),
                PERIOD,
                date(2026, 9, 17),
            )

    def test_community_and_social_sources_are_rejected(self) -> None:
        for url in (
            "https://www.reddit.com/r/security/comments/1",
            "https://news.ycombinator.com/item?id=1",
            "https://x.com/example/status/1",
        ):
            with self.subTest(url=url), self.assertRaises(TrendValidationError):
                observation(url=url)

    def test_global_research_source_is_allowed(self) -> None:
        item = observation()
        plan = plan_trend_update(
            (item,),
            (APPROVED,),
            (),
            PERIOD,
            date(2026, 9, 17),
        )

        self.assertEqual(plan.trends[0].observation.source_type, TrendSourceType.RESEARCH)

    def test_job_posting_requires_south_korea_location(self) -> None:
        with self.assertRaisesRegex(TrendValidationError, "South Korea job market"):
            observation(
                source_type=TrendSourceType.JOB_POSTING,
                job_location="San Francisco, California",
                job_market="United States",
            )

    def test_south_korea_job_posting_is_allowed(self) -> None:
        item = observation(
            source_type=TrendSourceType.JOB_POSTING,
            job_location="Seoul",
            job_market=SOUTH_KOREA_JOB_MARKET,
        )

        self.assertEqual(item.job_market, SOUTH_KOREA_JOB_MARKET)

    def test_domain_must_match_a_related_role(self) -> None:
        with self.assertRaisesRegex(TrendValidationError, "Domain must match"):
            plan_trend_update(
                (observation(domain=Category.AI),),
                (APPROVED,),
                (),
                PERIOD,
                date(2026, 9, 17),
            )

    def test_notion_page_contains_every_trends_db_property(self) -> None:
        plan = plan_trend_update(
            (observation(),),
            (APPROVED,),
            (),
            PERIOD,
            date(2026, 9, 17),
        )

        page = build_notion_trend_pages(plan)[0]

        self.assertEqual(
            set(page.properties),
            {
                "Title",
                "Summary",
                "Key Insight",
                "Source Type",
                "Source Name",
                "Original URL",
                "Published Date",
                "Collected Date",
                "Related Roles",
                "Domain",
            },
        )
        self.assertEqual(
            page.properties["Related Roles"],
            {"relation": [{"id": "role-1"}]},
        )
        self.assertEqual(
            page.properties["Domain"],
            {"select": {"name": "AI × Security"}},
        )

    def test_apply_failure_reports_created_and_failed_urls(self) -> None:
        second = observation(url="https://research.example/second")
        plan = plan_trend_update(
            (observation(), second),
            (APPROVED,),
            (),
            PERIOD,
            date(2026, 9, 17),
        )
        calls: list[str] = []

        def fail_second(properties: dict[str, object]) -> None:
            url = properties["Original URL"]["url"]  # type: ignore[index]
            calls.append(url)
            if url == second.original_url:
                raise RuntimeError("Notion write failed")

        with self.assertRaises(TrendApplyError) as context:
            apply_trend_update_plan(plan, fail_second)

        self.assertEqual(context.exception.failed_url, second.original_url)
        self.assertEqual(
            context.exception.created_urls,
            ("https://research.example/ai-security-agents",),
        )

    def test_invalid_later_page_prevents_every_write(self) -> None:
        valid_plan = plan_trend_update(
            (observation(),),
            (APPROVED,),
            (),
            PERIOD,
            date(2026, 9, 17),
        )
        invalid = valid_plan.trends[0]
        plan = TrendUpdatePlan(
            trends=(
                invalid,
                type(invalid)(invalid.observation, (), invalid.collected_on),
            ),
            skipped_existing_urls=(),
        )
        calls: list[dict[str, object]] = []

        with self.assertRaises(TrendValidationError):
            apply_trend_update_plan(plan, calls.append)

        self.assertEqual(calls, [])

    def test_structured_result_parser_builds_observation(self) -> None:
        parsed = parse_trend_observations(
            {
                "observations": [
                    {
                        "title": "Securing agentic AI systems",
                        "summary": "요약",
                        "key_insight": "핵심 발견",
                        "source_type": "Research",
                        "source_name": "Example Research",
                        "original_url": "https://research.example/agent-security",
                        "published_date": "2026-09-15",
                        "related_roles": ["AI Security Engineer"],
                        "domain": "AI × Security",
                    }
                ]
            }
        )

        self.assertEqual(parsed[0].published_on, date(2026, 9, 15))
        self.assertEqual(parsed[0].related_role_names, ("AI Security Engineer",))

    def test_skill_documents_safe_trend_update_workflow(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        reference = (ROOT / "references" / "trend-update.md").read_text(
            encoding="utf-8"
        )

        for requirement in (
            "references/trend-update.md",
            "build_trend_search_tasks",
            "plan_trend_update",
            "실제 Notion 쓰기 직전",
        ):
            with self.subTest(skill_requirement=requirement):
                self.assertIn(requirement, skill)
        for requirement in (
            "Approved",
            "Published Date",
            "Original URL",
            "Related Roles",
            "TrendApplyError",
        ):
            with self.subTest(reference_requirement=requirement):
                self.assertIn(requirement, reference)


if __name__ == "__main__":
    unittest.main()
