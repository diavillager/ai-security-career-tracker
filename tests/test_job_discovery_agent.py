from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.job_discovery import (
    JOB_DISCOVERY_AGENT_BY_DOMAIN,
    JOB_EVIDENCE_REVIEWER,
)


class JobDiscoveryAgentConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agents_dir = ROOT / ".codex" / "agents"

    def _load(self, name: str) -> dict[str, object]:
        with (self.agents_dir / f"{name}.toml").open("rb") as handle:
            return tomllib.load(handle)

    def test_three_search_agents_and_one_reviewer_are_configured(self) -> None:
        with (ROOT / ".codex" / "config.toml").open("rb") as handle:
            config = tomllib.load(handle)
        expected = {*JOB_DISCOVERY_AGENT_BY_DOMAIN.values(), JOB_EVIDENCE_REVIEWER}
        self.assertEqual({path.stem for path in self.agents_dir.glob("*.toml")}, expected)
        self.assertTrue(config["agents"]["enabled"])
        self.assertEqual(config["agents"]["max_concurrent_threads_per_session"], 3)

    def test_all_agents_are_read_only_and_use_live_search(self) -> None:
        for name in (*JOB_DISCOVERY_AGENT_BY_DOMAIN.values(), JOB_EVIDENCE_REVIEWER):
            with self.subTest(agent=name):
                agent = self._load(name)
                self.assertEqual(agent["name"], name)
                self.assertEqual(agent["model"], "gpt-5.6-terra")
                self.assertEqual(agent["model_reasoning_effort"], "high")
                self.assertEqual(agent["sandbox_mode"], "read-only")
                self.assertEqual(agent["web_search"], "live")

    def test_search_agents_use_job_contract_without_domain_allowlist(self) -> None:
        for name in JOB_DISCOVERY_AGENT_BY_DOMAIN.values():
            instructions = self._load(name)["developer_instructions"]
            with self.subTest(agent=name):
                self.assertIn("job-discovery-agent-contract.md", instructions)
                self.assertIn("허용 목록이 아닙니다", instructions)
                self.assertIn("두 번째 근거", instructions)
                self.assertIn("Notion이나 프로젝트 파일을 수정", instructions)

    def test_reviewer_is_sequential_and_does_not_make_final_decisions(self) -> None:
        instructions = self._load(JOB_EVIDENCE_REVIEWER)["developer_instructions"]
        self.assertIn("job-evidence-reviewer-contract.md", instructions)
        self.assertIn("최종 저장·제외 결정을 하지", instructions)
        self.assertIn("새 공고를 찾거나 observation을 추가하지", instructions)

    def test_skill_routes_the_new_agent_flow(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in JOB_DISCOVERY_AGENT_BY_DOMAIN.values():
            self.assertIn(name, skill)
        for text in (
            "build_job_search_tasks",
            "parse_job_agent_result",
            JOB_EVIDENCE_REVIEWER,
            "parse_job_evidence_review",
            "consolidate_job_agent_results",
            "두 번째 독립 근거를 요구하지",
            "기존 Roles DB에 쓰거나 Candidate 승인·거절 흐름으로 보내지 않습니다",
        ):
            self.assertIn(text, skill)

        contract = (ROOT / "references" / "job-discovery-agent-contract.md").read_text(encoding="utf-8")
        reviewer = (ROOT / "references" / "job-evidence-reviewer-contract.md").read_text(encoding="utf-8")
        for text in ("source_coverage", "search_queries_run", "published_on: null", "하나의 JSON 객체만"):
            self.assertIn(text, contract)
        for text in ("source_access_failure", "possible_duplicate", "해당 공고에만 flag", "하나의 JSON 객체만"):
            self.assertIn(text, reviewer)


if __name__ == "__main__":
    unittest.main()
