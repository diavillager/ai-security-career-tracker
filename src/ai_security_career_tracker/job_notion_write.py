"""Safe application boundary for writing a Job Discovery plan to Notion."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .job_discovery import JobDiscoveryPlan, ReviewStatus
from .notion_databases import NotionDatabaseConfig
from .notion_job_migration import NotionJobPage, build_notion_job_page
from .notion_properties import (
    JOB_CHANGE_STATUS,
    JOB_COLLECTED_DATE,
    JOB_DEADLINE,
    JOB_DOMAIN,
    JOB_EMPLOYER,
    JOB_EMPLOYMENT_TYPE,
    JOB_EXPERIENCE_LEVEL,
    JOB_INTEREST_STATUS,
    JOB_LAST_CHECKED_DATE,
    JOB_LOCATION,
    JOB_ORIGINAL_URL,
    JOB_POSTING_ID,
    JOB_POSTING_STATUS,
    JOB_PUBLISHED_DATE,
    JOB_PUBLISHED_DATE_STATUS,
    JOB_RECOGNIZED_ROLE,
    JOB_RELATED_URLS,
    JOB_REQUIREMENTS,
    JOB_RESPONSIBILITIES,
    JOB_REVIEW_NOTES,
    JOB_REVIEW_STATUS,
    JOB_SEARCH_ROUTES,
    JOB_SOURCE_TYPE,
    JOB_TECHNOLOGY_KEYWORDS,
    JOB_TITLE,
    JOB_WORK_MODE,
)
from .source_urls import source_comparison_urls


class JobNotionWriteError(ValueError):
    """Raised before writing when the configured Jobs target is unsafe."""


class JobNotionApplyError(RuntimeError):
    """Raised when a prevalidated Jobs write fails partway through."""

    def __init__(self, failed_url: str, created_urls: tuple[str, ...]) -> None:
        super().__init__(
            "Notion Jobs write failed after creating "
            f"{len(created_urls)} page(s); failed URL: {failed_url}"
        )
        self.failed_url = failed_url
        self.created_urls = created_urls


EXPECTED_JOBS_PROPERTY_TYPES: Mapping[str, str] = {
    JOB_TITLE: "title",
    JOB_EMPLOYER: "rich_text",
    JOB_RECOGNIZED_ROLE: "rich_text",
    JOB_DOMAIN: "select",
    JOB_REVIEW_STATUS: "select",
    JOB_EXPERIENCE_LEVEL: "select",
    JOB_RESPONSIBILITIES: "rich_text",
    JOB_REQUIREMENTS: "rich_text",
    JOB_TECHNOLOGY_KEYWORDS: "multi_select",
    JOB_LOCATION: "rich_text",
    JOB_EMPLOYMENT_TYPE: "select",
    JOB_WORK_MODE: "select",
    JOB_PUBLISHED_DATE: "date",
    JOB_DEADLINE: "date",
    JOB_POSTING_STATUS: "select",
    JOB_INTEREST_STATUS: "select",
    JOB_SOURCE_TYPE: "select",
    JOB_ORIGINAL_URL: "url",
    JOB_RELATED_URLS: "rich_text",
    JOB_PUBLISHED_DATE_STATUS: "select",
    JOB_POSTING_ID: "rich_text",
    JOB_SEARCH_ROUTES: "multi_select",
    JOB_COLLECTED_DATE: "date",
    JOB_LAST_CHECKED_DATE: "date",
    JOB_CHANGE_STATUS: "select",
    JOB_REVIEW_NOTES: "rich_text",
}

OPTION_PROPERTY_TYPES = frozenset({"select", "multi_select"})


@dataclass(frozen=True)
class JobsDatabaseSnapshot:
    """Read-only schema snapshot taken immediately before an approved write."""

    data_source_id: str
    property_types: Mapping[str, str]
    options: Mapping[str, frozenset[str]]


@dataclass(frozen=True)
class JobNotionApplicationResult:
    created_urls: tuple[str, ...]
    eligible_created: int
    needs_review_created: int
    excluded_not_written: int
    duplicates_not_written: int


def build_notion_job_pages(plan: JobDiscoveryPlan) -> tuple[NotionJobPage, ...]:
    """Translate every writable job before any external write begins."""

    if any(item.status is not ReviewStatus.ELIGIBLE for item in plan.eligible):
        raise JobNotionWriteError("The eligible group contains a non-eligible job.")
    if any(
        item.status is not ReviewStatus.NEEDS_REVIEW
        for item in plan.needs_review
    ):
        raise JobNotionWriteError(
            "The needs-review group contains a job with another status."
        )
    pages: list[NotionJobPage] = []
    stored_urls: set[str] = set()
    for planned in (*plan.eligible, *plan.needs_review):
        page = build_notion_job_page(planned)
        stored_url = page.properties[JOB_ORIGINAL_URL].get(  # type: ignore[union-attr]
            "url"
        )
        if not isinstance(stored_url, str) or not stored_url.strip():
            raise JobNotionWriteError("Every Jobs page needs a stored original URL.")
        comparison_urls = set(source_comparison_urls(stored_url))
        if comparison_urls & stored_urls:
            raise JobNotionWriteError(
                f"A Job Discovery plan contains a duplicate stored URL: {stored_url}"
            )
        stored_urls.update(comparison_urls)
        pages.append(page)
    return tuple(pages)


def _page_option_values(page: NotionJobPage) -> tuple[tuple[str, str], ...]:
    values: list[tuple[str, str]] = []
    for name, expected_type in EXPECTED_JOBS_PROPERTY_TYPES.items():
        if expected_type not in OPTION_PROPERTY_TYPES:
            continue
        property_value = page.properties[name]
        if expected_type == "select":
            selected = property_value.get("select")  # type: ignore[union-attr]
            if not isinstance(selected, Mapping) or not isinstance(
                selected.get("name"), str
            ):
                raise JobNotionWriteError(
                    f"Invalid select value for Jobs property: {name}"
                )
            values.append((name, selected["name"]))
        else:
            selected_many = property_value.get("multi_select")  # type: ignore[union-attr]
            if not isinstance(selected_many, list):
                raise JobNotionWriteError(
                    f"Invalid multi-select value for Jobs property: {name}"
                )
            for option in selected_many:
                if not isinstance(option, Mapping) or not isinstance(
                    option.get("name"), str
                ):
                    raise JobNotionWriteError(
                        f"Invalid multi-select option for Jobs property: {name}"
                    )
                values.append((name, option["name"]))
    return tuple(values)


def validate_jobs_write_target(
    config: NotionDatabaseConfig,
    target: JobsDatabaseSnapshot,
    pages: tuple[NotionJobPage, ...],
) -> None:
    """Match saved configuration, live schema, and every option before writing."""

    if not config.is_configured or not config.project_page_url.strip():
        raise JobNotionWriteError("Jobs and Trends configuration must be complete.")
    if not target.data_source_id.strip():
        raise JobNotionWriteError("The live Jobs data source ID must not be blank.")
    if config.jobs_database_id != target.data_source_id:
        raise JobNotionWriteError(
            "The configured Jobs identifier does not match the live schema snapshot."
        )
    for name, expected_type in EXPECTED_JOBS_PROPERTY_TYPES.items():
        if target.property_types.get(name) != expected_type:
            raise JobNotionWriteError(
                f"Jobs property is missing or has the wrong type: {name} ({expected_type})"
            )
        if expected_type in OPTION_PROPERTY_TYPES and name not in target.options:
            raise JobNotionWriteError(f"Jobs options were not read for property: {name}")
    for page in pages:
        for property_name, option_name in _page_option_values(page):
            if option_name not in target.options[property_name]:
                raise JobNotionWriteError(
                    "Jobs schema does not contain the required option: "
                    f"{property_name}={option_name}"
                )


def apply_job_discovery_plan(
    plan: JobDiscoveryPlan,
    config: NotionDatabaseConfig,
    target: JobsDatabaseSnapshot,
    create_page: Callable[[str, dict[str, object]], object],
) -> JobNotionApplicationResult:
    """Write only prevalidated eligible and needs-review jobs to the verified target."""

    pages = build_notion_job_pages(plan)
    validate_jobs_write_target(config, target, pages)
    created_urls: list[str] = []
    for page in pages:
        stored_url = page.properties[JOB_ORIGINAL_URL]["url"]  # type: ignore[index]
        try:
            create_page(target.data_source_id, page.properties)
        except Exception as error:
            raise JobNotionApplyError(stored_url, tuple(created_urls)) from error
        created_urls.append(stored_url)
    return JobNotionApplicationResult(
        created_urls=tuple(created_urls),
        eligible_created=len(plan.eligible),
        needs_review_created=len(plan.needs_review),
        excluded_not_written=len(plan.excluded),
        duplicates_not_written=len(plan.duplicates),
    )
