from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.role_discovery import (
    ROLE_EVIDENCE_REVIEWER,
    ROLE_DISCOVERY_AGENT_BY_CATEGORY,
)


class RoleDiscoveryAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agents_dir = ROOT / ".codex" / "agents"

    def _load_agent(self, agent_name: str) -> dict[str, object]:
        with (self.agents_dir / f"{agent_name}.toml").open("rb") as agent_file:
            return tomllib.load(agent_file)

    def test_three_domain_agents_and_sequential_reviewer_are_configured(self) -> None:
        with (ROOT / ".codex" / "config.toml").open("rb") as config_file:
            config = tomllib.load(config_file)

        expected_names = {
            *ROLE_DISCOVERY_AGENT_BY_CATEGORY.values(),
            ROLE_EVIDENCE_REVIEWER,
        }
        actual_names = {path.stem for path in self.agents_dir.glob("*.toml")}

        self.assertTrue(config["agents"]["enabled"])
        self.assertEqual(config["agents"]["max_concurrent_threads_per_session"], 3)
        self.assertEqual(actual_names, expected_names)

    def test_evidence_reviewer_is_read_only_and_bounded(self) -> None:
        reviewer = self._load_agent(ROLE_EVIDENCE_REVIEWER)
        instructions = reviewer["developer_instructions"]

        self.assertEqual(reviewer["model"], "gpt-5.6-terra")
        self.assertEqual(reviewer["model_reasoning_effort"], "high")
        self.assertEqual(reviewer["sandbox_mode"], "read-only")
        self.assertEqual(reviewer["web_search"], "live")
        self.assertIn("role-evidence-reviewer-contract.md", instructions)
        self.assertIn("Candidate 여부를 결정", instructions)
        self.assertIn("Notion이나 프로젝트 파일을 수정", instructions)
        self.assertIn("다른 Agent를 시작", instructions)

    def test_each_agent_is_read_only_and_uses_live_web_search(self) -> None:
        for agent_name in ROLE_DISCOVERY_AGENT_BY_CATEGORY.values():
            with self.subTest(agent=agent_name):
                agent = self._load_agent(agent_name)

                self.assertEqual(agent["name"], agent_name)
                self.assertEqual(agent["model"], "gpt-5.6-terra")
                self.assertEqual(agent["model_reasoning_effort"], "high")
                self.assertEqual(agent["sandbox_mode"], "read-only")
                self.assertEqual(agent["web_search"], "live")

    def test_each_agent_uses_the_shared_contract_and_stays_in_its_domain(self) -> None:
        expected_domain_text = {
            "ai_role_researcher": "AI 영역 조사만",
            "security_role_researcher": "Security 영역 조사만",
            "ai_security_role_researcher": "AI × Security 영역 조사만",
        }

        for agent_name, domain_text in expected_domain_text.items():
            with self.subTest(agent=agent_name):
                instructions = self._load_agent(agent_name)["developer_instructions"]

                self.assertIn("references/role-discovery-agent-contract.md", instructions)
                self.assertIn(domain_text, instructions)
                self.assertIn("Notion이나 프로젝트 파일을 수정", instructions)
                self.assertIn("다른 Agent를 시작", instructions)
                self.assertIn("Trend Update", instructions)

    def test_shared_contract_keeps_parent_workflow_in_control(self) -> None:
        contract = (
            ROOT / "references" / "role-discovery-agent-contract.md"
        ).read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        contract_requirements = (
            "run_id",
            "existing_roles",
            "South Korea",
            "Published Date",
            "Experience Level",
            "select_new_candidates",
            "세 영역 결과가 모두 성공",
            "하나의 JSON 객체만",
            "`required_skills`를 각각 1개 이상",
            "독립된 근거 2개 이상",
            "`employer_name`",
            "하나의 독립 근거로 셉니다",
            "`exclusions`에 `other`",
        )
        for requirement in contract_requirements:
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, contract)

        for agent_name in ROLE_DISCOVERY_AGENT_BY_CATEGORY.values():
            with self.subTest(skill_agent=agent_name):
                self.assertIn(agent_name, skill)
        self.assertIn("병렬로 시작", skill)
        self.assertIn(ROLE_EVIDENCE_REVIEWER, skill)
        self.assertIn("parse_role_evidence_review_result", skill)
        self.assertIn("validate_role_evidence_review", skill)
        self.assertIn("consolidate_agent_results", skill)

        reviewer_contract = (
            ROOT / "references" / "role-evidence-reviewer-contract.md"
        ).read_text(encoding="utf-8")
        for requirement in (
            "source_access_failure",
            "source_independence",
            "semantic_duplicate",
            "category_ambiguity",
            "하나의 JSON 객체만",
            "자동 승인·거절",
        ):
            with self.subTest(reviewer_requirement=requirement):
                self.assertIn(requirement, reviewer_contract)


if __name__ == "__main__":
    unittest.main()
