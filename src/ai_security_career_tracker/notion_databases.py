"""Validate, migrate, and persist reusable Notion data source identifiers."""

from __future__ import annotations

import argparse
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path


class NotionConfigurationError(ValueError):
    """Raised when local Notion identifiers are unsafe to use or replace."""


@dataclass(frozen=True)
class NotionDatabaseConfig:
    project_page_url: str
    jobs_database_id: str
    trends_database_id: str

    @property
    def is_configured(self) -> bool:
        return bool(self.jobs_database_id and self.trends_database_id)


@dataclass(frozen=True)
class LegacyNotionDatabaseConfig:
    project_page_url: str
    roles_database_id: str
    trends_database_id: str

    @property
    def is_configured(self) -> bool:
        return bool(self.roles_database_id and self.trends_database_id)


def _notion_table(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    with path.open("rb") as config_file:
        notion = tomllib.load(config_file).get("notion", {})
    if not isinstance(notion, dict):
        raise NotionConfigurationError("The [notion] section must be a table.")
    return notion


def _value(notion: dict[str, object], key: str) -> str:
    return str(notion.get(key, "")).strip()


def load_database_config(path: Path) -> NotionDatabaseConfig:
    """Load only the Jobs-era identifier pair and reject mixed generations."""

    notion = _notion_table(path)
    jobs_id = _value(notion, "jobs_database_id")
    trends_id = _value(notion, "trends_database_id")
    roles_id = _value(notion, "roles_database_id")
    if roles_id:
        raise NotionConfigurationError(
            "Legacy roles_database_id is still configured. Run the verified "
            "Roles-to-Jobs migration instead of treating it as Jobs DB."
        )
    if bool(jobs_id) != bool(trends_id):
        raise NotionConfigurationError(
            "Jobs DB and Trends DB identifiers must be saved together."
        )
    return NotionDatabaseConfig(
        project_page_url=_value(notion, "project_page_url"),
        jobs_database_id=jobs_id,
        trends_database_id=trends_id,
    )


def load_legacy_database_config(path: Path) -> LegacyNotionDatabaseConfig:
    """Read the exact legacy pair without allowing Jobs-era mixed state."""

    notion = _notion_table(path)
    roles_id = _value(notion, "roles_database_id")
    trends_id = _value(notion, "trends_database_id")
    jobs_id = _value(notion, "jobs_database_id")
    if jobs_id:
        raise NotionConfigurationError(
            "jobs_database_id is already present; legacy migration is not applicable."
        )
    if bool(roles_id) != bool(trends_id):
        raise NotionConfigurationError(
            "Legacy Roles DB and Trends DB identifiers must be saved together."
        )
    return LegacyNotionDatabaseConfig(
        project_page_url=_value(notion, "project_page_url"),
        roles_database_id=roles_id,
        trends_database_id=trends_id,
    )


def _render_config(
    path: Path,
    replacements: dict[str, str],
    *,
    remove_keys: set[str] | None = None,
) -> str:
    def toml_string(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    rendered = {key: toml_string(value) for key, value in replacements.items()}
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    section_start = next(
        (index for index, line in enumerate(lines) if line.strip() == "[notion]"),
        None,
    )
    if section_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("[notion]")
        section_start = len(lines) - 1
    section_end = next(
        (
            index
            for index in range(section_start + 1, len(lines))
            if lines[index].strip().startswith("[")
            and lines[index].strip().endswith("]")
        ),
        len(lines),
    )
    found: set[str] = set()
    output_section: list[str] = []
    for line in lines[section_start + 1 : section_end]:
        stripped = line.lstrip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
        if remove_keys and key in remove_keys:
            continue
        if key in rendered:
            indentation = line[: len(line) - len(stripped)]
            output_section.append(f"{indentation}{key} = {rendered[key]}")
            found.add(key)
        else:
            output_section.append(line)
    output_section.extend(
        f"{key} = {rendered[key]}" for key in rendered if key not in found
    )
    lines[section_start + 1 : section_end] = output_section
    if not path.exists() and section_start == 0:
        lines[:0] = [
            '[project]',
            'name = "AI Security Career Tracker"',
            'timezone = "Asia/Seoul"',
            'default_search_days = 7',
            '',
            '[search]',
            'provider = "codex_web"',
            '',
        ]
    return "\n".join(lines).rstrip() + "\n"


def _write_atomic(path: Path, content: str) -> None:
    temporary = path.with_name(f"{path.name}.migration.tmp")
    if temporary.exists():
        raise NotionConfigurationError(
            f"Temporary migration file already exists: {temporary.name}"
        )
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def persist_database_config(path: Path, config: NotionDatabaseConfig) -> bool:
    """Save a new Jobs-era pair without replacing different identifiers."""

    values = (config.project_page_url, config.jobs_database_id, config.trends_database_id)
    if not all(value.strip() for value in values):
        raise NotionConfigurationError(
            "Project page URL and both database identifiers are required."
        )
    notion = _notion_table(path)
    if _value(notion, "roles_database_id"):
        raise NotionConfigurationError(
            "Legacy roles_database_id requires explicit migration."
        )
    existing = load_database_config(path)
    if existing.is_configured:
        if existing != config:
            raise NotionConfigurationError(
                "Different database identifiers are already saved."
            )
        return False
    if existing.project_page_url and existing.project_page_url != config.project_page_url:
        raise NotionConfigurationError("A different project page is already configured.")
    content = _render_config(
        path,
        {
            "project_page_url": config.project_page_url,
            "jobs_database_id": config.jobs_database_id,
            "trends_database_id": config.trends_database_id,
        },
    )
    _write_atomic(path, content)
    return True


def migrate_database_config(
    path: Path,
    expected_legacy: LegacyNotionDatabaseConfig,
    migrated: NotionDatabaseConfig,
) -> bool:
    """Replace the verified Roles key with Jobs while preserving Trends."""

    notion = _notion_table(path)
    if _value(notion, "jobs_database_id") and not _value(
        notion, "roles_database_id"
    ):
        if load_database_config(path) == migrated:
            return False
        raise NotionConfigurationError(
            "A different Jobs-era configuration is already saved."
        )
    current = load_legacy_database_config(path)
    if not current.is_configured or current != expected_legacy:
        raise NotionConfigurationError(
            "The current legacy identifiers do not match the verified snapshot."
        )
    if migrated.project_page_url != current.project_page_url:
        raise NotionConfigurationError("The project page must not change during migration.")
    if migrated.trends_database_id != current.trends_database_id:
        raise NotionConfigurationError("The existing Trends identifier must be preserved.")
    if not migrated.jobs_database_id.strip():
        raise NotionConfigurationError("The new Jobs identifier is required.")
    content = _render_config(
        path,
        {
            "project_page_url": migrated.project_page_url,
            "jobs_database_id": migrated.jobs_database_id,
            "trends_database_id": migrated.trends_database_id,
        },
        remove_keys={"roles_database_id"},
    )
    _write_atomic(path, content)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Save verified Jobs and Trends data source identifiers."
    )
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--project-page-url", required=True)
    parser.add_argument("--jobs-database-id", required=True)
    parser.add_argument("--trends-database-id", required=True)
    args = parser.parse_args()
    changed = persist_database_config(
        args.config,
        NotionDatabaseConfig(
            project_page_url=args.project_page_url,
            jobs_database_id=args.jobs_database_id,
            trends_database_id=args.trends_database_id,
        ),
    )
    print("Saved Notion data source identifiers." if changed else "Identifiers already match.")


if __name__ == "__main__":
    main()
