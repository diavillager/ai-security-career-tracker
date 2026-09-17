"""Deterministic validation for Trend classification and role relations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Protocol, TypeVar

from .role_discovery import Category, normalize_role_name


class ClassificationValidationError(ValueError):
    """Raised when a Trend classification is incomplete or inconsistent."""


class TrendSourceType(StrEnum):
    """Source types defined by the product requirements."""

    NEWS = "News"
    INDUSTRY_MEDIA = "Industry Media"
    COMPANY_BLOG = "Company Blog"
    ENGINEERING_BLOG = "Engineering Blog"
    PRESS_RELEASE = "Press Release"
    JOB_POSTING = "Job Posting"
    OFFICIAL_DOCUMENTATION = "Official Documentation"
    RESEARCH_REPORT = "Research Report"
    NEWSLETTER = "Newsletter"
    GITHUB = "GitHub"
    PAPER = "Paper"
    CONFERENCE = "Conference"
    GOVERNMENT = "Government"
    OTHER = "Other"


class ApprovedRoleLike(Protocol):
    record_id: str
    role_name: str
    category: Category


ApprovedRoleT = TypeVar("ApprovedRoleT", bound=ApprovedRoleLike)


def validate_classification_fields(
    *,
    source_type: TrendSourceType,
    domains: tuple[Category, ...],
    related_role_names: tuple[str, ...],
    summary: str,
    key_insight: str,
    classification_basis: str,
) -> None:
    """Reject incomplete or duplicated classification output."""
    if not isinstance(source_type, TrendSourceType):
        raise ClassificationValidationError(
            "Source Type must be one of the product-defined values."
        )
    if not domains or any(not isinstance(domain, Category) for domain in domains):
        raise ClassificationValidationError(
            "Every trend needs at least one valid Domain."
        )
    if len(set(domains)) != len(domains):
        raise ClassificationValidationError("Trend Domains must not be duplicated.")
    if not related_role_names or any(not name.strip() for name in related_role_names):
        raise ClassificationValidationError(
            "Every trend needs at least one Related Role."
        )
    normalized_names = tuple(normalize_role_name(name) for name in related_role_names)
    if len(set(normalized_names)) != len(normalized_names):
        raise ClassificationValidationError(
            "Related Roles must not contain duplicate role names."
        )
    if not summary.strip() or not key_insight.strip():
        raise ClassificationValidationError(
            "Summary and Key Insight must both be non-empty."
        )
    if summary.strip() == key_insight.strip():
        raise ClassificationValidationError(
            "Summary and Key Insight must be written as separate values."
        )
    if not classification_basis.strip():
        raise ClassificationValidationError(
            "Every trend needs a classification basis for review."
        )


def resolve_related_roles(
    related_role_names: tuple[str, ...],
    approved_roles_by_name: Mapping[str, ApprovedRoleT],
) -> tuple[ApprovedRoleT, ...]:
    """Resolve every classified relation against the run-start Approved snapshot."""
    related_roles: list[ApprovedRoleT] = []
    for role_name in related_role_names:
        role = approved_roles_by_name.get(normalize_role_name(role_name))
        if role is None:
            raise ClassificationValidationError(
                "Every Related Role must be Approved in the run-start snapshot: "
                f"{role_name}"
            )
        related_roles.append(role)
    return tuple(related_roles)


def validate_domain_role_support(
    domains: tuple[Category, ...],
    related_role_categories: Sequence[Category],
) -> None:
    """Require the selected domains to be consistent with linked role categories."""
    categories = set(related_role_categories)
    supported: set[Category] = set(categories)
    if Category.AI_SECURITY in categories:
        supported.update((Category.AI, Category.SECURITY))
    if Category.AI in categories and Category.SECURITY in categories:
        supported.add(Category.AI_SECURITY)
    unsupported = tuple(domain.value for domain in domains if domain not in supported)
    if unsupported:
        raise ClassificationValidationError(
            "Every Trend Domain must be supported by its Related Roles: "
            + ", ".join(unsupported)
        )
