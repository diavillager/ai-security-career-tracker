from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.role_discovery import (
    Category,
    DiscoveryValidationError,
    EvidenceSource,
    ExistingRole,
    RoleObservation,
    RoleStatus,
    RESPONSIBILITY_TERMS,
    SEEDS,
    build_search_plan,
    default_period,
    normalize_role_name,
    select_new_candidates,
)


def observation(
    role_name: str = "Agent Security Engineer",
    category: Category = Category.AI_SECURITY,
    source_url: str = "https://careers.example/roles/agent-security",
    include_supporting_source: bool = True,
) -> RoleObservation:
    sources = [EvidenceSource("Example Careers", source_url, date(2026, 9, 14))]
    if include_supporting_source:
        sources.append(
            EvidenceSource(
                "Example Engineering",
                "https://engineering.example/agent-security-context",
                date(2026, 9, 15),
            )
        )
    return RoleObservation(
        role_name=role_name,
        suggested_category=category,
        description="Secures agent tools, identities, and runtime boundaries.",
        key_responsibilities=("Threat model agent tool use", "Design sandbox controls"),
        required_skills=("Python", "Threat modeling"),
        team_description="Agent Security team",
        product_context="Agent execution platform",
        discovery_reason="Responsibilities combine agent infrastructure and product security.",
        evidence_sources=tuple(sources),
    )


class RoleDiscoveryTests(unittest.TestCase):
    def test_default_period_is_seven_inclusive_days(self) -> None:
        period = default_period(date(2026, 9, 15))

        self.assertEqual(period.start, date(2026, 9, 9))
        self.assertEqual(period.end, date(2026, 9, 15))

    def test_search_plan_contains_all_three_domains(self) -> None:
        plan = build_search_plan(default_period(date(2026, 9, 15)))

        self.assertEqual({query.category for query in plan}, set(Category))
        self.assertTrue(all("responsibilities" in query.query for query in plan))

    def test_search_vocabulary_includes_every_prd_seed_and_term(self) -> None:
        expected_seeds = {
            "Applied AI Engineer",
            "AI Agent Engineer",
            "Agent Engineer",
            "LLM Engineer",
            "Generative AI Engineer",
            "AI Platform Engineer",
            "Agent Platform Engineer",
            "Agent Infrastructure Engineer",
            "AI Evaluation Engineer",
            "Product Security Engineer",
            "Application Security Engineer",
            "Cloud Security Engineer",
            "Security Platform Engineer",
            "IAM Engineer",
            "Security Engineer",
            "AI Security Engineer",
            "Agent Security Engineer",
            "GenAI Security Engineer",
            "LLM Security Engineer",
            "AI Product Security",
            "AI Platform Security",
        }
        expected_terms = {
            "agent",
            "tool use",
            "RAG",
            "evaluation",
            "model serving",
            "orchestration",
            "observability",
            "IAM",
            "authorization",
            "OAuth",
            "OIDC",
            "sandbox",
            "threat modeling",
            "workload identity",
            "policy enforcement",
            "audit logging",
            "data governance",
            "Zero Trust",
        }

        actual_seeds = {value for values in SEEDS.values() for value in values}
        actual_terms = {
            value for values in RESPONSIBILITY_TERMS.values() for value in values
        }

        self.assertTrue(expected_seeds <= actual_seeds)
        self.assertTrue(expected_terms <= actual_terms)

    def test_role_name_normalization_is_not_semantic(self) -> None:
        self.assertEqual(
            normalize_role_name("  AGENT   Security Engineer  "),
            normalize_role_name("Agent Security Engineer"),
        )
        self.assertNotEqual(
            normalize_role_name("Agent Security Engineer"),
            normalize_role_name("AI Security Engineer"),
        )

    def test_existing_roles_in_every_status_block_new_candidate(self) -> None:
        observations = tuple(
            observation(f"Existing {status.value}") for status in RoleStatus
        )
        existing = tuple(
            ExistingRole(f"existing {status.value}", status) for status in RoleStatus
        )

        outcome = select_new_candidates(
            observations,
            existing,
            date(2026, 9, 15),
            default_period(date(2026, 9, 15)),
        )

        self.assertEqual(outcome.new_candidates, ())
        self.assertEqual(
            {match.existing_status for match in outcome.existing_matches}, set(RoleStatus)
        )

    def test_new_role_is_always_candidate(self) -> None:
        outcome = select_new_candidates(
            (observation(),),
            (),
            date(2026, 9, 15),
            default_period(date(2026, 9, 15)),
        )

        candidate = outcome.new_candidates[0]
        self.assertEqual(candidate.status, RoleStatus.CANDIDATE)
        self.assertEqual(candidate.first_discovered, date(2026, 9, 15))
        self.assertEqual(candidate.last_reviewed, date(2026, 9, 15))

    def test_same_run_observations_merge_distinct_evidence(self) -> None:
        outcome = select_new_candidates(
            (
                observation(
                    source_url="https://careers.example/one",
                    include_supporting_source=False,
                ),
                observation(
                    source_url="https://engineering.example/agent-security",
                    include_supporting_source=False,
                ),
            ),
            (),
            date(2026, 9, 15),
            default_period(date(2026, 9, 15)),
        )

        self.assertEqual(len(outcome.new_candidates), 1)
        self.assertEqual(len(outcome.new_candidates[0].evidence_sources), 2)

    def test_candidate_requires_two_distinct_evidence_sources(self) -> None:
        with self.assertRaises(DiscoveryValidationError):
            select_new_candidates(
                (observation(include_supporting_source=False),),
                (),
                date(2026, 9, 15),
                default_period(date(2026, 9, 15)),
            )

    def test_source_outside_search_period_is_rejected(self) -> None:
        item = observation()
        old_source = EvidenceSource(
            "Old source",
            "https://careers.example/old-role",
            date(2026, 9, 8),
        )
        outside_period = RoleObservation(
            role_name=item.role_name,
            suggested_category=item.suggested_category,
            description=item.description,
            key_responsibilities=item.key_responsibilities,
            required_skills=item.required_skills,
            team_description=item.team_description,
            product_context=item.product_context,
            discovery_reason=item.discovery_reason,
            evidence_sources=(item.evidence_sources[0], old_source),
        )

        with self.assertRaises(DiscoveryValidationError):
            select_new_candidates(
                (outside_period,),
                (),
                date(2026, 9, 15),
                default_period(date(2026, 9, 15)),
            )

    def test_conflicting_categories_require_review(self) -> None:
        with self.assertRaises(DiscoveryValidationError):
            select_new_candidates(
                (
                    observation(category=Category.AI),
                    observation(category=Category.AI_SECURITY),
                ),
                (),
                date(2026, 9, 15),
                default_period(date(2026, 9, 15)),
            )

    def test_evidence_requires_original_web_url(self) -> None:
        with self.assertRaises(DiscoveryValidationError):
            EvidenceSource("Example", "not-a-url", date(2026, 9, 15))


if __name__ == "__main__":
    unittest.main()
