from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProjectFoundationTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        required = (
            "SKILL.md",
            "agents/openai.yaml",
            "config.example.toml",
            "references/product-requirements.md",
        )

        for relative_path in required:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_skill_frontmatter_uses_expected_name(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertTrue(content.startswith("---\n"))
        self.assertIn("\nname: ai-security-career-tracker\n", content)
        self.assertIn("\ndescription:", content)

    def test_default_configuration_matches_confirmed_decisions(self) -> None:
        with (ROOT / "config.example.toml").open("rb") as config_file:
            config = tomllib.load(config_file)

        self.assertEqual(config["project"]["timezone"], "Asia/Seoul")
        self.assertEqual(config["project"]["default_search_days"], 7)
        self.assertEqual(config["search"]["provider"], "codex_web")

    def test_database_identifiers_are_not_in_example_config(self) -> None:
        with (ROOT / "config.example.toml").open("rb") as config_file:
            notion = tomllib.load(config_file)["notion"]

        self.assertEqual(notion["roles_database_id"], "")
        self.assertEqual(notion["trends_database_id"], "")

    def test_private_local_config_is_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

        self.assertIn(".env", ignored)
        self.assertIn("config.toml", ignored)


if __name__ == "__main__":
    unittest.main()
