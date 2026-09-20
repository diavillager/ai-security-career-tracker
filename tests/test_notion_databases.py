from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SCRIPT = ROOT / "src" / "ai_security_career_tracker" / "notion_databases.py"

from ai_security_career_tracker.notion_databases import (
    LegacyNotionDatabaseConfig,
    NotionConfigurationError,
    NotionDatabaseConfig,
    load_database_config,
    load_legacy_database_config,
    migrate_database_config,
    persist_database_config,
)


CONFIG = NotionDatabaseConfig(
    project_page_url="https://notion.example/project",
    jobs_database_id="jobs-id",
    trends_database_id="trends-id",
)
LEGACY = LegacyNotionDatabaseConfig(
    project_page_url=CONFIG.project_page_url,
    roles_database_id="roles-id",
    trends_database_id=CONFIG.trends_database_id,
)


class NotionDatabaseConfigTests(unittest.TestCase):
    def test_documented_cli_saves_jobs_and_trends_pair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--config",
                    str(path),
                    "--project-page-url",
                    CONFIG.project_page_url,
                    "--jobs-database-id",
                    CONFIG.jobs_database_id,
                    "--trends-database-id",
                    CONFIG.trends_database_id,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(load_database_config(path), CONFIG)

    def test_missing_config_is_unconfigured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            loaded = load_database_config(Path(directory) / "config.toml")

        self.assertFalse(loaded.is_configured)

    def test_persist_is_idempotent_and_preserves_other_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                '[project]\ntimezone = "UTC"\n\n'
                '[search]\nprovider = "custom_provider"\n\n'
                '[notion]\nproject_page_url = ""\n'
                'jobs_database_id = ""\ntrends_database_id = ""\n',
                encoding="utf-8",
            )

            self.assertTrue(persist_database_config(path, CONFIG))
            self.assertFalse(persist_database_config(path, CONFIG))
            content = path.read_text(encoding="utf-8")

            self.assertIn('timezone = "UTC"', content)
            self.assertIn('provider = "custom_provider"', content)
            self.assertEqual(load_database_config(path), CONFIG)

    def test_different_saved_identifiers_are_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            persist_database_config(path, CONFIG)
            original = path.read_text(encoding="utf-8")

            with self.assertRaises(NotionConfigurationError):
                persist_database_config(
                    path,
                    NotionDatabaseConfig(
                        CONFIG.project_page_url,
                        "different-jobs-id",
                        CONFIG.trends_database_id,
                    ),
                )

            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_partial_jobs_pair_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                '[notion]\njobs_database_id = "jobs-id"\n'
                'trends_database_id = ""\n',
                encoding="utf-8",
            )

            with self.assertRaises(NotionConfigurationError):
                load_database_config(path)

    def test_legacy_config_cannot_be_treated_as_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                f'[notion]\nproject_page_url = "{LEGACY.project_page_url}"\n'
                f'roles_database_id = "{LEGACY.roles_database_id}"\n'
                f'trends_database_id = "{LEGACY.trends_database_id}"\n',
                encoding="utf-8",
            )

            self.assertEqual(load_legacy_database_config(path), LEGACY)
            with self.assertRaises(NotionConfigurationError):
                load_database_config(path)

    def test_verified_legacy_pair_migrates_atomically_and_preserves_trends(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                '[project]\ntimezone = "Asia/Seoul"\n\n'
                '[notion]\n'
                f'project_page_url = "{LEGACY.project_page_url}"\n'
                f'roles_database_id = "{LEGACY.roles_database_id}"\n'
                f'trends_database_id = "{LEGACY.trends_database_id}"\n',
                encoding="utf-8",
            )

            self.assertTrue(migrate_database_config(path, LEGACY, CONFIG))
            self.assertFalse(migrate_database_config(path, LEGACY, CONFIG))
            content = path.read_text(encoding="utf-8")

            self.assertNotIn("roles_database_id", content)
            self.assertIn('jobs_database_id = "jobs-id"', content)
            self.assertIn('trends_database_id = "trends-id"', content)
            self.assertEqual(load_database_config(path), CONFIG)

    def test_migration_refuses_changed_legacy_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                f'[notion]\nproject_page_url = "{LEGACY.project_page_url}"\n'
                'roles_database_id = "changed-role-id"\n'
                f'trends_database_id = "{LEGACY.trends_database_id}"\n',
                encoding="utf-8",
            )
            original = path.read_text(encoding="utf-8")

            with self.assertRaises(NotionConfigurationError):
                migrate_database_config(path, LEGACY, CONFIG)

            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_migration_refuses_trends_identifier_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                f'[notion]\nproject_page_url = "{LEGACY.project_page_url}"\n'
                f'roles_database_id = "{LEGACY.roles_database_id}"\n'
                f'trends_database_id = "{LEGACY.trends_database_id}"\n',
                encoding="utf-8",
            )

            with self.assertRaises(NotionConfigurationError):
                migrate_database_config(
                    path,
                    LEGACY,
                    NotionDatabaseConfig(
                        CONFIG.project_page_url,
                        CONFIG.jobs_database_id,
                        "different-trends-id",
                    ),
                )


if __name__ == "__main__":
    unittest.main()
