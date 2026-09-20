"""Deterministic boundaries for evaluating and deduplicating job postings."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from enum import Enum

from .source_urls import SourceUrlError, source_comparison_urls


SOUTH_KOREA_JOB_MARKET = "South Korea"
JOB_EVIDENCE_REVIEWER = "job_evidence_reviewer"


class JobDiscoveryError(ValueError):
    """Raised when a Job Discovery input is structurally unsafe."""


class JobDomain(str, Enum):
    AI = "AI"
    SECURITY = "Security"
    AI_SECURITY = "AI × Security"


JOB_DISCOVERY_AGENT_BY_DOMAIN = {
    JobDomain.AI: "ai_job_researcher",
    JobDomain.SECURITY: "security_job_researcher",
    JobDomain.AI_SECURITY: "ai_security_job_researcher",
}


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
    EVIDENCE_FLAGGED = "evidence_flagged"


class DuplicateReason(str, Enum):
    URL = "url"
    POSTING_ID = "posting_id"
    POSTING_FACTS = "posting_facts"


class AgentExclusionReason(str, Enum):
    ACCESS_FAILURE = "access_failure"
    OVERSEAS = "overseas"
    UNCLEAR_LOCATION = "unclear_location"
    OUTSIDE_PERIOD = "outside_period"
    UNRELATED = "unrelated"
    DUPLICATE_SEARCH_RESULT = "duplicate_search_result"
    OTHER = "other"


class JobReviewFlagType(str, Enum):
    SOURCE_ACCESS_FAILURE = "source_access_failure"
    EVIDENCE_CONFLICT = "evidence_conflict"
    CLASSIFICATION_AMBIGUITY = "classification_ambiguity"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    UNCLEAR_LOCATION = "unclear_location"


class JobReviewAssessment(str, Enum):
    CLEAR = "clear"
    FLAGGED = "flagged"


@dataclass(frozen=True)
class SearchPeriod:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise JobDiscoveryError("Search period start must not be after end.")


@dataclass(frozen=True)
class JobSearchTask:
    agent_name: str
    search_route: JobDomain
    queries: tuple[str, ...]
    period: SearchPeriod
    job_market: str = SOUTH_KOREA_JOB_MARKET


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
    review_flags: tuple[str, ...] = ()

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


@dataclass(frozen=True)
class SourceCoverage:
    source_name: str
    queries_run: int
    results_checked: int
    originals_opened: int


@dataclass(frozen=True)
class AgentJobExclusion:
    source_url: str | None
    reason: AgentExclusionReason
    summary: str


@dataclass(frozen=True)
class AgentJobDiscoveryResult:
    run_id: str
    agent_name: str
    search_route: JobDomain
    job_market: str
    search_period: SearchPeriod
    collected_on: date
    search_queries_run: tuple[str, ...]
    source_coverage: tuple[SourceCoverage, ...]
    sources_checked: tuple[str, ...]
    observations: tuple[JobObservation, ...]
    exclusions: tuple[AgentJobExclusion, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class JobReviewFlag:
    flag_type: JobReviewFlagType
    summary: str
    urls: tuple[str, ...]


@dataclass(frozen=True)
class ReviewedJob:
    source_url: str
    assessment: JobReviewAssessment
    flags: tuple[JobReviewFlag, ...]


@dataclass(frozen=True)
class JobEvidenceReviewResult:
    run_id: str
    agent_name: str
    reviewed_jobs: tuple[ReviewedJob, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class JobAgentConsolidation:
    plan: JobDiscoveryPlan
    complete_routes: tuple[JobDomain, ...]
    incomplete_routes: tuple[JobDomain, ...]
    blockers: tuple[str, ...]
    sources_checked: tuple[str, ...]
    exclusions: tuple[AgentJobExclusion, ...]


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


def build_job_search_tasks(period: SearchPeriod) -> tuple[JobSearchTask, ...]:
    """Build three independent search routes without making them allowlists."""
    queries = {
        JobDomain.AI: (
            "대한민국 AI 개발자 머신러닝 엔지니어 채용",
            "대한민국 LLM RAG AI agent 채용",
            "site:saramin.co.kr AI 엔지니어",
            "site:jobkorea.co.kr 머신러닝 채용",
            "site:wanted.co.kr AI 개발자",
            "site:jumpit.co.kr AI 엔지니어",
        ),
        JobDomain.SECURITY: (
            "대한민국 정보보안 보안 엔지니어 채용",
            "대한민국 클라우드 보안 IAM 취약점 분석 채용",
            "site:saramin.co.kr 보안 엔지니어",
            "site:jobkorea.co.kr 정보보안 채용",
            "site:wanted.co.kr Security Engineer Korea",
            "site:jumpit.co.kr 보안 채용",
        ),
        JobDomain.AI_SECURITY: (
            "대한민국 AI 보안 LLM 보안 채용",
            "대한민국 AI safety model security 채용",
            "대한민국 AI 거버넌스 위험 평가 채용",
            "site:saramin.co.kr AI 보안",
            "site:jobkorea.co.kr AI 보안",
            "site:wanted.co.kr AI Security Korea",
        ),
    }
    return tuple(
        JobSearchTask(
            agent_name=JOB_DISCOVERY_AGENT_BY_DOMAIN[domain],
            search_route=domain,
            queries=queries[domain],
            period=period,
        )
        for domain in JobDomain
    )


def _object(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise JobDiscoveryError(f"{field} must be an object.")
    return value


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise JobDiscoveryError(f"{field} must be a list.")
    return value


def _text(value: object, field: str, *, allow_blank: bool = False) -> str:
    if not isinstance(value, str) or (not allow_blank and not value.strip()):
        raise JobDiscoveryError(f"{field} must be a non-blank string.")
    return value


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise JobDiscoveryError(f"{field} must be a non-negative integer.")
    return value


def _date(value: object, field: str, *, optional: bool = False) -> date | None:
    if value is None and optional:
        return None
    text = _text(value, field)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise JobDiscoveryError(f"{field} must be an ISO date.") from error


def _enum(enum_type: type[Enum], value: object, field: str):
    try:
        return enum_type(_text(value, field))
    except ValueError as error:
        raise JobDiscoveryError(f"{field} has an unsupported value: {value!r}.") from error


def _text_tuple(value: object, field: str) -> tuple[str, ...]:
    return tuple(_text(item, field) for item in _list(value, field))


def _parse_observation(value: object, route: JobDomain) -> JobObservation:
    item = _object(value, "observations[]")
    search_routes = tuple(
        _enum(JobDomain, part, "search_routes[]")
        for part in _list(item.get("search_routes"), "search_routes")
    )
    if route not in search_routes:
        raise JobDiscoveryError("Observation search_routes must include its agent route.")
    return JobObservation(
        source_name=_text(item.get("source_name"), "source_name"),
        source_type=_enum(JobSourceType, item.get("source_type"), "source_type"),
        source_url=_text(item.get("source_url"), "source_url"),
        employer_name=_text(item.get("employer_name"), "employer_name", allow_blank=True),
        original_title=_text(item.get("original_title"), "original_title", allow_blank=True),
        recognized_role=_text(item.get("recognized_role"), "recognized_role", allow_blank=True),
        domain=_enum(JobDomain, item.get("domain"), "domain"),
        classification_basis=_text(item.get("classification_basis"), "classification_basis", allow_blank=True),
        responsibilities=_text_tuple(item.get("responsibilities"), "responsibilities"),
        requirements=_text_tuple(item.get("requirements"), "requirements"),
        technology_keywords=_text_tuple(item.get("technology_keywords"), "technology_keywords"),
        location=_text(item.get("location"), "location", allow_blank=True),
        job_market=_text(item.get("job_market"), "job_market"),
        experience_level=_enum(ExperienceLevel, item.get("experience_level"), "experience_level"),
        employment_type=_enum(EmploymentType, item.get("employment_type"), "employment_type"),
        work_mode=_enum(WorkMode, item.get("work_mode"), "work_mode"),
        published_on=_date(item.get("published_on"), "published_on", optional=True),
        deadline=_date(item.get("deadline"), "deadline", optional=True),
        posting_status=_enum(PostingStatus, item.get("posting_status"), "posting_status"),
        collected_on=_date(item.get("collected_on"), "collected_on"),
        search_routes=search_routes,
        canonical_url=_optional_text(item.get("canonical_url"), "canonical_url"),
        platform_job_id=_optional_text(item.get("platform_job_id"), "platform_job_id"),
        related_urls=_text_tuple(item.get("related_urls", []), "related_urls"),
    )


def parse_job_agent_result(payload: str) -> AgentJobDiscoveryResult:
    """Parse one search Agent JSON result at the deterministic boundary."""
    try:
        root = _object(json.loads(payload), "payload")
    except json.JSONDecodeError as error:
        raise JobDiscoveryError("Agent result must be one JSON object.") from error
    period_data = _object(root.get("search_period"), "search_period")
    period = SearchPeriod(
        _date(period_data.get("start"), "search_period.start"),
        _date(period_data.get("end"), "search_period.end"),
    )
    route = _enum(JobDomain, root.get("search_route"), "search_route")
    coverage = tuple(
        SourceCoverage(
            source_name=_text(item.get("source_name"), "source_coverage.source_name"),
            queries_run=_integer(item.get("queries_run"), "source_coverage.queries_run"),
            results_checked=_integer(item.get("results_checked"), "source_coverage.results_checked"),
            originals_opened=_integer(item.get("originals_opened"), "source_coverage.originals_opened"),
        )
        for value in _list(root.get("source_coverage"), "source_coverage")
        for item in (_object(value, "source_coverage[]"),)
    )
    exclusions = tuple(
        AgentJobExclusion(
            source_url=_optional_text(item.get("source_url"), "exclusions.source_url"),
            reason=_enum(AgentExclusionReason, item.get("reason"), "exclusions.reason"),
            summary=_text(item.get("summary"), "exclusions.summary"),
        )
        for value in _list(root.get("exclusions"), "exclusions")
        for item in (_object(value, "exclusions[]"),)
    )
    return AgentJobDiscoveryResult(
        run_id=_text(root.get("run_id"), "run_id"),
        agent_name=_text(root.get("agent_name"), "agent_name"),
        search_route=route,
        job_market=_text(root.get("job_market"), "job_market"),
        search_period=period,
        collected_on=_date(root.get("collected_on"), "collected_on"),
        search_queries_run=_text_tuple(root.get("search_queries_run"), "search_queries_run"),
        source_coverage=coverage,
        sources_checked=_text_tuple(root.get("sources_checked"), "sources_checked"),
        observations=tuple(
            _parse_observation(value, route)
            for value in _list(root.get("observations"), "observations")
        ),
        exclusions=exclusions,
        blockers=_text_tuple(root.get("blockers"), "blockers"),
    )


def parse_job_evidence_review(payload: str) -> JobEvidenceReviewResult:
    """Parse the sequential evidence review without making final decisions."""
    try:
        root = _object(json.loads(payload), "payload")
    except json.JSONDecodeError as error:
        raise JobDiscoveryError("Reviewer result must be one JSON object.") from error
    reviewed: list[ReviewedJob] = []
    seen_urls: set[str] = set()
    for value in _list(root.get("reviewed_jobs"), "reviewed_jobs"):
        item = _object(value, "reviewed_jobs[]")
        source_url = _text(item.get("source_url"), "reviewed_jobs.source_url")
        if source_url in seen_urls:
            raise JobDiscoveryError("Reviewer must cover each source URL once.")
        seen_urls.add(source_url)
        flags = tuple(
            JobReviewFlag(
                flag_type=_enum(JobReviewFlagType, flag.get("type"), "flags.type"),
                summary=_text(flag.get("summary"), "flags.summary"),
                urls=_text_tuple(flag.get("urls"), "flags.urls"),
            )
            for raw_flag in _list(item.get("flags"), "flags")
            for flag in (_object(raw_flag, "flags[]"),)
        )
        assessment = _enum(JobReviewAssessment, item.get("assessment"), "assessment")
        if assessment is JobReviewAssessment.CLEAR and flags:
            raise JobDiscoveryError("A clear review must not contain flags.")
        if assessment is JobReviewAssessment.FLAGGED and not flags:
            raise JobDiscoveryError("A flagged review must contain at least one flag.")
        reviewed.append(ReviewedJob(source_url, assessment, flags))
    return JobEvidenceReviewResult(
        run_id=_text(root.get("run_id"), "run_id"),
        agent_name=_text(root.get("agent_name"), "agent_name"),
        reviewed_jobs=tuple(reviewed),
        blockers=_text_tuple(root.get("blockers"), "blockers"),
    )


def apply_job_evidence_review(
    observations: tuple[JobObservation, ...],
    review: JobEvidenceReviewResult | None,
) -> tuple[JobObservation, ...]:
    """Apply reviewer flags per posting; missing review never drops observations."""
    observation_urls = {item.source_url for item in observations}
    if review is None:
        return tuple(
            replace(item, review_flags=(*item.review_flags, "review_not_run"))
            for item in observations
        )
    if review.agent_name != JOB_EVIDENCE_REVIEWER:
        raise JobDiscoveryError("Unexpected Job evidence reviewer name.")
    reviewed_by_url = {item.source_url: item for item in review.reviewed_jobs}
    extra = set(reviewed_by_url) - observation_urls
    if extra:
        raise JobDiscoveryError("Reviewer returned URLs not present in Agent observations.")
    output: list[JobObservation] = []
    for item in observations:
        reviewed = reviewed_by_url.get(item.source_url)
        flags = list(item.review_flags)
        if review.blockers:
            flags.append("reviewer_blocked")
        if reviewed is None:
            flags.append("review_missing")
        elif reviewed.assessment is JobReviewAssessment.FLAGGED:
            flags.extend(
                f"{flag.flag_type.value}: {flag.summary}" for flag in reviewed.flags
            )
        output.append(replace(item, review_flags=tuple(dict.fromkeys(flags))))
    return tuple(output)


def consolidate_job_agent_results(
    results: tuple[AgentJobDiscoveryResult, ...],
    run_id: str,
    existing_jobs: tuple[ExistingJob, ...],
    period: SearchPeriod,
    review: JobEvidenceReviewResult | None,
) -> JobAgentConsolidation:
    """Consolidate partial Agent results while preserving valid postings."""
    by_route: dict[JobDomain, AgentJobDiscoveryResult] = {}
    blockers: list[str] = []
    observations: list[JobObservation] = []
    sources: list[str] = []
    exclusions: list[AgentJobExclusion] = []
    for result in results:
        if result.search_route in by_route:
            raise JobDiscoveryError("Each search route may return at most one result.")
        if result.run_id != run_id:
            raise JobDiscoveryError("Agent run_id does not match the parent run.")
        if result.search_period != period:
            raise JobDiscoveryError("Agent search period does not match the parent period.")
        if result.job_market != SOUTH_KOREA_JOB_MARKET:
            raise JobDiscoveryError("Agent job market must be South Korea.")
        if result.agent_name != JOB_DISCOVERY_AGENT_BY_DOMAIN[result.search_route]:
            raise JobDiscoveryError("Agent name does not match its assigned search route.")
        by_route[result.search_route] = result
        observations.extend(result.observations)
        sources.extend(result.sources_checked)
        exclusions.extend(result.exclusions)
        blockers.extend(f"{result.search_route.value}: {item}" for item in result.blockers)
    if review is not None and review.run_id != run_id:
        raise JobDiscoveryError("Reviewer run_id does not match the parent run.")
    reviewed = apply_job_evidence_review(tuple(observations), review)
    complete = tuple(
        route for route in JobDomain if route in by_route and not by_route[route].blockers
    )
    incomplete = tuple(route for route in JobDomain if route not in complete)
    if review is None:
        blockers.append("Job evidence review was not completed.")
    elif review.blockers:
        blockers.extend(f"Reviewer: {item}" for item in review.blockers)
    return JobAgentConsolidation(
        plan=plan_job_discovery(reviewed, existing_jobs, period),
        complete_routes=complete,
        incomplete_routes=incomplete,
        blockers=tuple(blockers),
        sources_checked=tuple(dict.fromkeys(sources)),
        exclusions=tuple(exclusions),
    )


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
    if observation.review_flags:
        review.append(ReviewReason.EVIDENCE_FLAGGED)

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
