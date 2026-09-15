from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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
