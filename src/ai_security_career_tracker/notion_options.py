"""Translate internal enum values to user-facing Notion option names."""

from __future__ import annotations

from .classification import TrendSourceType
from .job_discovery import (
    EmploymentType,
    ExperienceLevel,
    JobSourceType,
    PostingStatus,
    ReviewStatus,
    WorkMode,
)
from .role_discovery import RoleStatus


ROLE_STATUS_TO_NOTION = {
    RoleStatus.CANDIDATE: "후보",
    RoleStatus.APPROVED: "승인",
    RoleStatus.REJECTED: "거절",
}

TREND_SOURCE_TYPE_TO_NOTION = {
    TrendSourceType.NEWS: "뉴스",
    TrendSourceType.INDUSTRY_MEDIA: "업계 매체",
    TrendSourceType.COMPANY_BLOG: "기업 블로그",
    TrendSourceType.ENGINEERING_BLOG: "기술 블로그",
    TrendSourceType.PRESS_RELEASE: "보도자료",
    TrendSourceType.JOB_POSTING: "채용 공고",
    TrendSourceType.OFFICIAL_DOCUMENTATION: "공식 문서",
    TrendSourceType.RESEARCH_REPORT: "연구 보고서",
    TrendSourceType.NEWSLETTER: "뉴스레터",
    TrendSourceType.GITHUB: "GitHub",
    TrendSourceType.PAPER: "논문",
    TrendSourceType.CONFERENCE: "컨퍼런스",
    TrendSourceType.GOVERNMENT: "정부",
    TrendSourceType.OTHER: "기타",
}

JOB_REVIEW_STATUS_TO_NOTION = {
    ReviewStatus.ELIGIBLE: "적합",
    ReviewStatus.NEEDS_REVIEW: "검토 필요",
}

JOB_EXPERIENCE_LEVEL_TO_NOTION = {
    ExperienceLevel.ENTRY: "신입",
    ExperienceLevel.EXPERIENCED: "경력",
    ExperienceLevel.BOTH: "신입·경력",
    ExperienceLevel.UNKNOWN: "미확인",
}

JOB_EMPLOYMENT_TYPE_TO_NOTION = {
    EmploymentType.FULL_TIME: "정규직",
    EmploymentType.CONTRACT: "계약직",
    EmploymentType.INTERN: "인턴",
    EmploymentType.OTHER: "기타",
    EmploymentType.UNKNOWN: "미확인",
}

JOB_WORK_MODE_TO_NOTION = {
    WorkMode.ONSITE: "출근",
    WorkMode.HYBRID: "하이브리드",
    WorkMode.REMOTE: "원격",
    WorkMode.UNKNOWN: "미확인",
}

JOB_POSTING_STATUS_TO_NOTION = {
    PostingStatus.OPEN: "모집 중",
    PostingStatus.CLOSED: "마감",
    PostingStatus.UNKNOWN: "미확인",
}

JOB_SOURCE_TYPE_TO_NOTION = {
    JobSourceType.EMPLOYER: "기업 공식",
    JobSourceType.SARAMIN: "Saramin",
    JobSourceType.JOBKOREA: "JobKorea",
    JobSourceType.WANTED: "Wanted",
    JobSourceType.JUMPIT: "Jumpit",
    JobSourceType.OTHER: "기타",
}

_NOTION_TO_ROLE_STATUS = {
    notion_name: status for status, notion_name in ROLE_STATUS_TO_NOTION.items()
}
_NOTION_TO_ROLE_STATUS.update({status.value: status for status in RoleStatus})
_NOTION_TO_TREND_SOURCE_TYPE = {
    notion_name: source_type
    for source_type, notion_name in TREND_SOURCE_TYPE_TO_NOTION.items()
}
_NOTION_TO_TREND_SOURCE_TYPE.update(
    {source_type.value: source_type for source_type in TrendSourceType}
)


def notion_role_status_name(status: RoleStatus) -> str:
    """Return the localized Notion option for an internal role status."""

    return ROLE_STATUS_TO_NOTION[status]


def role_status_from_notion(value: str) -> RoleStatus:
    """Convert a localized or legacy Notion role status into the internal enum."""

    return _NOTION_TO_ROLE_STATUS[value]


def notion_trend_source_type_name(source_type: TrendSourceType) -> str:
    """Return the localized Notion option for an internal trend source type."""

    return TREND_SOURCE_TYPE_TO_NOTION[source_type]


def trend_source_type_from_notion(value: str) -> TrendSourceType:
    """Convert a localized or legacy Notion source type into the internal enum."""

    return _NOTION_TO_TREND_SOURCE_TYPE[value]


def notion_job_review_status_name(status: ReviewStatus) -> str:
    """Return a storable Jobs review status; excluded jobs are report-only."""

    try:
        return JOB_REVIEW_STATUS_TO_NOTION[status]
    except KeyError as error:
        raise ValueError("Excluded jobs must not be stored in Jobs DB.") from error
