"""Deterministic boundaries for collecting trends for approved roles."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from urllib.parse import urlsplit

from .role_discovery import Category, DateRange, RoleStatus, normalize_role_name
from .source_urls import (
    SourceUrlError,
    normalize_source_url,
    preferred_source_url,
    source_comparison_urls,
)


class TrendValidationError(ValueError):
    """Raised when a Trend Update input cannot be stored safely."""


class TrendApplyError(RuntimeError):
    """Raised when a prevalidated Trends DB write fails partway through."""

    def __init__(
        self,
        failed_url: str,
        created_urls: tuple[str, ...],
    ) -> None:
        super().__init__(f"Trend write failed for URL: {failed_url}")
        self.failed_url = failed_url
        self.created_urls = created_urls


class TrendSourceType(StrEnum):
    JOB_POSTING = "Job Posting"
    REPORT = "Report"
    ARTICLE = "Article"
    RESEARCH = "Research"
    OFFICIAL = "Official"


SOUTH_KOREA_JOB_MARKET = "South Korea"
BLOCKED_SOURCE_HOSTS = (
    "reddit.com",
    "news.ycombinator.com",
    "facebook.com",
    "instagram.com",
    "threads.net",
    "tiktok.com",
    "twitter.com",
    "x.com",
)


@dataclass(frozen=True)
class RoleSnapshotRecord:
    record_id: str
    role_name: str
    category: Category
    status: RoleStatus

    def __post_init__(self) -> None:
        if not self.record_id.strip() or not self.role_name.strip():
            raise TrendValidationError(
                "Every Roles DB snapshot record needs an ID and Role Name."
            )


@dataclass(frozen=True)
class ApprovedRole:
    record_id: str
    role_name: str
    category: Category


@dataclass(frozen=True)
class TrendSearchTask:
    role: ApprovedRole
    period: DateRange
    query: str


@dataclass(frozen=True)
class TrendObservation:
    title: str
    summary: str
    key_insight: str
    source_type: TrendSourceType
    source_name: str
    original_url: str
    published_on: date
    related_role_names: tuple[str, ...]
    domain: Category
    job_location: str | None = None
    job_market: str | None = None
    canonical_url: str | None = None

    def __post_init__(self) -> None:
        required_text = (
            self.title,
            self.summary,
            self.key_insight,
            self.source_name,
        )
        parsed = urlsplit(self.original_url)
        if (
            not all(value.strip() for value in required_text)
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or type(self.published_on) is not date
            or not self.related_role_names
            or any(not name.strip() for name in self.related_role_names)
        ):
            raise TrendValidationError(
                "Every trend needs complete text, an original HTTP or HTTPS URL, "
                "a verified published date, and at least one Related Role."
            )
        if _is_blocked_source(parsed.hostname or ""):
            raise TrendValidationError(
                f"Community and social sources are excluded: {self.original_url}"
            )
        try:
            preferred = preferred_source_url(self.original_url, self.canonical_url)
        except SourceUrlError as error:
            raise TrendValidationError(str(error)) from error
        if _is_blocked_source(urlsplit(preferred).hostname or ""):
            raise TrendValidationError(
                f"Community and social sources are excluded: {preferred}"
            )
        if self.source_type is TrendSourceType.JOB_POSTING:
            if not self.job_location or not self.job_location.strip():
                raise TrendValidationError(
                    "Every trend Job Posting needs an explicitly verified location."
                )
            if self.job_market != SOUTH_KOREA_JOB_MARKET:
                raise TrendValidationError(
                    "Trend Job Postings must be located in the South Korea job market."
                )


@dataclass(frozen=True)
class PlannedTrend:
    observation: TrendObservation
    related_role_ids: tuple[str, ...]
    collected_on: date


@dataclass(frozen=True)
class TrendUpdatePlan:
    trends: tuple[PlannedTrend, ...]
    skipped_existing_urls: tuple[str, ...]


@dataclass(frozen=True)
class NotionTrendPage:
    title: str
    original_url: str
    properties: dict[str, object]


@dataclass(frozen=True)
class TrendApplicationResult:
    created_urls: tuple[str, ...]
    skipped_existing_urls: tuple[str, ...]


def _is_blocked_source(hostname: str) -> bool:
    normalized = hostname.casefold().removeprefix("www.")
    return any(
        normalized == blocked or normalized.endswith(f".{blocked}")
        for blocked in BLOCKED_SOURCE_HOSTS
    )


def select_approved_roles(
    records: tuple[RoleSnapshotRecord, ...],
) -> tuple[ApprovedRole, ...]:
    """Freeze the Approved subset while rejecting ambiguous snapshot records."""
    record_ids: set[str] = set()
    names: set[str] = set()
    approved: list[ApprovedRole] = []
    for record in records:
        normalized_name = normalize_role_name(record.role_name)
        if record.record_id in record_ids:
            raise TrendValidationError(
                f"Duplicate Roles DB record ID: {record.record_id}"
            )
        if normalized_name in names:
            raise TrendValidationError(
                f"Ambiguous duplicate Role Name: {record.role_name}"
            )
        record_ids.add(record.record_id)
        names.add(normalized_name)
        if record.status is RoleStatus.APPROVED:
            approved.append(
                ApprovedRole(
                    record_id=record.record_id,
                    role_name=record.role_name.strip(),
                    category=record.category,
                )
            )
    return tuple(approved)


def build_trend_search_tasks(
    records: tuple[RoleSnapshotRecord, ...],
    period: DateRange,
) -> tuple[TrendSearchTask, ...]:
    """Build one web-search task for every role approved at run start."""
    excluded_sites = " ".join(f"-site:{host}" for host in BLOCKED_SOURCE_HOSTS)
    return tuple(
        TrendSearchTask(
            role=role,
            period=period,
            query=(
                f'"{role.role_name}" '
                "(trend OR report OR research OR release OR announcement OR "
                "동향 OR 보고서 OR 연구 OR 출시 OR 발표) "
                f"{excluded_sites}"
            ),
        )
        for role in select_approved_roles(records)
    )


def plan_trend_update(
    observations: tuple[TrendObservation, ...],
    approved_roles: tuple[ApprovedRole, ...],
    existing_urls: Sequence[str],
    period: DateRange,
    collected_on: date,
) -> TrendUpdatePlan:
    """Validate every observation before producing any Trends DB write."""
    if type(collected_on) is not date:
        raise TrendValidationError("Collected Date must be a valid date.")

    roles_by_name: dict[str, ApprovedRole] = {}
    role_ids: set[str] = set()
    for role in approved_roles:
        normalized_name = normalize_role_name(role.role_name)
        if (
            not role.record_id.strip()
            or not normalized_name
            or normalized_name in roles_by_name
            or role.record_id in role_ids
        ):
            raise TrendValidationError(
                "Approved role snapshot contains a missing or duplicate role."
            )
        roles_by_name[normalized_name] = role
        role_ids.add(role.record_id)

    try:
        existing = {
            normalize_source_url(url)
            for url in existing_urls
            if isinstance(url, str) and url.strip()
        }
    except SourceUrlError as error:
        raise TrendValidationError(
            f"Existing Trends DB URL cannot be normalized: {error}"
        ) from error
    seen_urls: set[str] = set()
    planned: list[PlannedTrend] = []
    skipped: list[str] = []

    for observation in observations:
        if not period.start <= observation.published_on <= period.end:
            raise TrendValidationError(
                f"Trend source is outside the search period: {observation.original_url}"
            )
        comparison_urls = source_comparison_urls(
            observation.original_url,
            observation.canonical_url,
        )
        stored_url = preferred_source_url(
            observation.original_url,
            observation.canonical_url,
        )
        if any(url in existing for url in comparison_urls):
            if stored_url not in skipped:
                skipped.append(stored_url)
            continue
        if any(url in seen_urls for url in comparison_urls):
            raise TrendValidationError(
                f"Duplicate URL after normalization in one Trend Update result: {stored_url}"
            )

        related_roles: list[ApprovedRole] = []
        related_names: set[str] = set()
        for role_name in observation.related_role_names:
            normalized_name = normalize_role_name(role_name)
            if normalized_name in related_names:
                continue
            role = roles_by_name.get(normalized_name)
            if role is None:
                raise TrendValidationError(
                    "Every Related Role must be Approved in the run-start snapshot: "
                    f"{role_name}"
                )
            related_names.add(normalized_name)
            related_roles.append(role)

        if not any(role.category is observation.domain for role in related_roles):
            raise TrendValidationError(
                f"Trend Domain must match at least one Related Role: {observation.title}"
            )

        planned.append(
            PlannedTrend(
                observation=observation,
                related_role_ids=tuple(role.record_id for role in related_roles),
                collected_on=collected_on,
            )
        )
        seen_urls.update(comparison_urls)

    return TrendUpdatePlan(
        trends=tuple(planned),
        skipped_existing_urls=tuple(skipped),
    )


def _rich_text(value: str) -> dict[str, object]:
    return {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": value.strip()},
            }
        ]
    }


def build_notion_trend_pages(
    plan: TrendUpdatePlan,
) -> tuple[NotionTrendPage, ...]:
    """Translate a prevalidated plan into exact Trends DB properties."""
    pages: list[NotionTrendPage] = []
    urls: set[str] = set()
    for planned in plan.trends:
        observation = planned.observation
        comparison_urls = source_comparison_urls(
            observation.original_url,
            observation.canonical_url,
        )
        stored_url = preferred_source_url(
            observation.original_url,
            observation.canonical_url,
        )
        if any(url in urls for url in comparison_urls):
            raise TrendValidationError(
                f"Duplicate planned trend URL: {stored_url}"
            )
        if not planned.related_role_ids or any(
            not record_id.strip() for record_id in planned.related_role_ids
        ):
            raise TrendValidationError(
                f"Every planned trend needs Related Role IDs: {observation.title}"
            )
        properties: dict[str, object] = {
            "Title": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": observation.title.strip()},
                    }
                ]
            },
            "Summary": _rich_text(observation.summary),
            "Key Insight": _rich_text(observation.key_insight),
            "Source Type": {"select": {"name": observation.source_type.value}},
            "Source Name": _rich_text(observation.source_name),
            "Original URL": {"url": stored_url},
            "Published Date": {
                "date": {"start": observation.published_on.isoformat()}
            },
            "Collected Date": {"date": {"start": planned.collected_on.isoformat()}},
            "Related Roles": {
                "relation": [
                    {"id": record_id} for record_id in planned.related_role_ids
                ]
            },
            "Domain": {"select": {"name": observation.domain.value}},
        }
        pages.append(
            NotionTrendPage(
                title=observation.title,
                original_url=stored_url,
                properties=properties,
            )
        )
        urls.update(comparison_urls)
    return tuple(pages)


def apply_trend_update_plan(
    plan: TrendUpdatePlan,
    create_page: Callable[[dict[str, object]], None],
) -> TrendApplicationResult:
    """Create prevalidated Trends DB pages through a caller-provided writer."""
    pages = build_notion_trend_pages(plan)
    created_urls: list[str] = []
    for page in pages:
        try:
            create_page(page.properties)
        except Exception as error:
            raise TrendApplyError(
                failed_url=page.original_url,
                created_urls=tuple(created_urls),
            ) from error
        created_urls.append(page.original_url)
    return TrendApplicationResult(
        created_urls=tuple(created_urls),
        skipped_existing_urls=plan.skipped_existing_urls,
    )


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TrendValidationError(f"{field} must be an object.")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TrendValidationError(f"{field} must be non-empty text.")
    return value.strip()


def _text_list(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise TrendValidationError(f"{field} must be a non-empty list.")
    return tuple(_text(item, f"{field}[]") for item in value)


def _date(value: object, field: str) -> date:
    text = _text(value, field)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise TrendValidationError(
            f"{field} must be an ISO date in YYYY-MM-DD format."
        ) from error


def parse_trend_observations(
    payload: Mapping[str, object] | str,
) -> tuple[TrendObservation, ...]:
    """Parse structured web-research output into validated observations."""
    try:
        raw = json.loads(payload) if isinstance(payload, str) else payload
    except json.JSONDecodeError as error:
        raise TrendValidationError("Trend result must be valid JSON.") from error
    root = _mapping(raw, "result")
    raw_observations = root.get("observations")
    if not isinstance(raw_observations, list):
        raise TrendValidationError("observations must be a list.")

    observations: list[TrendObservation] = []
    try:
        for index, item in enumerate(raw_observations):
            observation = _mapping(item, f"observations[{index}]")
            observations.append(
                TrendObservation(
                    title=_text(observation.get("title"), "title"),
                    summary=_text(observation.get("summary"), "summary"),
                    key_insight=_text(
                        observation.get("key_insight"),
                        "key_insight",
                    ),
                    source_type=TrendSourceType(
                        _text(observation.get("source_type"), "source_type")
                    ),
                    source_name=_text(
                        observation.get("source_name"),
                        "source_name",
                    ),
                    original_url=_text(
                        observation.get("original_url"),
                        "original_url",
                    ),
                    published_on=_date(
                        observation.get("published_date"),
                        "published_date",
                    ),
                    related_role_names=_text_list(
                        observation.get("related_roles"),
                        "related_roles",
                    ),
                    domain=Category(_text(observation.get("domain"), "domain")),
                    job_location=(
                        _text(observation.get("job_location"), "job_location")
                        if observation.get("job_location") is not None
                        else None
                    ),
                    job_market=(
                        _text(observation.get("job_market"), "job_market")
                        if observation.get("job_market") is not None
                        else None
                    ),
                    canonical_url=(
                        _text(observation.get("canonical_url"), "canonical_url")
                        if observation.get("canonical_url") is not None
                        else None
                    ),
                )
            )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, TrendValidationError):
            raise
        raise TrendValidationError(f"Invalid Trend result value: {error}") from error
    return tuple(observations)
