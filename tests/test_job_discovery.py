from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.job_discovery import (
    DuplicateReason,
    EmploymentType,
    ExistingJob,
    ExperienceLevel,
    JobDiscoveryError,
    JobDomain,
    JobObservation,
    JobSourceType,
    PostingStatus,
    ReviewReason,
    ReviewStatus,
    SearchPeriod,
    WorkMode,
    duplicate_reason,
    evaluate_job,
    plan_job_discovery,
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


if __name__ == "__main__":
    unittest.main()
