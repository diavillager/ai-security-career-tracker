"""Deterministic boundaries for planning and consolidating Role Discovery."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from urllib.parse import urlsplit

from .source_urls import SourceUrlError, source_comparison_url


class DiscoveryValidationError(ValueError):
    """Raised when a proposed role lacks safe, consistent evidence."""


class Category(StrEnum):
    AI = "AI"
    SECURITY = "Security"
    AI_SECURITY = "AI × Security"


class RoleStatus(StrEnum):
    CANDIDATE = "Candidate"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class ExperienceLevel(StrEnum):
    ENTRY = "신입"
    EXPERIENCED = "경력"
    BOTH = "신입·경력"
    UNKNOWN = "미확인"


class EvidenceType(StrEnum):
    JOB_POSTING = "Job Posting"
    INFORMATIONAL = "Informational"


class ExclusionReason(StrEnum):
    OVERSEAS = "overseas"
    UNCLEAR_LOCATION = "unclear_location"
    MISSING_PUBLISHED_DATE = "missing_published_date"
    OUTSIDE_PERIOD = "outside_period"
    DOMAIN_MISMATCH = "domain_mismatch"
    OTHER = "other"


class ReviewAssessment(StrEnum):
    CLEAR = "clear"
    FLAGGED = "flagged"


class ReviewFlagType(StrEnum):
    SOURCE_ACCESS_FAILURE = "source_access_failure"
    SOURCE_INDEPENDENCE = "source_independence"
    EVIDENCE_CONFLICT = "evidence_conflict"
    CATEGORY_AMBIGUITY = "category_ambiguity"
    SEMANTIC_DUPLICATE = "semantic_duplicate"
    UNSUPPORTED_CLAIM = "unsupported_claim"


SOUTH_KOREA_JOB_MARKET = "South Korea"
ROLE_EVIDENCE_REVIEWER = "role_evidence_reviewer"
PREFERRED_JOB_SOURCES = (
    "Employer career pages",
    "Saramin",
    "JobKorea",
    "Wanted",
    "Jumpit",
)
SOUTH_KOREA_SEARCH_TERMS = (
    '"South Korea"',
    '"Republic of Korea"',
    "Korea",
    "한국",
    "대한민국",
    "서울",
    "판교",
)


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise DiscoveryValidationError("The start date must not follow the end date.")


@dataclass(frozen=True)
class SearchQuery:
    category: Category
    query: str
    period: DateRange
    job_market: str = SOUTH_KOREA_JOB_MARKET
    preferred_sources: tuple[str, ...] = PREFERRED_JOB_SOURCES


@dataclass(frozen=True)
class AgentSearchTask:
    agent_name: str
    search_query: SearchQuery


@dataclass(frozen=True)
class EvidenceSource:
    name: str
    url: str
    published_on: date
    source_type: EvidenceType = EvidenceType.INFORMATIONAL
    employer_name: str | None = None
    job_title: str | None = None
    job_location: str | None = None
    job_market: str | None = None
    canonical_url: str | None = None

    def __post_init__(self) -> None:
        parsed = urlsplit(self.url)
        if (
            not self.name.strip()
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or not isinstance(self.published_on, date)
        ):
            raise DiscoveryValidationError(
                "Every evidence source needs a name, an original HTTP or HTTPS URL, "
                "and a verified published date."
            )
        try:
            source_comparison_url(self.url, self.canonical_url)
        except SourceUrlError as error:
            raise DiscoveryValidationError(str(error)) from error
        if self.source_type is EvidenceType.JOB_POSTING:
            if not self.employer_name or not self.employer_name.strip():
                raise DiscoveryValidationError(
                    "Every job posting needs a verified employer name."
                )
            if not self.job_title or not self.job_title.strip():
                raise DiscoveryValidationError(
                    "Every job posting needs the exact title from the source."
                )
            if not self.job_location or not self.job_location.strip():
                raise DiscoveryValidationError(
                    "Every job posting needs an explicitly verified job location."
                )
            if self.job_market != SOUTH_KOREA_JOB_MARKET:
                raise DiscoveryValidationError(
                    "Role Discovery only accepts job postings for the South Korea job market."
                )


@dataclass(frozen=True)
class ExistingRole:
    role_name: str
    status: RoleStatus


@dataclass(frozen=True)
class RoleObservation:
    role_name: str
    suggested_category: Category
    description: str
    key_responsibilities: tuple[str, ...]
    required_skills: tuple[str, ...]
    team_description: str
    product_context: str
    discovery_reason: str
    experience_level: ExperienceLevel
    evidence_sources: tuple[EvidenceSource, ...]

    def __post_init__(self) -> None:
        required_text = (
            self.role_name,
            self.description,
            self.team_description,
            self.product_context,
            self.discovery_reason,
        )
        if not all(value.strip() for value in required_text):
            raise DiscoveryValidationError(
                "Role name, description, team, product context, and discovery reason "
                "are required."
            )
        if not any(value.strip() for value in self.key_responsibilities):
            raise DiscoveryValidationError("At least one responsibility is required.")
        if not any(value.strip() for value in self.required_skills):
            raise DiscoveryValidationError("At least one required skill is required.")
        if not self.evidence_sources:
            raise DiscoveryValidationError("At least one evidence source is required.")
        mismatched_titles = tuple(
            source.job_title
            for source in self.evidence_sources
            if source.source_type is EvidenceType.JOB_POSTING
            and normalize_role_name(source.job_title or "")
            != normalize_role_name(self.role_name)
        )
        if mismatched_titles:
            raise DiscoveryValidationError(
                "Every job posting title must match the observation role name "
                "without semantic merging. Mismatched titles: "
                + ", ".join(mismatched_titles)
            )


@dataclass(frozen=True)
class CandidateRole:
    role_name: str
    category: Category
    experience_level: ExperienceLevel
    description: str
    key_responsibilities: tuple[str, ...]
    discovery_reasons: tuple[str, ...]
    evidence_sources: tuple[EvidenceSource, ...]
    job_locations: tuple[str, ...]
    job_market: str
    first_discovered: date
    last_reviewed: date
    status: RoleStatus = RoleStatus.CANDIDATE


@dataclass(frozen=True)
class ExistingRoleMatch:
    observed_role_name: str
    existing_role_name: str
    existing_status: RoleStatus


@dataclass(frozen=True)
class AgentExclusion:
    url: str
    reason: ExclusionReason

    def __post_init__(self) -> None:
        parsed = urlsplit(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise DiscoveryValidationError(
                "Every agent exclusion needs an original HTTP or HTTPS URL."
            )


@dataclass(frozen=True)
class AgentDiscoveryResult:
    run_id: str
    agent_name: str
    category: Category
    search_period: DateRange
    job_market: str
    sources_checked: int
    observations: tuple[RoleObservation, ...]
    exclusions: tuple[AgentExclusion, ...] = ()
    existing_matches: tuple[ExistingRoleMatch, ...] = ()
    blockers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.agent_name.strip():
            raise DiscoveryValidationError(
                "Every agent result needs a run ID and an agent name."
            )
        if self.job_market != SOUTH_KOREA_JOB_MARKET:
            raise DiscoveryValidationError(
                "Every agent result must use the South Korea job market."
            )
        if self.sources_checked < 0:
            raise DiscoveryValidationError(
                "Agent source count must not be negative."
            )


@dataclass(frozen=True)
class EvidenceReviewFlag:
    flag_type: ReviewFlagType
    summary: str
    urls: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise DiscoveryValidationError("Every review flag needs a summary.")
        if not self.urls:
            raise DiscoveryValidationError("Every review flag needs at least one URL.")
        for url in self.urls:
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise DiscoveryValidationError(
                    "Every review flag URL must use HTTP or HTTPS."
                )


@dataclass(frozen=True)
class ReviewedRole:
    role_name: str
    assessment: ReviewAssessment
    flags: tuple[EvidenceReviewFlag, ...]

    def __post_init__(self) -> None:
        if not self.role_name.strip():
            raise DiscoveryValidationError("Reviewed role name must not be blank.")
        if self.assessment is ReviewAssessment.CLEAR and self.flags:
            raise DiscoveryValidationError("A clear review must not contain flags.")
        if self.assessment is ReviewAssessment.FLAGGED and not self.flags:
            raise DiscoveryValidationError("A flagged review needs at least one flag.")


@dataclass(frozen=True)
class RoleEvidenceReviewResult:
    run_id: str
    agent_name: str
    reviewed_roles: tuple[ReviewedRole, ...]
    blockers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.agent_name.strip():
            raise DiscoveryValidationError(
                "Every evidence review needs a run ID and an agent name."
            )


@dataclass(frozen=True)
class DiscoveryOutcome:
    new_candidates: tuple[CandidateRole, ...]
    existing_matches: tuple[ExistingRoleMatch, ...]
    sources_checked: int = 0
    exclusions: tuple[AgentExclusion, ...] = ()


SEEDS: dict[Category, tuple[str, ...]] = {
    Category.AI: (
        "Applied AI Engineer",
        "AI Agent Engineer",
        "Agent Engineer",
        "LLM Engineer",
        "Generative AI Engineer",
        "AI Platform Engineer",
        "Agent Platform Engineer",
        "Agent Infrastructure Engineer",
        "AI Evaluation Engineer",
    ),
    Category.SECURITY: (
        "Product Security Engineer",
        "Application Security Engineer",
        "Cloud Security Engineer",
        "Security Platform Engineer",
        "IAM Engineer",
        "Security Engineer",
    ),
    Category.AI_SECURITY: (
        "AI Security Engineer",
        "Agent Security Engineer",
        "GenAI Security Engineer",
        "LLM Security Engineer",
        "AI Product Security",
        "AI Platform Security",
    ),
}

RESPONSIBILITY_TERMS: dict[Category, tuple[str, ...]] = {
    Category.AI: (
        "agent",
        "tool use",
        "RAG",
        "evaluation",
        "model serving",
        "orchestration",
        "observability",
    ),
    Category.SECURITY: (
        "IAM",
        "authorization",
        "OAuth",
        "OIDC",
        "threat modeling",
        "policy enforcement",
        "data governance",
        "Zero Trust",
    ),
    Category.AI_SECURITY: (
        "agent security",
        "prompt injection",
        "sandbox",
        "workload identity",
        "policy enforcement",
        "audit logging",
        "data governance",
    ),
}

ROLE_DISCOVERY_AGENT_BY_CATEGORY: dict[Category, str] = {
    Category.AI: "ai_role_researcher",
    Category.SECURITY: "security_role_researcher",
    Category.AI_SECURITY: "ai_security_role_researcher",
}


def default_period(as_of: date, days: int = 7) -> DateRange:
    """Return an inclusive calendar range ending on ``as_of``."""
    if days < 1:
        raise DiscoveryValidationError("Search days must be at least one.")
    return DateRange(start=as_of - timedelta(days=days - 1), end=as_of)


def build_search_plan(period: DateRange) -> tuple[SearchQuery, ...]:
    """Build domain queries with preferred sources, without creating an allowlist."""
    queries: list[SearchQuery] = []
    locations = " OR ".join(SOUTH_KOREA_SEARCH_TERMS)
    for category in Category:
        roles = " OR ".join(f'"{role}"' for role in SEEDS[category])
        responsibilities = " OR ".join(
            f'"{term}"' for term in RESPONSIBILITY_TERMS[category]
        )
        query = (
            f"({roles}) ({responsibilities}) "
            f"(job OR jobs OR careers OR hiring OR recruit OR 채용 OR 구인) "
            f"({locations})"
        )
        queries.append(
            SearchQuery(
                category=category,
                query=query,
                period=period,
                job_market=SOUTH_KOREA_JOB_MARKET,
            )
        )
    return tuple(queries)


def build_agent_search_tasks(period: DateRange) -> tuple[AgentSearchTask, ...]:
    """Assign each deterministic domain query to its dedicated research agent."""
    return tuple(
        AgentSearchTask(
            agent_name=ROLE_DISCOVERY_AGENT_BY_CATEGORY[query.category],
            search_query=query,
        )
        for query in build_search_plan(period)
    )


def normalize_role_name(role_name: str) -> str:
    """Normalize spelling form, case, and whitespace without semantic matching."""
    normalized = unicodedata.normalize("NFKC", role_name)
    return " ".join(normalized.casefold().split())


def _unique_text(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return tuple(result)


def _merge_experience_levels(
    levels: set[ExperienceLevel],
) -> ExperienceLevel:
    """Combine explicit levels while treating unknown as missing evidence."""
    stated = levels - {ExperienceLevel.UNKNOWN}
    if not stated:
        return ExperienceLevel.UNKNOWN
    if ExperienceLevel.BOTH in stated or stated == {
        ExperienceLevel.ENTRY,
        ExperienceLevel.EXPERIENCED,
    }:
        return ExperienceLevel.BOTH
    return next(iter(stated))


def _normalize_employer_name(value: str) -> str:
    """Normalize common legal-name variations without semantic matching."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"\(\s*주\s*\)|주식회사", "", normalized)
    normalized = re.sub(
        r"\b(?:incorporated|inc|corporation|corp|company|co|limited|ltd)\b\.?,?",
        "",
        normalized,
    )
    return re.sub(r"[^0-9a-z가-힣]+", "", normalized)


def _independent_evidence_key(
    role_name: str,
    source: EvidenceSource,
) -> tuple[str, ...]:
    """Group mirrors of the same vacancy while keeping other sources URL-based."""
    if source.source_type is EvidenceType.JOB_POSTING:
        return (
            "job_posting",
            _normalize_employer_name(source.employer_name or ""),
            normalize_role_name(source.job_title or role_name),
        )
    return (
        "informational",
        source_comparison_url(source.url, source.canonical_url),
    )


def group_independent_evidence(
    role_name: str,
    evidence_sources: tuple[EvidenceSource, ...],
) -> tuple[tuple[EvidenceSource, ...], ...]:
    """Keep every URL while grouping mirrors for independent-evidence counts."""
    grouped: dict[tuple[str, ...], list[EvidenceSource]] = {}
    for source in evidence_sources:
        grouped.setdefault(
            _independent_evidence_key(role_name, source),
            [],
        ).append(source)
    return tuple(tuple(sources) for sources in grouped.values())


def format_candidate_evidence_sources(candidate: CandidateRole) -> str:
    """Format every retained URL with a visible independent-evidence group."""
    lines: list[str] = []
    for index, sources in enumerate(
        group_independent_evidence(candidate.role_name, candidate.evidence_sources),
        start=1,
    ):
        label = f"독립 근거 {index}"
        if len(sources) > 1:
            if all(
                source.source_type is EvidenceType.JOB_POSTING for source in sources
            ):
                label += " · 동일 공고"
            else:
                label += " · 동일 원문"
        for source in sources:
            canonical = (
                f" · Canonical: {source.canonical_url}"
                if source.canonical_url and source.canonical_url != source.url
                else ""
            )
            lines.append(f"[{label}] {source.name} — {source.url}{canonical}")
    return "\n".join(lines)


def format_candidate_evidence_note(candidate: CandidateRole) -> str:
    """Summarize independent groups and retained URLs for the Notion Notes field."""
    groups = group_independent_evidence(
        candidate.role_name,
        candidate.evidence_sources,
    )
    lines = [
        f"독립 근거: {len(groups)}개 / 보존 URL: {len(candidate.evidence_sources)}개"
    ]
    mirrored_job_groups = [
        f"독립 근거 {index} ({', '.join(source.name for source in sources)})"
        for index, sources in enumerate(groups, start=1)
        if len(sources) > 1
        and all(source.source_type is EvidenceType.JOB_POSTING for source in sources)
    ]
    mirrored_source_groups = [
        f"독립 근거 {index} ({', '.join(source.name for source in sources)})"
        for index, sources in enumerate(groups, start=1)
        if len(sources) > 1
        and not all(source.source_type is EvidenceType.JOB_POSTING for source in sources)
    ]
    if mirrored_job_groups:
        lines.append(f"동일 공고 그룹: {'; '.join(mirrored_job_groups)}")
    if mirrored_source_groups:
        lines.append(f"동일 원문 그룹: {'; '.join(mirrored_source_groups)}")
    return "\n".join(lines)


def select_new_candidates(
    observations: tuple[RoleObservation, ...],
    existing_roles: tuple[ExistingRole, ...],
    discovered_on: date,
    search_period: DateRange,
) -> DiscoveryOutcome:
    """Exclude every existing status and merge same-run evidence for new roles."""
    existing_by_name = {
        normalize_role_name(role.role_name): role for role in existing_roles
    }
    grouped: dict[str, list[RoleObservation]] = {}
    existing_matches: list[ExistingRoleMatch] = []

    for observation in observations:
        if any(
            source.published_on < search_period.start
            or source.published_on > search_period.end
            for source in observation.evidence_sources
        ):
            raise DiscoveryValidationError(
                f"Every evidence source must be published within the search period: "
                f"{observation.role_name}"
            )
        normalized_name = normalize_role_name(observation.role_name)
        if not normalized_name:
            raise DiscoveryValidationError("Role name must not be blank.")
        existing = existing_by_name.get(normalized_name)
        if existing is not None:
            existing_matches.append(
                ExistingRoleMatch(
                    observed_role_name=observation.role_name,
                    existing_role_name=existing.role_name,
                    existing_status=existing.status,
                )
            )
            continue
        grouped.setdefault(normalized_name, []).append(observation)

    candidates: list[CandidateRole] = []
    for group in grouped.values():
        categories = {item.suggested_category for item in group}
        if len(categories) != 1:
            raise DiscoveryValidationError(
                f"Conflicting categories require review for role: {group[0].role_name}"
            )

        evidence_by_url: dict[str, EvidenceSource] = {}
        for item in group:
            for source in item.evidence_sources:
                evidence_by_url.setdefault(source.url, source)

        evidence_groups = group_independent_evidence(
            group[0].role_name,
            tuple(evidence_by_url.values()),
        )
        if len(evidence_groups) < 2:
            raise DiscoveryValidationError(
                f"At least two independent evidence sources are required for role: "
                f"{group[0].role_name}"
            )

        korean_job_postings = tuple(
            source
            for source in evidence_by_url.values()
            if source.source_type is EvidenceType.JOB_POSTING
            and source.job_market == SOUTH_KOREA_JOB_MARKET
        )
        if not korean_job_postings:
            raise DiscoveryValidationError(
                f"At least one South Korea job posting is required for role: "
                f"{group[0].role_name}"
            )

        candidates.append(
            CandidateRole(
                role_name=group[0].role_name.strip(),
                category=next(iter(categories)),
                experience_level=_merge_experience_levels(
                    {item.experience_level for item in group}
                ),
                description=group[0].description.strip(),
                key_responsibilities=_unique_text(
                    [value for item in group for value in item.key_responsibilities]
                ),
                discovery_reasons=_unique_text(
                    [item.discovery_reason for item in group]
                ),
                evidence_sources=tuple(evidence_by_url.values()),
                job_locations=_unique_text(
                    [source.job_location or "" for source in korean_job_postings]
                ),
                job_market=SOUTH_KOREA_JOB_MARKET,
                first_discovered=discovered_on,
                last_reviewed=discovered_on,
            )
        )

    return DiscoveryOutcome(
        new_candidates=tuple(candidates),
        existing_matches=tuple(existing_matches),
    )


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DiscoveryValidationError(f"{field} must be an object.")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DiscoveryValidationError(f"{field} must be a non-empty string.")
    return value.strip()


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise DiscoveryValidationError(f"{field} must be a list.")
    return value


def _date(value: object, field: str) -> date:
    try:
        return date.fromisoformat(_string(value, field))
    except ValueError as exc:
        raise DiscoveryValidationError(
            f"{field} must be an ISO date in YYYY-MM-DD format."
        ) from exc


def parse_agent_discovery_result(
    payload: Mapping[str, object] | str,
) -> AgentDiscoveryResult:
    """Parse a subagent's structured output into deterministic domain objects."""
    try:
        if isinstance(payload, str):
            decoded = json.loads(payload)
            payload = _mapping(decoded, "agent result")
        period_data = _mapping(payload.get("search_period"), "search_period")
        observations: list[RoleObservation] = []
        for index, raw_observation in enumerate(
            _list(payload.get("observations"), "observations")
        ):
            item = _mapping(raw_observation, f"observations[{index}]")
            evidence: list[EvidenceSource] = []
            for source_index, raw_source in enumerate(
                _list(item.get("evidence_sources"), "evidence_sources")
            ):
                source = _mapping(
                    raw_source,
                    f"observations[{index}].evidence_sources[{source_index}]",
                )
                source_type = EvidenceType(
                    _string(source.get("source_type"), "source_type")
                )
                evidence.append(
                    EvidenceSource(
                        name=_string(source.get("name"), "source name"),
                        url=_string(source.get("url"), "source URL"),
                        published_on=_date(
                            source.get("published_on"), "published_on"
                        ),
                        source_type=source_type,
                        employer_name=(
                            _string(source.get("employer_name"), "employer_name")
                            if source.get("employer_name") is not None
                            else None
                        ),
                        job_title=(
                            _string(source.get("job_title"), "job_title")
                            if source.get("job_title") is not None
                            else None
                        ),
                        job_location=(
                            _string(source.get("job_location"), "job_location")
                            if source.get("job_location") is not None
                            else None
                        ),
                        job_market=(
                            _string(source.get("job_market"), "source job_market")
                            if source.get("job_market") is not None
                            else None
                        ),
                        canonical_url=(
                            _string(source.get("canonical_url"), "canonical_url")
                            if source.get("canonical_url") is not None
                            else None
                        ),
                    )
                )
            observations.append(
                RoleObservation(
                    role_name=_string(item.get("role_name"), "role_name"),
                    suggested_category=Category(
                        _string(item.get("suggested_category"), "suggested_category")
                    ),
                    description=_string(item.get("description"), "description"),
                    key_responsibilities=tuple(
                        _string(value, "key_responsibilities item")
                        for value in _list(
                            item.get("key_responsibilities"),
                            "key_responsibilities",
                        )
                    ),
                    required_skills=tuple(
                        _string(value, "required_skills item")
                        for value in _list(
                            item.get("required_skills"), "required_skills"
                        )
                    ),
                    team_description=_string(
                        item.get("team_description"), "team_description"
                    ),
                    product_context=_string(
                        item.get("product_context"), "product_context"
                    ),
                    discovery_reason=_string(
                        item.get("discovery_reason"), "discovery_reason"
                    ),
                    experience_level=ExperienceLevel(
                        _string(item.get("experience_level"), "experience_level")
                    ),
                    evidence_sources=tuple(evidence),
                )
            )

        exclusions = tuple(
            AgentExclusion(
                url=_string(
                    _mapping(item, "exclusion").get("url"), "exclusion URL"
                ),
                reason=ExclusionReason(
                    _string(
                        _mapping(item, "exclusion").get("reason"),
                        "exclusion reason",
                    )
                ),
            )
            for item in _list(payload.get("exclusions"), "exclusions")
        )
        existing_matches = tuple(
            ExistingRoleMatch(
                observed_role_name=_string(
                    _mapping(item, "existing match").get("observed_role_name"),
                    "observed_role_name",
                ),
                existing_role_name=_string(
                    _mapping(item, "existing match").get("existing_role_name"),
                    "existing_role_name",
                ),
                existing_status=RoleStatus(
                    _string(
                        _mapping(item, "existing match").get("existing_status"),
                        "existing_status",
                    )
                ),
            )
            for item in _list(payload.get("existing_matches"), "existing_matches")
        )
        sources_checked = payload.get("sources_checked")
        if isinstance(sources_checked, bool) or not isinstance(sources_checked, int):
            raise DiscoveryValidationError("sources_checked must be an integer.")

        return AgentDiscoveryResult(
            run_id=_string(payload.get("run_id"), "run_id"),
            agent_name=_string(payload.get("agent_name"), "agent_name"),
            category=Category(_string(payload.get("category"), "category")),
            search_period=DateRange(
                start=_date(period_data.get("start"), "search_period.start"),
                end=_date(period_data.get("end"), "search_period.end"),
            ),
            job_market=_string(payload.get("job_market"), "job_market"),
            sources_checked=sources_checked,
            observations=tuple(observations),
            exclusions=exclusions,
            existing_matches=existing_matches,
            blockers=tuple(
                _string(value, "blockers item")
                for value in _list(payload.get("blockers"), "blockers")
            ),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, DiscoveryValidationError):
            raise
        raise DiscoveryValidationError(
            f"Invalid agent discovery result: {exc}"
        ) from exc


def parse_role_evidence_review_result(
    payload: Mapping[str, object] | str,
) -> RoleEvidenceReviewResult:
    """Parse the semantic reviewer's JSON response into validated objects."""
    try:
        if isinstance(payload, str):
            decoded = json.loads(payload)
            payload = _mapping(decoded, "evidence review result")

        reviewed_roles: list[ReviewedRole] = []
        for role_index, raw_role in enumerate(
            _list(payload.get("reviewed_roles"), "reviewed_roles")
        ):
            role = _mapping(raw_role, f"reviewed_roles[{role_index}]")
            flags: list[EvidenceReviewFlag] = []
            for flag_index, raw_flag in enumerate(
                _list(role.get("flags"), "flags")
            ):
                flag = _mapping(
                    raw_flag,
                    f"reviewed_roles[{role_index}].flags[{flag_index}]",
                )
                flags.append(
                    EvidenceReviewFlag(
                        flag_type=ReviewFlagType(
                            _string(flag.get("type"), "review flag type")
                        ),
                        summary=_string(
                            flag.get("summary"), "review flag summary"
                        ),
                        urls=tuple(
                            _string(url, "review flag URL")
                            for url in _list(flag.get("urls"), "review flag URLs")
                        ),
                    )
                )
            reviewed_roles.append(
                ReviewedRole(
                    role_name=_string(role.get("role_name"), "reviewed role name"),
                    assessment=ReviewAssessment(
                        _string(role.get("assessment"), "review assessment")
                    ),
                    flags=tuple(flags),
                )
            )

        return RoleEvidenceReviewResult(
            run_id=_string(payload.get("run_id"), "run_id"),
            agent_name=_string(payload.get("agent_name"), "agent_name"),
            reviewed_roles=tuple(reviewed_roles),
            blockers=tuple(
                _string(value, "blockers item")
                for value in _list(payload.get("blockers"), "blockers")
            ),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, DiscoveryValidationError):
            raise
        raise DiscoveryValidationError(
            f"Invalid role evidence review result: {exc}"
        ) from exc


def validate_role_evidence_review(
    review: RoleEvidenceReviewResult,
    results: tuple[AgentDiscoveryResult, ...],
    run_id: str,
) -> RoleEvidenceReviewResult:
    """Require one semantic review for every normalized observed role."""
    if not run_id.strip() or review.run_id != run_id:
        raise DiscoveryValidationError(
            "The evidence review must use the parent workflow run ID."
        )
    if review.agent_name != ROLE_EVIDENCE_REVIEWER:
        raise DiscoveryValidationError(
            f"Unexpected evidence reviewer: {review.agent_name}"
        )
    if review.blockers:
        raise DiscoveryValidationError("The evidence review contains blockers.")
    if len(results) != len(ROLE_DISCOVERY_AGENT_BY_CATEGORY):
        raise DiscoveryValidationError(
            "Evidence review requires all three domain-agent results."
        )
    if any(result.run_id != run_id or result.blockers for result in results):
        raise DiscoveryValidationError(
            "Evidence review cannot validate incomplete or blocked agent results."
        )

    expected_roles = {
        normalize_role_name(observation.role_name)
        for result in results
        for observation in result.observations
    }
    reviewed_names = [
        normalize_role_name(reviewed.role_name)
        for reviewed in review.reviewed_roles
    ]
    if len(reviewed_names) != len(set(reviewed_names)):
        raise DiscoveryValidationError(
            "The evidence review contains a duplicate reviewed role."
        )
    if set(reviewed_names) != expected_roles:
        raise DiscoveryValidationError(
            "The evidence review must cover every observed role exactly once."
        )
    return review


def consolidate_agent_results(
    results: tuple[AgentDiscoveryResult, ...],
    run_id: str,
    existing_roles: tuple[ExistingRole, ...],
    discovered_on: date,
    search_period: DateRange,
) -> DiscoveryOutcome:
    """Validate a complete three-agent run before candidate selection."""
    if not run_id.strip():
        raise DiscoveryValidationError("Run ID must not be blank.")
    if len(results) != len(ROLE_DISCOVERY_AGENT_BY_CATEGORY):
        raise DiscoveryValidationError(
            "Role Discovery requires exactly one result from each domain agent."
        )

    by_category: dict[Category, AgentDiscoveryResult] = {}
    for result in results:
        if result.run_id != run_id:
            raise DiscoveryValidationError(
                "Agent results from different Role Discovery runs cannot be combined."
            )
        if result.search_period != search_period:
            raise DiscoveryValidationError(
                "Agent results must use the parent workflow search period."
            )
        if result.job_market != SOUTH_KOREA_JOB_MARKET:
            raise DiscoveryValidationError(
                "Agent results must use the South Korea job market."
            )
        if result.category in by_category:
            raise DiscoveryValidationError(
                f"Duplicate agent result for category: {result.category.value}"
            )
        expected_agent = ROLE_DISCOVERY_AGENT_BY_CATEGORY[result.category]
        if result.agent_name != expected_agent:
            raise DiscoveryValidationError(
                f"Unexpected agent for category {result.category.value}: "
                f"{result.agent_name}"
            )
        if result.blockers:
            raise DiscoveryValidationError(
                f"Agent result has blockers: {result.agent_name}"
            )
        if any(
            observation.suggested_category is not result.category
            for observation in result.observations
        ):
            raise DiscoveryValidationError(
                f"Agent result contains an observation outside its category: "
                f"{result.agent_name}"
            )
        by_category[result.category] = result

    if set(by_category) != set(ROLE_DISCOVERY_AGENT_BY_CATEGORY):
        raise DiscoveryValidationError(
            "Role Discovery is incomplete because a domain result is missing."
        )

    observations = tuple(
        observation
        for category in Category
        for observation in by_category[category].observations
    )
    validated = select_new_candidates(
        observations=observations,
        existing_roles=existing_roles,
        discovered_on=discovered_on,
        search_period=search_period,
    )
    agent_matches = tuple(
        match
        for category in Category
        for match in by_category[category].existing_matches
    )
    existing_by_name = {
        normalize_role_name(role.role_name): role for role in existing_roles
    }
    for match in agent_matches:
        normalized_observed = normalize_role_name(match.observed_role_name)
        normalized_existing = normalize_role_name(match.existing_role_name)
        existing = existing_by_name.get(normalized_existing)
        if (
            normalized_observed != normalized_existing
            or existing is None
            or existing.status is not match.existing_status
        ):
            raise DiscoveryValidationError(
                "Agent existing-role matches must agree with the parent snapshot."
            )
    unique_matches: dict[
        tuple[str, str, RoleStatus], ExistingRoleMatch
    ] = {}
    for match in (*validated.existing_matches, *agent_matches):
        key = (
            normalize_role_name(match.observed_role_name),
            normalize_role_name(match.existing_role_name),
            match.existing_status,
        )
        unique_matches.setdefault(key, match)

    return DiscoveryOutcome(
        new_candidates=validated.new_candidates,
        existing_matches=tuple(unique_matches.values()),
        sources_checked=sum(result.sources_checked for result in results),
        exclusions=tuple(
            exclusion
            for category in Category
            for exclusion in by_category[category].exclusions
        ),
    )
