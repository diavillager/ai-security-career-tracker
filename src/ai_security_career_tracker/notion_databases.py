"""Validate and persist reusable Notion database identifiers."""

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
    roles_database_id: str
    trends_database_id: str

    @property
    def is_configured(self) -> bool:
        return bool(self.roles_database_id and self.trends_database_id)


def load_database_config(path: Path) -> NotionDatabaseConfig:
    """Load configuration and reject partial database identifier pairs."""
    if not path.exists():
        return NotionDatabaseConfig("", "", "")

    with path.open("rb") as config_file:
        notion = tomllib.load(config_file).get("notion", {})

    config = NotionDatabaseConfig(
        project_page_url=str(notion.get("project_page_url", "")).strip(),
        roles_database_id=str(notion.get("roles_database_id", "")).strip(),
        trends_database_id=str(notion.get("trends_database_id", "")).strip(),
    )
    if bool(config.roles_database_id) != bool(config.trends_database_id):
        raise NotionConfigurationError(
            "Roles DB and Trends DB identifiers must be saved together. "
            "Inspect the existing Notion page instead of creating a replacement."
        )
    return config


def persist_database_config(path: Path, config: NotionDatabaseConfig) -> bool:
    """Create a local config once; refuse to replace different saved identifiers."""
    values = (
        config.project_page_url,
        config.roles_database_id,
        config.trends_database_id,
    )
    if not all(value.strip() for value in values):
        raise NotionConfigurationError(
            "Project page URL and both database identifiers are required."
        )

    existing = load_database_config(path)
    if existing.is_configured:
        if existing != config:
            raise NotionConfigurationError(
                "Different database identifiers are already saved. "
                "Verify the existing databases instead of replacing them."
            )
        return False

    if path.exists() and existing.project_page_url:
        if existing.project_page_url != config.project_page_url:
            raise NotionConfigurationError(
                "A different project page is already configured."
            )

    def toml_string(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    replacements = {
        "project_page_url": toml_string(config.project_page_url),
        "roles_database_id": toml_string(config.roles_database_id),
        "trends_database_id": toml_string(config.trends_database_id),
    }
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
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
        for index in range(section_start + 1, section_end):
            stripped = lines[index].lstrip()
            key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
            if key in replacements:
                indentation = lines[index][: len(lines[index]) - len(stripped)]
                lines[index] = f"{indentation}{key} = {replacements[key]}"
                found.add(key)

        missing = [key for key in replacements if key not in found]
        lines[section_end:section_end] = [
            f"{key} = {replacements[key]}" for key in missing
        ]
        content = "\n".join(lines).rstrip() + "\n"
    else:
        content = (
            '[project]\n'
            'name = "AI Security Career Tracker"\n'
            'timezone = "Asia/Seoul"\n'
            'default_search_days = 7\n\n'
            '[search]\n'
            'provider = "codex_web"\n\n'
            '[notion]\n'
            f'project_page_url = {replacements["project_page_url"]}\n'
            f'roles_database_id = {replacements["roles_database_id"]}\n'
            f'trends_database_id = {replacements["trends_database_id"]}\n'
        )
    path.write_text(content, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Save verified Notion database identifiers to local config."
    )
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--project-page-url", required=True)
    parser.add_argument("--roles-database-id", required=True)
    parser.add_argument("--trends-database-id", required=True)
    args = parser.parse_args()

    changed = persist_database_config(
        args.config,
        NotionDatabaseConfig(
            project_page_url=args.project_page_url,
            roles_database_id=args.roles_database_id,
            trends_database_id=args.trends_database_id,
        ),
    )
    print("Saved Notion database identifiers." if changed else "Identifiers already match.")


if __name__ == "__main__":
    main()
