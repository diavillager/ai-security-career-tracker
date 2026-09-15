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
    NotionConfigurationError,
    NotionDatabaseConfig,
    load_database_config,
    persist_database_config,
)


CONFIG = NotionDatabaseConfig(
    project_page_url="https://notion.example/project",
    roles_database_id="roles-id",
    trends_database_id="trends-id",
)


class NotionDatabaseConfigTests(unittest.TestCase):
    def test_documented_cli_runs_from_project_root(self) -> None:
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
                    "--roles-database-id",
                    CONFIG.roles_database_id,
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

    def test_persist_and_reload_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"

            self.assertTrue(persist_database_config(path, CONFIG))
            self.assertEqual(load_database_config(path), CONFIG)

    def test_repeated_persist_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            persist_database_config(path, CONFIG)

            self.assertFalse(persist_database_config(path, CONFIG))

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
                        "different-roles-id",
                        CONFIG.trends_database_id,
                    ),
                )

            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_existing_non_notion_settings_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                '[project]\ntimezone = "UTC"\n\n'
                '[search]\nprovider = "custom_provider"\n\n'
                '[notion]\nproject_page_url = ""\n'
                'roles_database_id = ""\ntrends_database_id = ""\n',
                encoding="utf-8",
            )

            persist_database_config(path, CONFIG)
            content = path.read_text(encoding="utf-8")

            self.assertIn('timezone = "UTC"', content)
            self.assertIn('provider = "custom_provider"', content)
            self.assertEqual(load_database_config(path), CONFIG)

    def test_partial_identifier_pair_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                '[notion]\nroles_database_id = "roles-id"\n'
                'trends_database_id = ""\n',
                encoding="utf-8",
            )

            with self.assertRaises(NotionConfigurationError):
                load_database_config(path)


if __name__ == "__main__":
    unittest.main()
