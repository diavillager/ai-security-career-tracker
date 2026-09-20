"""Pure planning boundaries for the Jobs and Trends Notion migration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .job_discovery import (
    EmploymentType,
    ExperienceLevel,
    JobDomain,
    JobObservation,
    JobSourceType,
    PlannedJob,
    PostingStatus,
    ReviewReason,
    ReviewStatus,
    WorkMode,
)
from .notion_options import (
    JOB_EMPLOYMENT_TYPE_TO_NOTION,
    JOB_EXPERIENCE_LEVEL_TO_NOTION,
    JOB_POSTING_STATUS_TO_NOTION,
    JOB_SOURCE_TYPE_TO_NOTION,
    JOB_WORK_MODE_TO_NOTION,
    notion_job_review_status_name,
)
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


class NotionJobMigrationError(ValueError):
    """Raised when a migration plan cannot preserve the verified source data."""


@dataclass(frozen=True)
class LegacyRoleMigrationInput:
    page_id: str
    role_name: str
    employer_name: str
    recognized_role: str
    domain: JobDomain
    experience_level: ExperienceLevel
    responsibilities: tuple[str, ...]
    technology_keywords: tuple[str, ...]
    location: str
    source_type: JobSourceType
    source_url: str | None
    related_urls: tuple[str, ...]
    posting_id: str | None
    published_on: date | None
    first_discovered_on: date
    last_reviewed_on: date
    role_description: str
    evidence_sources: str
    legacy_notes: str
    search_routes: tuple[JobDomain, ...]


@dataclass(frozen=True)
class NotionJobPage:
    source_url: str
    properties: dict[str, object]


@dataclass(frozen=True)
class NotionJobMigrationPlan:
    jobs_schema: str
    trends_schema_statements: str
    job_pages: tuple[NotionJobPage, ...]
    archived_role_page_ids: tuple[str, ...]


def jobs_schema_ddl() -> str:
    """Return the exact SQL DDL accepted by Notion create_database."""

    return """CREATE TABLE (
"공고명" TITLE,
"회사명" RICH_TEXT,
"인식한 직무" RICH_TEXT,
"직무 분야" SELECT('AI':blue, 'Security':red, 'AI × Security':purple),
"검토 상태" SELECT('적합':green, '검토 필요':yellow),
"경력 수준" SELECT('신입':green, '경력':blue, '신입·경력':purple, '미확인':gray),
"주요 업무" RICH_TEXT,
"자격 요건" RICH_TEXT,
"기술 키워드" MULTI_SELECT('VPN':blue, 'Firewall':red, 'IAM':purple, 'Endpoint Security':orange, '보안 운영':green),
"근무지" RICH_TEXT,
"고용 형태" SELECT('정규직':green, '계약직':blue, '인턴':purple, '기타':gray, '미확인':default),
"근무 방식" SELECT('출근':blue, '하이브리드':purple, '원격':green, '미확인':gray),
"게시일" DATE,
"마감일" DATE,
"모집 상태" SELECT('모집 중':green, '마감':gray, '미확인':yellow),
"관심 상태" SELECT('신규':blue, '관심':yellow, '지원 예정':purple, '지원':green, '제외':gray),
"출처 유형" SELECT('기업 공식':blue, 'Saramin':green, 'JobKorea':orange, 'Wanted':purple, 'Jumpit':pink, '기타':gray),
"원문 URL" URL,
"관련 URL" RICH_TEXT,
"게시일 상태" SELECT('확인':green, '미확인':yellow),
"공고 식별자" RICH_TEXT,
"검색 경로" MULTI_SELECT('AI':blue, 'Security':red, 'AI × Security':purple),
"수집일" DATE,
"마지막 확인일" DATE,
"변경 상태" SELECT('신규':blue, '변경됨':yellow, '변경 없음':gray),
"검토 메모" RICH_TEXT
)"""


def trends_schema_migration_statements() -> str:
    """Return the approved empty-Trends migration statements."""

    return "; ".join(
        (
            'RENAME COLUMN "핵심 시사점" TO "취업 시사점"',
            'DROP COLUMN "관련 직무"',
            'ADD COLUMN "관련 직무" MULTI_SELECT()',
            'ADD COLUMN "기술 키워드" MULTI_SELECT()',
            'ADD COLUMN "동향 유형" SELECT(\'기술\':blue, \'채용시장\':green, \'산업\':orange, \'규제·정책\':purple, \'위협·사고\':red, \'연구\':yellow)',
            'ADD COLUMN "지역 범위" SELECT(\'국내\':blue, \'해외\':orange, \'글로벌\':purple)',
        )
    )


def _text_objects(value: str) -> list[dict[str, object]]:
    text = value.strip()
    return [
        {"type": "text", "text": {"content": text[index : index + 2000]}}
        for index in range(0, len(text), 2000)
    ]


def _rich_text(value: str) -> dict[str, object]:
    return {"rich_text": _text_objects(value)}


def _joined(values: tuple[str, ...]) -> str:
    return "\n".join(value.strip() for value in values if value.strip())


def build_notion_job_page(
    planned: PlannedJob,
    *,
    last_checked_on: date | None = None,
    published_date_verified: bool = True,
    interest_status: str = "신규",
    change_status: str = "신규",
) -> NotionJobPage:
    """Translate one validated planned job into exact Notion properties."""

    if planned.status is ReviewStatus.EXCLUDED:
        raise NotionJobMigrationError("Excluded jobs must not be stored in Jobs DB.")
    observation = planned.observation
    if observation.job_market != "South Korea" or not observation.location.strip():
        raise NotionJobMigrationError("Jobs DB requires a verified South Korea location.")
    if interest_status not in {"신규", "관심", "지원 예정", "지원", "제외"}:
        raise NotionJobMigrationError("Unsupported Jobs interest status.")
    if change_status not in {"신규", "변경됨", "변경 없음"}:
        raise NotionJobMigrationError("Unsupported Jobs change status.")

    related_urls = tuple(
        dict.fromkeys((*observation.related_urls, *planned.related_urls))
    )
    review_note_parts = [observation.classification_basis.strip()]
    review_note_parts.extend(flag.strip() for flag in observation.review_flags if flag.strip())
    review_note = "\n\n".join(part for part in review_note_parts if part)
    properties: dict[str, object] = {
        JOB_TITLE: {
            "title": _text_objects(observation.original_title)
        },
        JOB_EMPLOYER: _rich_text(observation.employer_name),
        JOB_RECOGNIZED_ROLE: _rich_text(observation.recognized_role),
        JOB_DOMAIN: {"select": {"name": observation.domain.value}},
        JOB_REVIEW_STATUS: {
            "select": {"name": notion_job_review_status_name(planned.status)}
        },
        JOB_EXPERIENCE_LEVEL: {
            "select": {"name": JOB_EXPERIENCE_LEVEL_TO_NOTION[observation.experience_level]}
        },
        JOB_RESPONSIBILITIES: _rich_text(_joined(observation.responsibilities)),
        JOB_REQUIREMENTS: _rich_text(_joined(observation.requirements)),
        JOB_TECHNOLOGY_KEYWORDS: {
            "multi_select": [
                {"name": value} for value in observation.technology_keywords
            ]
        },
        JOB_LOCATION: _rich_text(observation.location),
        JOB_EMPLOYMENT_TYPE: {
            "select": {"name": JOB_EMPLOYMENT_TYPE_TO_NOTION[observation.employment_type]}
        },
        JOB_WORK_MODE: {
            "select": {"name": JOB_WORK_MODE_TO_NOTION[observation.work_mode]}
        },
        JOB_PUBLISHED_DATE: {
            "date": (
                {"start": observation.published_on.isoformat()}
                if observation.published_on
                else None
            )
        },
        JOB_DEADLINE: {
            "date": (
                {"start": observation.deadline.isoformat()}
                if observation.deadline
                else None
            )
        },
        JOB_POSTING_STATUS: {
            "select": {"name": JOB_POSTING_STATUS_TO_NOTION[observation.posting_status]}
        },
        JOB_INTEREST_STATUS: {"select": {"name": interest_status}},
        JOB_SOURCE_TYPE: {
            "select": {"name": JOB_SOURCE_TYPE_TO_NOTION[observation.source_type]}
        },
        JOB_ORIGINAL_URL: {"url": observation.canonical_url or observation.source_url},
        JOB_RELATED_URLS: _rich_text(_joined(related_urls)),
        JOB_PUBLISHED_DATE_STATUS: {
            "select": {
                "name": (
                    "확인"
                    if observation.published_on and published_date_verified
                    else "미확인"
                )
            }
        },
        JOB_POSTING_ID: _rich_text(observation.platform_job_id or ""),
        JOB_SEARCH_ROUTES: {
            "multi_select": [
                {"name": route.value} for route in observation.search_routes
            ]
        },
        JOB_COLLECTED_DATE: {"date": {"start": observation.collected_on.isoformat()}},
        JOB_LAST_CHECKED_DATE: {
            "date": {"start": (last_checked_on or observation.collected_on).isoformat()}
        },
        JOB_CHANGE_STATUS: {"select": {"name": change_status}},
        JOB_REVIEW_NOTES: _rich_text(review_note),
    }
    return NotionJobPage(
        observation.canonical_url or observation.source_url,
        properties,
    )


def _legacy_observation(item: LegacyRoleMigrationInput) -> JobObservation:
    if item.source_url is None:
        raise NotionJobMigrationError("A concept-only Role cannot become a Jobs row.")
    if not item.page_id.strip():
        raise NotionJobMigrationError("Legacy Role page ID must not be blank.")
    preserved_notes = "\n\n".join(
        part.strip()
        for part in (item.role_description, item.legacy_notes, item.evidence_sources)
        if part.strip()
    )
    return JobObservation(
        source_name="Legacy Roles migration",
        source_type=item.source_type,
        source_url=item.source_url,
        employer_name=item.employer_name,
        original_title=item.role_name,
        recognized_role=item.recognized_role,
        domain=item.domain,
        classification_basis=item.role_description,
        responsibilities=item.responsibilities,
        requirements=(),
        technology_keywords=item.technology_keywords,
        location=item.location,
        job_market="South Korea",
        experience_level=item.experience_level,
        employment_type=EmploymentType.UNKNOWN,
        work_mode=WorkMode.UNKNOWN,
        published_on=item.published_on,
        deadline=None,
        posting_status=PostingStatus.UNKNOWN,
        collected_on=item.first_discovered_on,
        search_routes=item.search_routes,
        platform_job_id=item.posting_id,
        related_urls=item.related_urls,
        review_flags=(preserved_notes,),
    )


def plan_notion_job_migration(
    legacy_roles: tuple[LegacyRoleMigrationInput, ...],
    *,
    trends_row_count: int,
) -> NotionJobMigrationPlan:
    """Build a no-write migration plan and refuse unsafe Trends conversion."""

    if trends_row_count != 0:
        raise NotionJobMigrationError(
            "Trends relation conversion requires an empty data source."
        )
    seen_pages: set[str] = set()
    pages: list[NotionJobPage] = []
    archive_only: list[str] = []
    for item in legacy_roles:
        if item.page_id in seen_pages:
            raise NotionJobMigrationError("Legacy Role page IDs must be unique.")
        seen_pages.add(item.page_id)
        if item.source_url is None:
            archive_only.append(item.page_id)
            continue
        observation = _legacy_observation(item)
        planned = PlannedJob(
            observation=observation,
            status=ReviewStatus.NEEDS_REVIEW,
            reasons=(ReviewReason.EVIDENCE_FLAGGED,),
        )
        pages.append(
            build_notion_job_page(
                planned,
                last_checked_on=item.last_reviewed_on,
                published_date_verified=False,
            )
        )
    return NotionJobMigrationPlan(
        jobs_schema=jobs_schema_ddl(),
        trends_schema_statements=trends_schema_migration_statements(),
        job_pages=tuple(pages),
        archived_role_page_ids=tuple(archive_only),
    )
