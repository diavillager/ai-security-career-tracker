from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RoleDiscoveryAgentTests(unittest.TestCase):
    def test_agent_configuration_is_valid_toml(self) -> None:
        with (ROOT / ".codex" / "config.toml").open("rb") as config_file:
            config = tomllib.load(config_file)

        with (
            ROOT / ".codex" / "agents" / "role_discovery.toml"
        ).open("rb") as agent_file:
            agent = tomllib.load(agent_file)

        self.assertEqual(config["agents"]["max_concurrent_threads_per_session"], 1)
        self.assertEqual(agent["name"], "role_discovery")
        self.assertEqual(agent["sandbox_mode"], "read-only")
        self.assertEqual(agent["model_reasoning_effort"], "high")

    def test_agent_instructions_keep_role_discovery_boundaries(self) -> None:
        with (
            ROOT / ".codex" / "agents" / "role_discovery.toml"
        ).open("rb") as agent_file:
            instructions = tomllib.load(agent_file)["developer_instructions"]

        required_phrases = (
            "references/role-discovery.md",
            "대한민국",
            "Published Date",
            "Experience Level",
            "Candidate",
            "Approved",
            "Rejected",
            "Notion을 생성하거나 수정하지 마세요",
            "Trend Update를 실행하거나 Trends DB에 쓰지 마세요",
        )

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, instructions)


if __name__ == "__main__":
    unittest.main()
