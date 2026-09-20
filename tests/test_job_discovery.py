from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.job_discovery import (
    JOB_DISCOVERY_AGENT_BY_DOMAIN,
    AgentJobDiscoveryResult,
    DuplicateReason,
    EmploymentType,
    ExistingJob,
    ExperienceLevel,
    JobDiscoveryError,
    JobDomain,
    JobObservation,
    JobSourceType,
    JobReviewAssessment,
    PostingStatus,
    ReviewReason,
    ReviewStatus,
    SearchPeriod,
    WorkMode,
    apply_job_evidence_review,
    build_job_search_tasks,
    consolidate_job_agent_results,
    duplicate_reason,
    evaluate_job,
    plan_job_discovery,
    parse_job_agent_result,
    parse_job_evidence_review,
)


PERIOD = SearchPeriod(date(2026, 8, 20), date(2026, 9, 20))


def job(
    *,
    source_url: str = "https://careers.example/jobs/123",
    employer_name: str = "Example Corp",
    original_title: str = "AI Security Engineer",
    recognized_role: str = "AI 보안 엔지니어",
    domain: JobDomain = JobDomain.AI_SECURITY,
    classification_basis: str = "LLM 위협 모델링과 보안 평가를 담당합니다.",
    responsibilities: tuple[str, ...] = ("LLM 위협 모델링",),
    requirements: tuple[str, ...] = ("Python과 보안 평가 경험",),
    location: str = "서울",
    job_market: str = "South Korea",
    published_on: date | None = date(2026, 9, 10),
    deadline: date | None = date(2026, 10, 10),
    platform_job_id: str | None = "123",
    source_name: str = "Example Careers",
    canonical_url: str | None = None,
    search_routes: tuple[JobDomain, ...] = (JobDomain.AI_SECURITY,),
) -> JobObservation:
    return JobObservation(
        source_name=source_name,
        source_type=JobSourceType.EMPLOYER,
        source_url=source_url,
        employer_name=employer_name,
        original_title=original_title,
        recognized_role=recognized_role,
        domain=domain,
        classification_basis=classification_basis,
        responsibilities=responsibilities,
        requirements=requirements,
        technology_keywords=("LLM", "Threat Modeling"),
        location=location,
        job_market=job_market,
        experience_level=ExperienceLevel.EXPERIENCED,
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        published_on=published_on,
        deadline=deadline,
        posting_status=PostingStatus.OPEN,
        collected_on=date(2026, 9, 20),
        search_routes=search_routes,
        canonical_url=canonical_url,
        platform_job_id=platform_job_id,
    )


def agent_payload(
    route: JobDomain = JobDomain.AI,
    *,
    blockers: list[str] | None = None,
    observations: list[dict[str, object]] | None = None,
) -> str:
    if observations is None:
        observations = [
            {
                "source_name": "Example Careers",
                "source_type": "Employer",
                "source_url": f"https://careers.example/jobs/{route.name.lower()}",
                "canonical_url": None,
                "platform_job_id": route.name.lower(),
                "related_urls": [],
                "employer_name": "Example Corp",
                "original_title": "AI Security Engineer",
                "recognized_role": "AI 보안 엔지니어",
                "domain": "AI × Security",
                "classification_basis": "LLM 위협 모델링과 보안 평가를 담당합니다.",
                "responsibilities": ["LLM 위협 모델링"],
                "requirements": ["Python과 보안 평가 경험"],
                "technology_keywords": ["LLM", "Threat Modeling"],
                "location": "서울",
                "job_market": "South Korea",
                "experience_level": "Experienced",
                "employment_type": "Full-time",
                "work_mode": "Hybrid",
                "published_on": "2026-09-10",
                "deadline": "2026-10-10",
                "posting_status": "Open",
                "collected_on": "2026-09-20",
                "search_routes": [route.value],
            }
        ]
    return json.dumps(
        {
            "run_id": "run-1",
            "agent_name": JOB_DISCOVERY_AGENT_BY_DOMAIN[route],
            "search_route": route.value,
            "job_market": "South Korea",
            "search_period": {"start": "2026-08-20", "end": "2026-09-20"},
            "collected_on": "2026-09-20",
            "search_queries_run": ["대한민국 채용"],
            "source_coverage": [
                {"source_name": "Employer", "queries_run": 1, "results_checked": 3, "originals_opened": 1}
            ],
            "sources_checked": ["Employer"],
            "observations": observations,
            "exclusions": [],
            "blockers": blockers or [],
        },
        ensure_ascii=False,
    )


def review_payload(
    urls: tuple[str, ...],
    *,
    flagged_url: str | None = None,
    omit_url: str | None = None,
    extra_url: str | None = None,
) -> str:
    reviewed = []
    for url in urls:
        if url == omit_url:
            continue
        flagged = url == flagged_url
        reviewed.append(
            {
                "source_url": url,
                "assessment": "flagged" if flagged else "clear",
                "flags": [
                    {"type": "classification_ambiguity", "summary": "분류 재확인이 필요합니다.", "urls": [url]}
                ] if flagged else [],
            }
        )
    if extra_url:
        reviewed.append({"source_url": extra_url, "assessment": "clear", "flags": []})
    return json.dumps(
        {"run_id": "run-1", "agent_name": "job_evidence_reviewer", "reviewed_jobs": reviewed, "blockers": []},
        ensure_ascii=False,
    )


class JobEvaluationTests(unittest.TestCase):
    def test_one_verified_korean_posting_is_eligible(self) -> None:
        assessment = evaluate_job(job(), PERIOD)

        self.assertEqual(assessment.status, ReviewStatus.ELIGIBLE)
        self.assertEqual(assessment.reasons, ())

    def test_missing_published_date_is_reviewed_without_claiming_period(self) -> None:
        assessment = evaluate_job(
            job(published_on=None, deadline=None),
            PERIOD,
        )

        self.assertEqual(assessment.status, ReviewStatus.NEEDS_REVIEW)
        self.assertIn(ReviewReason.MISSING_PUBLISHED_DATE, assessment.reasons)

    def test_outside_period_is_excluded(self) -> None:
        assessment = evaluate_job(
            job(published_on=date(2026, 8, 1), deadline=date(2026, 8, 31)),
            PERIOD,
        )

        self.assertEqual(assessment.status, ReviewStatus.EXCLUDED)
        self.assertIn(ReviewReason.OUTSIDE_PERIOD, assessment.reasons)

    def test_overseas_or_unclear_location_is_excluded(self) -> None:
        overseas = evaluate_job(
            job(location="Tokyo", job_market="Japan"),
            PERIOD,
        )
        unclear = evaluate_job(job(location=""), PERIOD)

        self.assertEqual(overseas.status, ReviewStatus.EXCLUDED)
        self.assertIn(ReviewReason.OVERSEAS, overseas.reasons)
        self.assertEqual(unclear.status, ReviewStatus.EXCLUDED)
        self.assertIn(ReviewReason.UNCLEAR_LOCATION, unclear.reasons)

    def test_missing_details_affect_only_that_posting(self) -> None:
        valid = job()
        incomplete = job(
            source_url="https://careers.example/jobs/456",
            platform_job_id="456",
            employer_name="Other Corp",
            original_title="Security Analyst",
            recognized_role="",
            classification_basis="",
            responsibilities=(),
            requirements=(),
        )

        plan = plan_job_discovery((valid, incomplete), (), PERIOD)

        self.assertEqual(len(plan.eligible), 1)
        self.assertEqual(plan.eligible[0].observation.source_url, valid.source_url)
        self.assertEqual(len(plan.needs_review), 1)
        self.assertIn(
            ReviewReason.MISSING_CLASSIFICATION,
            plan.needs_review[0].reasons,
        )

    def test_all_three_domains_remain_supported(self) -> None:
        for domain in JobDomain:
            assessment = evaluate_job(
                job(domain=domain, search_routes=(domain,)),
                PERIOD,
            )
            self.assertEqual(assessment.status, ReviewStatus.ELIGIBLE)

    def test_search_route_does_not_limit_recognized_domain(self) -> None:
        assessment = evaluate_job(
            job(
                domain=JobDomain.AI_SECURITY,
                search_routes=(JobDomain.AI,),
            ),
            PERIOD,
        )

        self.assertEqual(assessment.status, ReviewStatus.ELIGIBLE)


class JobDuplicateTests(unittest.TestCase):
    def test_tracking_url_variants_are_one_posting_and_preserve_both_urls(self) -> None:
        first = job(
            source_url="https://careers.example/jobs/123?utm_source=search",
        )
        mirror = job(
            source_url="https://careers.example/jobs/123",
            source_name="Domestic Platform",
            platform_job_id=None,
        )

        plan = plan_job_discovery((first, mirror), (), PERIOD)

        self.assertEqual(len(plan.eligible), 1)
        self.assertEqual(len(plan.duplicates), 1)
        self.assertEqual(plan.duplicates[0].reason, DuplicateReason.URL)
        self.assertIn(mirror.source_url, plan.eligible[0].related_urls)

    def test_same_platform_job_id_is_duplicate(self) -> None:
        first = job(source_name="Wanted", source_url="https://wanted.example/a")
        second = job(source_name="Wanted", source_url="https://wanted.example/b")

        self.assertEqual(
            duplicate_reason(first, second),
            DuplicateReason.POSTING_ID,
        )

    def test_matching_posting_facts_are_duplicate(self) -> None:
        first = job(platform_job_id=None)
        mirror = job(
            source_url="https://jobs.example/mirror/1",
            source_name="JobKorea",
            platform_job_id=None,
        )

        self.assertEqual(
            duplicate_reason(first, mirror),
            DuplicateReason.POSTING_FACTS,
        )

    def test_same_title_with_different_date_remains_separate(self) -> None:
        first = job(platform_job_id=None)
        reposted = job(
            source_url="https://careers.example/jobs/789",
            platform_job_id=None,
            published_on=date(2026, 9, 15),
            deadline=date(2026, 10, 15),
        )

        plan = plan_job_discovery((first, reposted), (), PERIOD)

        self.assertEqual(len(plan.eligible), 2)
        self.assertEqual(plan.duplicates, ())

    def test_existing_job_duplicate_does_not_create_new_record(self) -> None:
        observed = job()
        existing = ExistingJob(
            page_id="notion-page-1",
            source_name="Example Careers",
            source_url="https://careers.example/jobs/123",
            employer_name="Example Corp",
            original_title="AI Security Engineer",
            location="서울",
            published_on=date(2026, 9, 10),
            deadline=date(2026, 10, 10),
            platform_job_id="123",
        )

        plan = plan_job_discovery((observed,), (existing,), PERIOD)

        self.assertEqual(plan.eligible, ())
        self.assertEqual(len(plan.duplicates), 1)
        self.assertEqual(plan.duplicates[0].existing_page_id, "notion-page-1")

    def test_same_company_title_without_dates_is_not_merged_by_guess(self) -> None:
        first = job(
            source_url="https://careers.example/jobs/no-date-1",
            platform_job_id=None,
            published_on=None,
            deadline=None,
        )
        second = replace(
            first,
            source_url="https://careers.example/jobs/no-date-2",
        )

        plan = plan_job_discovery((first, second), (), PERIOD)

        self.assertEqual(len(plan.needs_review), 2)
        self.assertEqual(plan.duplicates, ())


class JobValidationTests(unittest.TestCase):
    def test_invalid_source_url_is_rejected_at_boundary(self) -> None:
        with self.assertRaises(JobDiscoveryError):
            job(source_url="not-a-url")

    def test_deadline_before_published_date_is_rejected(self) -> None:
        with self.assertRaises(JobDiscoveryError):
            job(
                published_on=date(2026, 9, 10),
                deadline=date(2026, 9, 1),
            )


class JobAgentFlowTests(unittest.TestCase):
    def test_search_builder_creates_three_routes_with_multiple_queries(self) -> None:
        tasks = build_job_search_tasks(PERIOD)

        self.assertEqual({task.search_route for task in tasks}, set(JobDomain))
        self.assertEqual(
            {task.agent_name for task in tasks},
            set(JOB_DISCOVERY_AGENT_BY_DOMAIN.values()),
        )
        for task in tasks:
            self.assertGreaterEqual(len(task.queries), 5)
            self.assertTrue(any("saramin" in query for query in task.queries))
            self.assertTrue(any("jobkorea" in query for query in task.queries))

    def test_parser_accepts_cross_route_classification(self) -> None:
        result = parse_job_agent_result(agent_payload(JobDomain.AI))

        self.assertIsInstance(result, AgentJobDiscoveryResult)
        self.assertEqual(result.search_route, JobDomain.AI)
        self.assertEqual(result.observations[0].domain, JobDomain.AI_SECURITY)

    def test_missing_route_does_not_discard_valid_posting(self) -> None:
        result = parse_job_agent_result(agent_payload(JobDomain.AI))
        review = parse_job_evidence_review(
            review_payload(tuple(item.source_url for item in result.observations))
        )

        consolidated = consolidate_job_agent_results(
            (result,), "run-1", (), PERIOD, review
        )

        self.assertEqual(len(consolidated.plan.eligible), 1)
        self.assertEqual(consolidated.complete_routes, (JobDomain.AI,))
        self.assertEqual(
            consolidated.incomplete_routes,
            (JobDomain.SECURITY, JobDomain.AI_SECURITY),
        )

    def test_agent_blocker_marks_route_incomplete_without_losing_job(self) -> None:
        result = parse_job_agent_result(
            agent_payload(JobDomain.AI, blockers=["Wanted 접근 제한"])
        )
        review = parse_job_evidence_review(
            review_payload(tuple(item.source_url for item in result.observations))
        )

        consolidated = consolidate_job_agent_results(
            (result,), "run-1", (), PERIOD, review
        )

        self.assertEqual(len(consolidated.plan.eligible), 1)
        self.assertIn(JobDomain.AI, consolidated.incomplete_routes)
        self.assertIn("AI: Wanted 접근 제한", consolidated.blockers)

    def test_reviewer_flag_affects_only_its_posting(self) -> None:
        first = job(source_url="https://careers.example/jobs/one", platform_job_id="one")
        second = job(
            source_url="https://careers.example/jobs/two",
            platform_job_id="two",
            employer_name="Other Corp",
        )
        review = parse_job_evidence_review(
            review_payload((first.source_url, second.source_url), flagged_url=second.source_url)
        )

        reviewed = apply_job_evidence_review((first, second), review)
        plan = plan_job_discovery(reviewed, (), PERIOD)

        self.assertEqual(len(plan.eligible), 1)
        self.assertEqual(plan.eligible[0].observation.source_url, first.source_url)
        self.assertEqual(len(plan.needs_review), 1)
        self.assertIn(ReviewReason.EVIDENCE_FLAGGED, plan.needs_review[0].reasons)

    def test_missing_reviewer_coverage_marks_only_missing_job_for_review(self) -> None:
        first = job(source_url="https://careers.example/jobs/one", platform_job_id="one")
        second = job(
            source_url="https://careers.example/jobs/two",
            platform_job_id="two",
            employer_name="Other Corp",
        )
        review = parse_job_evidence_review(
            review_payload((first.source_url, second.source_url), omit_url=second.source_url)
        )

        plan = plan_job_discovery(
            apply_job_evidence_review((first, second), review), (), PERIOD
        )

        self.assertEqual(len(plan.eligible), 1)
        self.assertEqual(len(plan.needs_review), 1)
        self.assertEqual(plan.needs_review[0].observation.source_url, second.source_url)

    def test_reviewer_cannot_introduce_unobserved_url(self) -> None:
        observation = job()
        review = parse_job_evidence_review(
            review_payload((observation.source_url,), extra_url="https://careers.example/jobs/extra")
        )

        with self.assertRaises(JobDiscoveryError):
            apply_job_evidence_review((observation,), review)


if __name__ == "__main__":
    unittest.main()
