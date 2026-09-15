"""Deterministic boundaries for planning and consolidating Role Discovery."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from urllib.parse import urlsplit


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


@dataclass(frozen=True)
class EvidenceSource:
    name: str
    url: str
    published_on: date

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


@dataclass(frozen=True)
class CandidateRole:
    role_name: str
    category: Category
    description: str
    key_responsibilities: tuple[str, ...]
    discovery_reasons: tuple[str, ...]
    evidence_sources: tuple[EvidenceSource, ...]
    first_discovered: date
    last_reviewed: date
    status: RoleStatus = RoleStatus.CANDIDATE


@dataclass(frozen=True)
class ExistingRoleMatch:
    observed_role_name: str
    existing_role_name: str
    existing_status: RoleStatus


@dataclass(frozen=True)
class DiscoveryOutcome:
    new_candidates: tuple[CandidateRole, ...]
    existing_matches: tuple[ExistingRoleMatch, ...]


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


def default_period(as_of: date, days: int = 7) -> DateRange:
    """Return an inclusive calendar range ending on ``as_of``."""
    if days < 1:
        raise DiscoveryValidationError("Search days must be at least one.")
    return DateRange(start=as_of - timedelta(days=days - 1), end=as_of)


def build_search_plan(period: DateRange) -> tuple[SearchQuery, ...]:
    """Build one independent, non-whitelist search query for each domain."""
    queries: list[SearchQuery] = []
    for category in Category:
        roles = " OR ".join(f'"{role}"' for role in SEEDS[category])
        responsibilities = " OR ".join(
            f'"{term}"' for term in RESPONSIBILITY_TERMS[category]
        )
        query = (
            f"({roles}) ({responsibilities}) "
            f"(job OR careers OR responsibilities OR team)"
        )
        queries.append(SearchQuery(category=category, query=query, period=period))
    return tuple(queries)


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

        if len(evidence_by_url) < 2:
            raise DiscoveryValidationError(
                f"At least two distinct evidence sources are required for role: "
                f"{group[0].role_name}"
            )

        candidates.append(
            CandidateRole(
                role_name=group[0].role_name.strip(),
                category=next(iter(categories)),
                description=group[0].description.strip(),
                key_responsibilities=_unique_text(
                    [value for item in group for value in item.key_responsibilities]
                ),
                discovery_reasons=_unique_text(
                    [item.discovery_reason for item in group]
                ),
                evidence_sources=tuple(evidence_by_url.values()),
                first_discovered=discovered_on,
                last_reviewed=discovered_on,
            )
        )

    return DiscoveryOutcome(
        new_candidates=tuple(candidates),
        existing_matches=tuple(existing_matches),
    )
