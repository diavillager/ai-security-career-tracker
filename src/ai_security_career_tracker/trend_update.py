"""Deterministic boundaries for Jobs-independent Trend Update runs."""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from urllib.parse import urlsplit

from .classification import TrendSourceType
from .notion_databases import NotionDatabaseConfig
from .notion_options import notion_trend_source_type_name
from .notion_properties import (
    TREND_CAREER_INSIGHT, TREND_COLLECTED_DATE, TREND_DOMAIN,
    TREND_ORIGINAL_URL, TREND_PUBLISHED_DATE, TREND_REGION_SCOPE,
    TREND_RELATED_ROLES, TREND_SOURCE_NAME, TREND_SOURCE_TYPE, TREND_SUMMARY,
    TREND_TECHNOLOGY_KEYWORDS, TREND_TITLE, TREND_TYPE,
)
from .role_discovery import Category, DateRange, normalize_role_name
from .source_urls import (
    SourceUrlError, normalize_source_url, preferred_source_url,
    source_comparison_urls,
)


class TrendValidationError(ValueError):
    """Raised when a Trend Update input cannot be stored safely."""


class TrendApplyError(RuntimeError):
    def __init__(self, failed_url: str, created_urls: tuple[str, ...]) -> None:
        super().__init__(f"Trend write failed for URL: {failed_url}")
        self.failed_url = failed_url
        self.created_urls = created_urls


class TrendType(StrEnum):
    TECHNOLOGY = "Technology"
    HIRING_MARKET = "Hiring Market"
    INDUSTRY = "Industry"
    REGULATION_POLICY = "Regulation and Policy"
    THREAT_INCIDENT = "Threat and Incident"
    RESEARCH = "Research"


class RegionScope(StrEnum):
    SOUTH_KOREA = "South Korea"
    OVERSEAS = "Overseas"
    GLOBAL = "Global"


TREND_TYPE_TO_NOTION = {
    TrendType.TECHNOLOGY: "기술", TrendType.HIRING_MARKET: "채용시장",
    TrendType.INDUSTRY: "산업", TrendType.REGULATION_POLICY: "규제·정책",
    TrendType.THREAT_INCIDENT: "위협·사고", TrendType.RESEARCH: "연구",
}
REGION_SCOPE_TO_NOTION = {
    RegionScope.SOUTH_KOREA: "국내", RegionScope.OVERSEAS: "해외",
    RegionScope.GLOBAL: "글로벌",
}
SOUTH_KOREA_JOB_MARKET = "South Korea"
BLOCKED_SOURCE_HOSTS = (
    "reddit.com", "news.ycombinator.com", "facebook.com", "instagram.com",
    "threads.net", "tiktok.com", "twitter.com", "x.com",
)
EXPECTED_TRENDS_PROPERTY_TYPES: Mapping[str, str] = {
    TREND_TITLE: "title", TREND_SUMMARY: "text", TREND_CAREER_INSIGHT: "text",
    TREND_SOURCE_TYPE: "select", TREND_SOURCE_NAME: "text",
    TREND_ORIGINAL_URL: "url", TREND_PUBLISHED_DATE: "date",
    TREND_COLLECTED_DATE: "date", TREND_RELATED_ROLES: "multi_select",
    TREND_DOMAIN: "multi_select", TREND_TECHNOLOGY_KEYWORDS: "multi_select",
    TREND_TYPE: "select", TREND_REGION_SCOPE: "select",
}
OPTION_PROPERTY_TYPES = frozenset({"select", "multi_select"})


@dataclass(frozen=True)
class TrendSearchTask:
    search_route: Category
    period: DateRange
    query: str


@dataclass(frozen=True)
class TrendObservation:
    title: str
    summary: str
    career_insight: str
    source_type: TrendSourceType
    source_name: str
    original_url: str
    published_on: date
    related_roles: tuple[str, ...]
    domains: tuple[Category, ...]
    technology_keywords: tuple[str, ...]
    trend_type: TrendType
    region_scope: RegionScope
    classification_basis: str
    job_location: str | None = None
    job_market: str | None = None
    canonical_url: str | None = None

    def __post_init__(self) -> None:
        required = (self.title, self.summary, self.career_insight,
                    self.source_name, self.classification_basis)
        parsed = urlsplit(self.original_url)
        if (not all(value.strip() for value in required)
                or parsed.scheme not in {"http", "https"} or not parsed.netloc
                or type(self.published_on) is not date):
            raise TrendValidationError(
                "Every trend needs complete text, an original HTTP or HTTPS URL, "
                "and a verified published date."
            )
        if not isinstance(self.source_type, TrendSourceType):
            raise TrendValidationError("Trend Source Type is invalid.")
        if not isinstance(self.trend_type, TrendType):
            raise TrendValidationError("Trend Type is invalid.")
        if not isinstance(self.region_scope, RegionScope):
            raise TrendValidationError("Region Scope is invalid.")
        if not self.domains or any(not isinstance(item, Category) for item in self.domains):
            raise TrendValidationError("Every trend needs at least one valid Domain.")
        if len(set(self.domains)) != len(self.domains):
            raise TrendValidationError("Trend Domains must not be duplicated.")
        self._validate_unique_text(self.related_roles, "Related Roles")
        self._validate_unique_text(self.technology_keywords, "Technology Keywords")
        if self.summary.strip() == self.career_insight.strip():
            raise TrendValidationError(
                "Summary and Career Insight must be written as separate values."
            )
        if _is_blocked_source(parsed.hostname or ""):
            raise TrendValidationError(f"Community and social sources are excluded: {self.original_url}")
        try:
            preferred = preferred_source_url(self.original_url, self.canonical_url)
        except SourceUrlError as error:
            raise TrendValidationError(str(error)) from error
        if _is_blocked_source(urlsplit(preferred).hostname or ""):
            raise TrendValidationError(f"Community and social sources are excluded: {preferred}")
        if self.source_type is TrendSourceType.JOB_POSTING:
            if not self.job_location or not self.job_location.strip():
                raise TrendValidationError("Every trend Job Posting needs an explicitly verified location.")
            if self.job_market != SOUTH_KOREA_JOB_MARKET:
                raise TrendValidationError("Trend Job Postings must be located in the South Korea job market.")
            if self.region_scope is not RegionScope.SOUTH_KOREA:
                raise TrendValidationError("Trend Job Postings must use the South Korea region scope.")

    @staticmethod
    def _validate_unique_text(values: tuple[str, ...], field: str) -> None:
        if not values or any(not value.strip() for value in values):
            raise TrendValidationError(f"Every trend needs at least one {field} value.")
        normalized = tuple(normalize_role_name(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise TrendValidationError(f"{field} must not contain duplicates.")


@dataclass(frozen=True)
class PlannedTrend:
    observation: TrendObservation
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
class TrendsDatabaseSnapshot:
    data_source_id: str
    property_types: Mapping[str, str]
    options: Mapping[str, frozenset[str]]


@dataclass(frozen=True)
class TrendApplicationResult:
    created_urls: tuple[str, ...]
    skipped_existing_urls: tuple[str, ...]


def _is_blocked_source(hostname: str) -> bool:
    normalized = hostname.casefold().removeprefix("www.")
    return any(normalized == blocked or normalized.endswith(f".{blocked}")
               for blocked in BLOCKED_SOURCE_HOSTS)


def build_trend_search_tasks(period: DateRange) -> tuple[TrendSearchTask, ...]:
    """Build three field-level tasks without reading Jobs or legacy Roles."""
    excluded = " ".join(f"-site:{host}" for host in BLOCKED_SOURCE_HOSTS)
    topics = {
        Category.AI: "AI artificial intelligence LLM agent model",
        Category.SECURITY: "cybersecurity cloud security vulnerability threat",
        Category.AI_SECURITY: ('"AI security" "LLM security" "model security" '
                               '"AI safety" "prompt injection"'),
    }
    return tuple(TrendSearchTask(route, period,
        f"{topics[route]} (report OR research OR release OR announcement OR "
        f"policy OR incident OR 동향 OR 보고서 OR 연구 OR 출시 OR 정책 OR 사고) {excluded}")
        for route in (Category.AI, Category.SECURITY, Category.AI_SECURITY))


def plan_trend_update(observations: tuple[TrendObservation, ...],
                      existing_urls: Sequence[str], period: DateRange,
                      collected_on: date) -> TrendUpdatePlan:
    """Validate and deduplicate observations without Jobs or Roles snapshots."""
    if type(collected_on) is not date:
        raise TrendValidationError("Collected Date must be a valid date.")
    try:
        existing = {normalize_source_url(url) for url in existing_urls
                    if isinstance(url, str) and url.strip()}
    except SourceUrlError as error:
        raise TrendValidationError(f"Existing Trends DB URL cannot be normalized: {error}") from error
    seen: set[str] = set()
    planned: list[PlannedTrend] = []
    skipped: list[str] = []
    for observation in observations:
        if not period.start <= observation.published_on <= period.end:
            raise TrendValidationError(f"Trend source is outside the search period: {observation.original_url}")
        comparison = source_comparison_urls(observation.original_url, observation.canonical_url)
        stored = preferred_source_url(observation.original_url, observation.canonical_url)
        if any(url in existing for url in comparison):
            if stored not in skipped:
                skipped.append(stored)
            continue
        if any(url in seen for url in comparison):
            raise TrendValidationError(
                f"Duplicate URL after normalization in one Trend Update result: {stored}"
            )
        planned.append(PlannedTrend(observation, collected_on))
        seen.update(comparison)
    return TrendUpdatePlan(tuple(planned), tuple(skipped))


def _text_objects(value: str) -> list[dict[str, object]]:
    text = value.strip()
    return [{"type": "text", "text": {"content": text[i:i + 2000]}}
            for i in range(0, len(text), 2000)]


def _rich_text(value: str) -> dict[str, object]:
    return {"rich_text": _text_objects(value)}


def build_notion_trend_pages(plan: TrendUpdatePlan) -> tuple[NotionTrendPage, ...]:
    pages: list[NotionTrendPage] = []
    urls: set[str] = set()
    for planned in plan.trends:
        item = planned.observation
        comparison = source_comparison_urls(item.original_url, item.canonical_url)
        stored = preferred_source_url(item.original_url, item.canonical_url)
        if any(url in urls for url in comparison):
            raise TrendValidationError(f"Duplicate planned trend URL: {stored}")
        properties: dict[str, object] = {
            TREND_TITLE: {"title": _text_objects(item.title)},
            TREND_SUMMARY: _rich_text(item.summary),
            TREND_CAREER_INSIGHT: _rich_text(item.career_insight),
            TREND_SOURCE_TYPE: {"select": {"name": notion_trend_source_type_name(item.source_type)}},
            TREND_SOURCE_NAME: _rich_text(item.source_name),
            TREND_ORIGINAL_URL: {"url": stored},
            TREND_PUBLISHED_DATE: {"date": {"start": item.published_on.isoformat()}},
            TREND_COLLECTED_DATE: {"date": {"start": planned.collected_on.isoformat()}},
            TREND_RELATED_ROLES: {"multi_select": [{"name": x} for x in item.related_roles]},
            TREND_DOMAIN: {"multi_select": [{"name": x.value} for x in item.domains]},
            TREND_TECHNOLOGY_KEYWORDS: {"multi_select": [{"name": x} for x in item.technology_keywords]},
            TREND_TYPE: {"select": {"name": TREND_TYPE_TO_NOTION[item.trend_type]}},
            TREND_REGION_SCOPE: {"select": {"name": REGION_SCOPE_TO_NOTION[item.region_scope]}},
        }
        pages.append(NotionTrendPage(item.title, stored, properties))
        urls.update(comparison)
    return tuple(pages)


def _page_option_values(page: NotionTrendPage) -> tuple[tuple[str, str], ...]:
    values: list[tuple[str, str]] = []
    for name, expected in EXPECTED_TRENDS_PROPERTY_TYPES.items():
        if expected not in OPTION_PROPERTY_TYPES:
            continue
        value = page.properties[name]
        if expected == "select":
            selected = value.get("select")  # type: ignore[union-attr]
            if not isinstance(selected, Mapping) or not isinstance(selected.get("name"), str):
                raise TrendValidationError(f"Invalid Trends select value: {name}")
            values.append((name, selected["name"]))
        else:
            selected = value.get("multi_select")  # type: ignore[union-attr]
            if not isinstance(selected, list):
                raise TrendValidationError(f"Invalid Trends multi-select value: {name}")
            for option in selected:
                if not isinstance(option, Mapping) or not isinstance(option.get("name"), str):
                    raise TrendValidationError(f"Invalid Trends option: {name}")
                values.append((name, option["name"]))
    return tuple(values)


def validate_trends_write_target(config: NotionDatabaseConfig,
                                  target: TrendsDatabaseSnapshot,
                                  pages: tuple[NotionTrendPage, ...]) -> None:
    if not config.is_configured or not config.project_page_url.strip():
        raise TrendValidationError("Jobs and Trends configuration must be complete.")
    if config.trends_database_id != target.data_source_id:
        raise TrendValidationError("The configured Trends identifier does not match the live schema snapshot.")
    for name, expected in EXPECTED_TRENDS_PROPERTY_TYPES.items():
        if target.property_types.get(name) != expected:
            raise TrendValidationError(f"Trends property is missing or has the wrong type: {name} ({expected})")
        if expected in OPTION_PROPERTY_TYPES and name not in target.options:
            raise TrendValidationError(f"Trends options were not read for property: {name}")
    for page in pages:
        for name, option in _page_option_values(page):
            if option not in target.options[name]:
                raise TrendValidationError(f"Trends schema does not contain the required option: {name}={option}")


def apply_trend_update_plan(plan: TrendUpdatePlan, config: NotionDatabaseConfig,
                            target: TrendsDatabaseSnapshot,
                            create_page: Callable[[str, dict[str, object]], object]) -> TrendApplicationResult:
    pages = build_notion_trend_pages(plan)
    validate_trends_write_target(config, target, pages)
    created: list[str] = []
    for page in pages:
        try:
            create_page(target.data_source_id, page.properties)
        except Exception as error:
            raise TrendApplyError(page.original_url, tuple(created)) from error
        created.append(page.original_url)
    return TrendApplicationResult(tuple(created), plan.skipped_existing_urls)


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
    try:
        return date.fromisoformat(_text(value, field))
    except ValueError as error:
        raise TrendValidationError(f"{field} must be an ISO date in YYYY-MM-DD format.") from error


def parse_trend_observations(payload: Mapping[str, object] | str) -> tuple[TrendObservation, ...]:
    try:
        root = _mapping(json.loads(payload) if isinstance(payload, str) else payload, "result")
    except json.JSONDecodeError as error:
        raise TrendValidationError("Trend result must be valid JSON.") from error
    raw = root.get("observations")
    if not isinstance(raw, list):
        raise TrendValidationError("observations must be a list.")
    result: list[TrendObservation] = []
    try:
        for index, value in enumerate(raw):
            item = _mapping(value, f"observations[{index}]")
            result.append(TrendObservation(
                title=_text(item.get("title"), "title"),
                summary=_text(item.get("summary"), "summary"),
                career_insight=_text(item.get("career_insight"), "career_insight"),
                source_type=TrendSourceType(_text(item.get("source_type"), "source_type")),
                source_name=_text(item.get("source_name"), "source_name"),
                original_url=_text(item.get("original_url"), "original_url"),
                published_on=_date(item.get("published_date"), "published_date"),
                related_roles=_text_list(item.get("related_roles"), "related_roles"),
                domains=tuple(Category(x) for x in _text_list(item.get("domains"), "domains")),
                technology_keywords=_text_list(item.get("technology_keywords"), "technology_keywords"),
                trend_type=TrendType(_text(item.get("trend_type"), "trend_type")),
                region_scope=RegionScope(_text(item.get("region_scope"), "region_scope")),
                classification_basis=_text(item.get("classification_basis"), "classification_basis"),
                job_location=(_text(item.get("job_location"), "job_location") if item.get("job_location") is not None else None),
                job_market=(_text(item.get("job_market"), "job_market") if item.get("job_market") is not None else None),
                canonical_url=(_text(item.get("canonical_url"), "canonical_url") if item.get("canonical_url") is not None else None),
            ))
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, TrendValidationError):
            raise
        raise TrendValidationError(f"Invalid Trend result value: {error}") from error
    return tuple(result)
