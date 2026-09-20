"""Deterministic boundaries for evaluating and deduplicating job postings."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import date
from enum import Enum

from .source_urls import SourceUrlError, source_comparison_urls


SOUTH_KOREA_JOB_MARKET = "South Korea"


class JobDiscoveryError(ValueError):
    """Raised when a Job Discovery input is structurally unsafe."""


class JobDomain(str, Enum):
    AI = "AI"
    SECURITY = "Security"
    AI_SECURITY = "AI × Security"


class ExperienceLevel(str, Enum):
    ENTRY = "Entry"
    EXPERIENCED = "Experienced"
    BOTH = "Entry and Experienced"
    UNKNOWN = "Unknown"


class EmploymentType(str, Enum):
    FULL_TIME = "Full-time"
    CONTRACT = "Contract"
    INTERN = "Intern"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class WorkMode(str, Enum):
    ONSITE = "Onsite"
    HYBRID = "Hybrid"
    REMOTE = "Remote"
    UNKNOWN = "Unknown"


class PostingStatus(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"
    UNKNOWN = "Unknown"


class JobSourceType(str, Enum):
    EMPLOYER = "Employer"
    SARAMIN = "Saramin"
    JOBKOREA = "JobKorea"
    WANTED = "Wanted"
    JUMPIT = "Jumpit"
    OTHER = "Other"


class ReviewStatus(str, Enum):
    ELIGIBLE = "Eligible"
    NEEDS_REVIEW = "Needs Review"
    EXCLUDED = "Excluded"


class ReviewReason(str, Enum):
    OUTSIDE_PERIOD = "outside_period"
    OVERSEAS = "overseas"
    UNCLEAR_LOCATION = "unclear_location"
    MISSING_PUBLISHED_DATE = "missing_published_date"
    MISSING_JOB_DETAILS = "missing_job_details"
    MISSING_CLASSIFICATION = "missing_classification"


class DuplicateReason(str, Enum):
    URL = "url"
    POSTING_ID = "posting_id"
    POSTING_FACTS = "posting_facts"


@dataclass(frozen=True)
class SearchPeriod:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise JobDiscoveryError("Search period start must not be after end.")


@dataclass(frozen=True)
class JobObservation:
    source_name: str
    source_type: JobSourceType
    source_url: str
    employer_name: str
    original_title: str
    recognized_role: str
    domain: JobDomain
    classification_basis: str
    responsibilities: tuple[str, ...]
    requirements: tuple[str, ...]
    technology_keywords: tuple[str, ...]
    location: str
    job_market: str
    experience_level: ExperienceLevel
    employment_type: EmploymentType
    work_mode: WorkMode
    published_on: date | None
    deadline: date | None
    posting_status: PostingStatus
    collected_on: date
    search_routes: tuple[JobDomain, ...]
    canonical_url: str | None = None
    platform_job_id: str | None = None
    related_urls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_name.strip():
            raise JobDiscoveryError("Source name must not be blank.")
        try:
            source_comparison_urls(self.source_url, self.canonical_url)
            for url in self.related_urls:
                source_comparison_urls(url)
        except SourceUrlError as error:
            raise JobDiscoveryError(str(error)) from error
        if not self.search_routes:
            raise JobDiscoveryError("At least one search route is required.")
        if self.deadline is not None and self.published_on is not None:
            if self.deadline < self.published_on:
                raise JobDiscoveryError(
                    "Job posting deadline must not be before its published date."
                )


@dataclass(frozen=True)
class ExistingJob:
    page_id: str
    source_name: str
    source_url: str
    employer_name: str
    original_title: str
    location: str
    published_on: date | None
    deadline: date | None
    canonical_url: str | None = None
    platform_job_id: str | None = None
    related_urls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.page_id.strip():
            raise JobDiscoveryError("Existing job page ID must not be blank.")
        try:
            source_comparison_urls(self.source_url, self.canonical_url)
            for url in self.related_urls:
                source_comparison_urls(url)
        except SourceUrlError as error:
            raise JobDiscoveryError(str(error)) from error


@dataclass(frozen=True)
class JobAssessment:
    observation: JobObservation
    status: ReviewStatus
    reasons: tuple[ReviewReason, ...]


@dataclass(frozen=True)
class PlannedJob:
    observation: JobObservation
    status: ReviewStatus
    reasons: tuple[ReviewReason, ...]
    related_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class DuplicateJob:
    observation: JobObservation
    reason: DuplicateReason
    existing_page_id: str | None = None
    matched_source_url: str | None = None


@dataclass(frozen=True)
class JobDiscoveryPlan:
    eligible: tuple[PlannedJob, ...]
    needs_review: tuple[PlannedJob, ...]
    excluded: tuple[JobAssessment, ...]
    duplicates: tuple[DuplicateJob, ...]


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def _normalize_identity_text(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", _normalize_text(value))


def _unique_urls(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        source_comparison_urls(value)
        if value not in seen:
            seen.add(value)
            output.append(value)
    return tuple(output)


def evaluate_job(
    observation: JobObservation,
    period: SearchPeriod,
) -> JobAssessment:
    """Evaluate one posting without requiring supporting evidence from another URL."""
    excluded: list[ReviewReason] = []
    review: list[ReviewReason] = []

    if observation.job_market != SOUTH_KOREA_JOB_MARKET:
        excluded.append(ReviewReason.OVERSEAS)
    if not observation.location.strip():
        excluded.append(ReviewReason.UNCLEAR_LOCATION)
    if observation.published_on is not None and not (
        period.start <= observation.published_on <= period.end
    ):
        excluded.append(ReviewReason.OUTSIDE_PERIOD)
    if not observation.original_title.strip() or not observation.employer_name.strip():
        review.append(ReviewReason.MISSING_JOB_DETAILS)
    if not observation.responsibilities and not observation.requirements:
        review.append(ReviewReason.MISSING_JOB_DETAILS)
    if not observation.recognized_role.strip() or not observation.classification_basis.strip():
        review.append(ReviewReason.MISSING_CLASSIFICATION)
    if observation.published_on is None:
        review.append(ReviewReason.MISSING_PUBLISHED_DATE)

    if excluded:
        return JobAssessment(
            observation,
            ReviewStatus.EXCLUDED,
            tuple(dict.fromkeys(excluded)),
        )
    if review:
        return JobAssessment(
            observation,
            ReviewStatus.NEEDS_REVIEW,
            tuple(dict.fromkeys(review)),
        )
    return JobAssessment(observation, ReviewStatus.ELIGIBLE, ())


def _url_identity_keys(job: JobObservation | ExistingJob) -> set[tuple[str, str]]:
    keys = {
        ("url", value)
        for value in source_comparison_urls(job.source_url, job.canonical_url)
    }
    for url in job.related_urls:
        keys.add(("url", source_comparison_urls(url)[0]))
    return keys


def _posting_id_key(
    job: JobObservation | ExistingJob,
) -> tuple[str, str, str] | None:
    if not job.platform_job_id or not job.platform_job_id.strip():
        return None
    return (
        "posting_id",
        _normalize_identity_text(job.source_name),
        _normalize_identity_text(job.platform_job_id),
    )


def _posting_facts_key(
    job: JobObservation | ExistingJob,
) -> tuple[str, ...] | None:
    if job.published_on is None and job.deadline is None:
        return None
    required = (job.employer_name, job.original_title, job.location)
    if not all(value.strip() for value in required):
        return None
    return (
        "posting_facts",
        _normalize_identity_text(job.employer_name),
        _normalize_text(job.original_title),
        _normalize_identity_text(job.location),
        job.published_on.isoformat() if job.published_on else "",
        job.deadline.isoformat() if job.deadline else "",
    )


def duplicate_reason(
    first: JobObservation | ExistingJob,
    second: JobObservation | ExistingJob,
) -> DuplicateReason | None:
    """Compare actual posting identity without merging role-level similarities."""
    if _url_identity_keys(first) & _url_identity_keys(second):
        return DuplicateReason.URL
    first_id = _posting_id_key(first)
    second_id = _posting_id_key(second)
    if first_id is not None and first_id == second_id:
        return DuplicateReason.POSTING_ID
    first_facts = _posting_facts_key(first)
    second_facts = _posting_facts_key(second)
    if first_facts is not None and first_facts == second_facts:
        return DuplicateReason.POSTING_FACTS
    return None


def _observation_urls(observation: JobObservation) -> tuple[str, ...]:
    return _unique_urls(
        (
            observation.source_url,
            *((observation.canonical_url,) if observation.canonical_url else ()),
            *observation.related_urls,
        )
    )


def plan_job_discovery(
    observations: tuple[JobObservation, ...],
    existing_jobs: tuple[ExistingJob, ...],
    period: SearchPeriod,
) -> JobDiscoveryPlan:
    """Plan each posting independently and preserve duplicate source URLs."""
    planned: list[PlannedJob] = []
    excluded: list[JobAssessment] = []
    duplicates: list[DuplicateJob] = []

    for observation in observations:
        assessment = evaluate_job(observation, period)
        if assessment.status is ReviewStatus.EXCLUDED:
            excluded.append(assessment)
            continue

        existing_match: tuple[ExistingJob, DuplicateReason] | None = None
        for existing in existing_jobs:
            reason = duplicate_reason(observation, existing)
            if reason is not None:
                existing_match = (existing, reason)
                break
        if existing_match is not None:
            existing, reason = existing_match
            duplicates.append(
                DuplicateJob(
                    observation=observation,
                    reason=reason,
                    existing_page_id=existing.page_id,
                    matched_source_url=existing.source_url,
                )
            )
            continue

        planned_match_index: int | None = None
        planned_match_reason: DuplicateReason | None = None
        for index, item in enumerate(planned):
            reason = duplicate_reason(observation, item.observation)
            if reason is not None:
                planned_match_index = index
                planned_match_reason = reason
                break
        if planned_match_index is not None:
            current = planned[planned_match_index]
            combined_urls = _unique_urls(
                (
                    *current.related_urls,
                    *_observation_urls(current.observation),
                    *_observation_urls(observation),
                )
            )
            if (
                current.status is ReviewStatus.NEEDS_REVIEW
                and assessment.status is ReviewStatus.ELIGIBLE
            ):
                replacement_urls = tuple(
                    url
                    for url in combined_urls
                    if url not in _observation_urls(observation)
                )
                planned[planned_match_index] = PlannedJob(
                    observation=observation,
                    status=assessment.status,
                    reasons=assessment.reasons,
                    related_urls=replacement_urls,
                )
            else:
                related_urls = tuple(
                    url
                    for url in combined_urls
                    if url not in _observation_urls(current.observation)
                )
                planned[planned_match_index] = replace(
                    current,
                    related_urls=related_urls,
                )
            duplicates.append(
                DuplicateJob(
                    observation=observation,
                    reason=planned_match_reason or DuplicateReason.URL,
                    matched_source_url=current.observation.source_url,
                )
            )
            continue

        planned.append(
            PlannedJob(
                observation=observation,
                status=assessment.status,
                reasons=assessment.reasons,
            )
        )

    return JobDiscoveryPlan(
        eligible=tuple(
            item for item in planned if item.status is ReviewStatus.ELIGIBLE
        ),
        needs_review=tuple(
            item for item in planned if item.status is ReviewStatus.NEEDS_REVIEW
        ),
        excluded=tuple(excluded),
        duplicates=tuple(duplicates),
    )
