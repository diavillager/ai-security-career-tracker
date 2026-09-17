from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.role_discovery import (
    AgentDiscoveryResult,
    AgentExclusion,
    CandidateRole,
    Category,
    DiscoveryValidationError,
    EvidenceType,
    EvidenceReviewFlag,
    ExclusionReason,
    EvidenceSource,
    ExistingRole,
    ExistingRoleMatch,
    ExperienceLevel,
    PREFERRED_JOB_SOURCES,
    ROLE_EVIDENCE_REVIEWER,
    ReviewAssessment,
    ReviewFlagType,
    ReviewedRole,
    RoleObservation,
    RoleEvidenceReviewResult,
    RoleStatus,
    RESPONSIBILITY_TERMS,
    SEEDS,
    SOUTH_KOREA_JOB_MARKET,
    build_agent_search_tasks,
    build_search_plan,
    consolidate_agent_results,
    default_period,
    format_candidate_evidence_note,
    format_candidate_evidence_sources,
    group_independent_evidence,
    normalize_role_name,
    parse_agent_discovery_result,
    parse_role_evidence_review_result,
    select_new_candidates,
    validate_role_evidence_review,
)


def observation(
    role_name: str = "Agent Security Engineer",
    category: Category = Category.AI_SECURITY,
    source_url: str = "https://careers.example/roles/agent-security",
    include_supporting_source: bool = True,
    experience_level: ExperienceLevel = ExperienceLevel.EXPERIENCED,
    employer_name: str = "Example Company",
    source_name: str = "Example Careers",
) -> RoleObservation:
    sources = [
        EvidenceSource(
            source_name,
            source_url,
            date(2026, 9, 14),
            source_type=EvidenceType.JOB_POSTING,
            employer_name=employer_name,
            job_title=role_name,
            job_location="Seoul",
            job_market=SOUTH_KOREA_JOB_MARKET,
        )
    ]
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
        experience_level=experience_level,
        evidence_sources=tuple(sources),
    )


def agent_result(
    category: Category,
    *,
    run_id: str = "run-1",
    observations: tuple[RoleObservation, ...] = (),
    blockers: tuple[str, ...] = (),
    sources_checked: int = 0,
    exclusions: tuple[AgentExclusion, ...] = (),
    existing_matches: tuple[ExistingRoleMatch, ...] = (),
) -> AgentDiscoveryResult:
    agent_names = {
        Category.AI: "ai_role_researcher",
        Category.SECURITY: "security_role_researcher",
        Category.AI_SECURITY: "ai_security_role_researcher",
    }
    return AgentDiscoveryResult(
        run_id=run_id,
        agent_name=agent_names[category],
        category=category,
        search_period=default_period(date(2026, 9, 15)),
        job_market=SOUTH_KOREA_JOB_MARKET,
        sources_checked=sources_checked,
        observations=observations,
        exclusions=exclusions,
        existing_matches=existing_matches,
        blockers=blockers,
    )


class RoleDiscoveryTests(unittest.TestCase):
    def test_default_period_is_seven_inclusive_days(self) -> None:
        period = default_period(date(2026, 9, 15))

        self.assertEqual(period.start, date(2026, 9, 9))
        self.assertEqual(period.end, date(2026, 9, 15))

    def test_search_plan_contains_all_three_domains(self) -> None:
        plan = build_search_plan(default_period(date(2026, 9, 15)))

        self.assertEqual({query.category for query in plan}, set(Category))
        self.assertTrue(all(query.job_market == SOUTH_KOREA_JOB_MARKET for query in plan))
        self.assertTrue(all("채용" in query.query and "한국" in query.query for query in plan))

    def test_each_domain_is_assigned_to_a_dedicated_agent(self) -> None:
        tasks = build_agent_search_tasks(default_period(date(2026, 9, 15)))

        self.assertEqual(
            {
                task.search_query.category: task.agent_name
                for task in tasks
            },
            {
                Category.AI: "ai_role_researcher",
                Category.SECURITY: "security_role_researcher",
                Category.AI_SECURITY: "ai_security_role_researcher",
            },
        )
        self.assertEqual(len({task.agent_name for task in tasks}), 3)

    def test_complete_agent_run_is_consolidated_before_candidate_selection(self) -> None:
        results = (
            agent_result(
                Category.AI,
                sources_checked=2,
                exclusions=(
                    AgentExclusion(
                        "https://careers.example/overseas",
                        ExclusionReason.OVERSEAS,
                    ),
                ),
            ),
            agent_result(Category.SECURITY, sources_checked=3),
            agent_result(
                Category.AI_SECURITY,
                observations=(observation(),),
                sources_checked=2,
                existing_matches=(
                    ExistingRoleMatch(
                        "Existing Security Engineer",
                        "existing security engineer",
                        RoleStatus.APPROVED,
                    ),
                ),
            ),
        )

        outcome = consolidate_agent_results(
            results,
            "run-1",
            (
                ExistingRole(
                    "existing security engineer",
                    RoleStatus.APPROVED,
                ),
            ),
            date(2026, 9, 15),
            default_period(date(2026, 9, 15)),
        )

        self.assertEqual(len(outcome.new_candidates), 1)
        self.assertEqual(outcome.new_candidates[0].category, Category.AI_SECURITY)
        self.assertEqual(outcome.sources_checked, 7)
        self.assertEqual(len(outcome.exclusions), 1)
        self.assertEqual(len(outcome.existing_matches), 1)

    def test_structured_agent_payload_is_parsed_before_consolidation(self) -> None:
        payload = {
            "run_id": "run-1",
            "agent_name": "ai_role_researcher",
            "category": "AI",
            "search_period": {"start": "2026-09-09", "end": "2026-09-15"},
            "job_market": "South Korea",
            "sources_checked": 0,
            "observations": [],
            "exclusions": [],
            "existing_matches": [],
            "blockers": [],
        }

        result = parse_agent_discovery_result(json.dumps(payload, ensure_ascii=False))

        self.assertEqual(result.agent_name, "ai_role_researcher")
        self.assertEqual(result.category, Category.AI)
        self.assertEqual(result.search_period, default_period(date(2026, 9, 15)))

    def test_agent_payload_preserves_job_posting_employer_name(self) -> None:
        payload = {
            "run_id": "run-1",
            "agent_name": "ai_role_researcher",
            "category": "AI",
            "search_period": {"start": "2026-09-09", "end": "2026-09-15"},
            "job_market": "South Korea",
            "sources_checked": 1,
            "observations": [
                {
                    "role_name": "AI Developer",
                    "suggested_category": "AI",
                    "description": "AI 제품을 개발합니다.",
                    "key_responsibilities": ["AI 기능 개발"],
                    "required_skills": ["Python"],
                    "team_description": "AI 팀",
                    "product_context": "AI 서비스",
                    "discovery_reason": "국내 채용 공고에서 확인했습니다.",
                    "experience_level": "경력",
                    "evidence_sources": [
                        {
                            "name": "Example Careers",
                            "url": "https://careers.example/ai-developer",
                            "published_on": "2026-09-15",
                            "source_type": "Job Posting",
                            "employer_name": "Example Company",
                            "job_title": "AI Developer",
                            "job_location": "Seoul",
                            "job_market": "South Korea",
                        }
                    ],
                }
            ],
            "exclusions": [],
            "existing_matches": [],
            "blockers": [],
        }

        result = parse_agent_discovery_result(payload)

        self.assertEqual(
            result.observations[0].evidence_sources[0].employer_name,
            "Example Company",
        )
        self.assertEqual(
            result.observations[0].evidence_sources[0].job_title,
            "AI Developer",
        )

    def test_agent_payload_rejects_non_json_explanation(self) -> None:
        with self.assertRaises(DiscoveryValidationError):
            parse_agent_discovery_result("조사 결과입니다: {\"run_id\": \"run-1\"}")

    def test_evidence_review_payload_is_parsed_and_covers_every_role(self) -> None:
        results = (
            agent_result(
                Category.AI,
                observations=(observation("AI Agent Engineer", Category.AI),),
            ),
            agent_result(Category.SECURITY),
            agent_result(Category.AI_SECURITY),
        )
        payload = {
            "run_id": "run-1",
            "agent_name": ROLE_EVIDENCE_REVIEWER,
            "reviewed_roles": [
                {
                    "role_name": "AI Agent Engineer",
                    "assessment": "flagged",
                    "flags": [
                        {
                            "type": "source_independence",
                            "summary": "두 URL이 같은 채용 공고의 복제본입니다.",
                            "urls": [
                                "https://careers.example/roles/agent-security",
                                "https://engineering.example/agent-security-context",
                            ],
                        }
                    ],
                }
            ],
            "blockers": [],
        }

        review = parse_role_evidence_review_result(
            json.dumps(payload, ensure_ascii=False)
        )
        validated = validate_role_evidence_review(review, results, "run-1")

        self.assertEqual(validated.agent_name, ROLE_EVIDENCE_REVIEWER)
        self.assertEqual(
            validated.reviewed_roles[0].assessment,
            ReviewAssessment.FLAGGED,
        )
        self.assertEqual(
            validated.reviewed_roles[0].flags[0].flag_type,
            ReviewFlagType.SOURCE_INDEPENDENCE,
        )

    def test_evidence_review_must_cover_every_observed_role(self) -> None:
        results = (
            agent_result(
                Category.AI,
                observations=(observation("AI Agent Engineer", Category.AI),),
            ),
            agent_result(Category.SECURITY),
            agent_result(Category.AI_SECURITY),
        )
        review = RoleEvidenceReviewResult(
            run_id="run-1",
            agent_name=ROLE_EVIDENCE_REVIEWER,
            reviewed_roles=(),
        )

        with self.assertRaises(DiscoveryValidationError):
            validate_role_evidence_review(review, results, "run-1")

    def test_evidence_review_blocker_stops_validation(self) -> None:
        results = (
            agent_result(Category.AI),
            agent_result(Category.SECURITY),
            agent_result(Category.AI_SECURITY),
        )
        review = RoleEvidenceReviewResult(
            run_id="run-1",
            agent_name=ROLE_EVIDENCE_REVIEWER,
            reviewed_roles=(),
            blockers=("원문 접근 실패",),
        )

        with self.assertRaises(DiscoveryValidationError):
            validate_role_evidence_review(review, results, "run-1")

    def test_clear_evidence_review_cannot_contain_flags(self) -> None:
        with self.assertRaises(DiscoveryValidationError):
            ReviewedRole(
                role_name="AI Agent Engineer",
                assessment=ReviewAssessment.CLEAR,
                flags=(
                    EvidenceReviewFlag(
                        flag_type=ReviewFlagType.UNSUPPORTED_CLAIM,
                        summary="설명에 원문으로 확인되지 않는 주장이 있습니다.",
                        urls=("https://careers.example/roles/agent-security",),
                    ),
                ),
            )

    def test_agent_existing_match_must_agree_with_parent_snapshot(self) -> None:
        results = (
            agent_result(
                Category.AI,
                existing_matches=(
                    ExistingRoleMatch(
                        "Invented Role",
                        "Invented Role",
                        RoleStatus.APPROVED,
                    ),
                ),
            ),
            agent_result(Category.SECURITY),
            agent_result(Category.AI_SECURITY),
        )

        with self.assertRaises(DiscoveryValidationError):
            consolidate_agent_results(
                results,
                "run-1",
                (),
                date(2026, 9, 15),
                default_period(date(2026, 9, 15)),
            )

    def test_incomplete_agent_run_is_rejected(self) -> None:
        results = (
            agent_result(Category.AI),
            agent_result(Category.SECURITY),
        )

        with self.assertRaises(DiscoveryValidationError):
            consolidate_agent_results(
                results,
                "run-1",
                (),
                date(2026, 9, 15),
                default_period(date(2026, 9, 15)),
            )

    def test_results_from_different_runs_are_rejected(self) -> None:
        results = (
            agent_result(Category.AI),
            agent_result(Category.SECURITY, run_id="run-2"),
            agent_result(Category.AI_SECURITY),
        )

        with self.assertRaises(DiscoveryValidationError):
            consolidate_agent_results(
                results,
                "run-1",
                (),
                date(2026, 9, 15),
                default_period(date(2026, 9, 15)),
            )

    def test_agent_result_from_different_period_is_rejected(self) -> None:
        ai_result = agent_result(Category.AI)
        wrong_period_result = AgentDiscoveryResult(
            run_id="run-1",
            agent_name="security_role_researcher",
            category=Category.SECURITY,
            search_period=default_period(date(2026, 9, 14)),
            job_market=SOUTH_KOREA_JOB_MARKET,
            sources_checked=0,
            observations=(),
        )
        results = (
            ai_result,
            wrong_period_result,
            agent_result(Category.AI_SECURITY),
        )

        with self.assertRaises(DiscoveryValidationError):
            consolidate_agent_results(
                results,
                "run-1",
                (),
                date(2026, 9, 15),
                default_period(date(2026, 9, 15)),
            )

    def test_agent_blocker_prevents_partial_candidate_selection(self) -> None:
        results = (
            agent_result(Category.AI),
            agent_result(Category.SECURITY, blockers=("웹 검색 실패",)),
            agent_result(Category.AI_SECURITY),
        )

        with self.assertRaises(DiscoveryValidationError):
            consolidate_agent_results(
                results,
                "run-1",
                (),
                date(2026, 9, 15),
                default_period(date(2026, 9, 15)),
            )

    def test_search_plan_prioritizes_official_and_domestic_sources_without_allowlisting(self) -> None:
        plan = build_search_plan(default_period(date(2026, 9, 15)))

        self.assertEqual(
            PREFERRED_JOB_SOURCES,
            (
                "Employer career pages",
                "Saramin",
                "JobKorea",
                "Wanted",
                "Jumpit",
            ),
        )
        self.assertTrue(
            all(query.preferred_sources == PREFERRED_JOB_SOURCES for query in plan)
        )
        self.assertTrue(all("site:" not in query.query for query in plan))

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
        self.assertEqual(candidate.job_market, SOUTH_KOREA_JOB_MARKET)
        self.assertEqual(candidate.job_locations, ("Seoul",))
        self.assertEqual(candidate.experience_level, ExperienceLevel.EXPERIENCED)

    def test_entry_and_experienced_observations_merge_as_both(self) -> None:
        outcome = select_new_candidates(
            (
                observation(
                    source_url="https://careers.example/entry",
                    include_supporting_source=False,
                    experience_level=ExperienceLevel.ENTRY,
                    employer_name="Entry Company",
                ),
                observation(
                    source_url="https://careers.example/experienced",
                    include_supporting_source=False,
                    experience_level=ExperienceLevel.EXPERIENCED,
                    employer_name="Experienced Company",
                ),
            ),
            (),
            date(2026, 9, 15),
            default_period(date(2026, 9, 15)),
        )

        self.assertEqual(
            outcome.new_candidates[0].experience_level,
            ExperienceLevel.BOTH,
        )

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
                    employer_name="Another Company",
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

    def test_mirrored_job_postings_count_as_one_independent_source(self) -> None:
        with self.assertRaisesRegex(
            DiscoveryValidationError,
            "At least two independent evidence sources",
        ):
            select_new_candidates(
                (
                    observation(
                        source_url="https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=1",
                        include_supporting_source=False,
                        employer_name="(주) Beyond Data",
                    ),
                    observation(
                        source_url="https://www.jobkorea.co.kr/Recruit/GI_Read/1",
                        include_supporting_source=False,
                        employer_name="Beyond Data",
                    ),
                ),
                (),
                date(2026, 9, 15),
                default_period(date(2026, 9, 15)),
            )

    def test_candidate_keeps_every_mirror_url_and_labels_its_group(self) -> None:
        outcome = select_new_candidates(
            (
                observation(
                    role_name="AI Developer",
                    source_name="Saramin",
                    source_url="https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=1",
                    employer_name="(주) Beyond Data",
                ),
                observation(
                    role_name="AI Developer",
                    source_name="JobKorea",
                    source_url="https://www.jobkorea.co.kr/Recruit/GI_Read/1",
                    include_supporting_source=False,
                    employer_name="Beyond Data",
                ),
            ),
            (),
            date(2026, 9, 15),
            default_period(date(2026, 9, 15)),
        )

        candidate = outcome.new_candidates[0]
        groups = group_independent_evidence(
            candidate.role_name,
            candidate.evidence_sources,
        )

        self.assertEqual(len(candidate.evidence_sources), 3)
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(groups[0]), 2)
        formatted_sources = format_candidate_evidence_sources(candidate)
        self.assertIn(
            "[독립 근거 1 · 동일 공고] Saramin — https://www.saramin.co.kr",
            formatted_sources,
        )
        self.assertIn(
            "[독립 근거 1 · 동일 공고] JobKorea — https://www.jobkorea.co.kr",
            formatted_sources,
        )
        self.assertIn(
            "[독립 근거 2] Example Engineering — https://engineering.example",
            formatted_sources,
        )
        self.assertEqual(
            format_candidate_evidence_note(candidate),
            "독립 근거: 2개 / 보존 URL: 3개\n"
            "동일 공고 그룹: 독립 근거 1 (Saramin, JobKorea)",
        )

    def test_tracking_variants_of_informational_url_count_as_one_source(self) -> None:
        sources = (
            EvidenceSource(
                "Example Research",
                "https://research.example/report?id=42&utm_source=search",
                date(2026, 9, 15),
            ),
            EvidenceSource(
                "Example Research",
                "https://RESEARCH.example/report?utm_medium=email&id=42#summary",
                date(2026, 9, 15),
            ),
        )

        groups = group_independent_evidence("AI Security Engineer", sources)

        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)
        candidate = CandidateRole(
            role_name="AI Security Engineer",
            category=Category.AI_SECURITY,
            experience_level=ExperienceLevel.EXPERIENCED,
            description="Secures AI systems.",
            key_responsibilities=("Review controls",),
            discovery_reasons=("New responsibility",),
            evidence_sources=sources,
            job_locations=("Seoul",),
            job_market=SOUTH_KOREA_JOB_MARKET,
            first_discovered=date(2026, 9, 15),
            last_reviewed=date(2026, 9, 15),
        )
        self.assertIn("동일 원문", format_candidate_evidence_sources(candidate))
        self.assertIn("동일 원문 그룹", format_candidate_evidence_note(candidate))

    def test_verified_canonical_url_groups_informational_mirrors(self) -> None:
        canonical = "https://publisher.example/reports/agent-security"
        sources = (
            EvidenceSource(
                "Search Result",
                "https://search.example/result/1",
                date(2026, 9, 15),
                canonical_url=canonical,
            ),
            EvidenceSource(
                "Publisher",
                canonical,
                date(2026, 9, 15),
            ),
        )

        groups = group_independent_evidence("AI Security Engineer", sources)

        self.assertEqual(len(groups), 1)

    def test_agent_payload_preserves_verified_canonical_url(self) -> None:
        payload = {
            "run_id": "run-1",
            "agent_name": "ai_security_role_researcher",
            "category": "AI × Security",
            "search_period": {"start": "2026-09-09", "end": "2026-09-15"},
            "job_market": SOUTH_KOREA_JOB_MARKET,
            "sources_checked": 2,
            "observations": [
                {
                    "role_name": "Agent Security Engineer",
                    "suggested_category": "AI × Security",
                    "description": "Agent security role",
                    "key_responsibilities": ["Secure tools"],
                    "required_skills": ["Threat modeling"],
                    "team_description": "Security team",
                    "product_context": "Agent platform",
                    "discovery_reason": "Agent security responsibility",
                    "experience_level": "경력",
                    "evidence_sources": [
                        {
                            "name": "Example Careers",
                            "url": "https://jobs.example/agent-security?utm_source=search",
                            "canonical_url": "https://jobs.example/agent-security",
                            "published_on": "2026-09-14",
                            "source_type": "Job Posting",
                            "employer_name": "Example Company",
                            "job_title": "Agent Security Engineer",
                            "job_location": "Seoul",
                            "job_market": "South Korea",
                        },
                        {
                            "name": "Example Research",
                            "url": "https://research.example/agent-security",
                            "published_on": "2026-09-15",
                            "source_type": "Informational",
                        },
                    ],
                }
            ],
            "exclusions": [],
            "existing_matches": [],
            "blockers": [],
        }

        result = parse_agent_discovery_result(payload)

        self.assertEqual(
            result.observations[0].evidence_sources[0].canonical_url,
            "https://jobs.example/agent-security",
        )

    def test_job_posting_requires_employer_name(self) -> None:
        with self.assertRaisesRegex(
            DiscoveryValidationError,
            "verified employer name",
        ):
            EvidenceSource(
                "Example Careers",
                "https://careers.example/roles/agent-security",
                date(2026, 9, 15),
                source_type=EvidenceType.JOB_POSTING,
                job_title="Agent Security Engineer",
                job_location="Seoul",
                job_market=SOUTH_KOREA_JOB_MARKET,
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
            experience_level=item.experience_level,
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

    def test_overseas_job_posting_is_rejected(self) -> None:
        with self.assertRaises(DiscoveryValidationError):
            EvidenceSource(
                "Overseas Careers",
                "https://careers.example/roles/overseas",
                date(2026, 9, 15),
                source_type=EvidenceType.JOB_POSTING,
                employer_name="Example Company",
                job_title="Agent Security Engineer",
                job_location="McLean, Virginia",
                job_market="United States",
            )

    def test_job_posting_requires_exact_source_job_title(self) -> None:
        with self.assertRaisesRegex(
            DiscoveryValidationError,
            "exact title from the source",
        ):
            EvidenceSource(
                "Example Careers",
                "https://careers.example/roles/agent-security",
                date(2026, 9, 15),
                source_type=EvidenceType.JOB_POSTING,
                employer_name="Example Company",
                job_location="Seoul",
                job_market=SOUTH_KOREA_JOB_MARKET,
            )

    def test_observation_rejects_semantically_merged_job_titles(self) -> None:
        item = observation()
        mismatched_source = EvidenceSource(
            "Another Careers",
            "https://careers.example/network-security-field-engineer",
            date(2026, 9, 15),
            source_type=EvidenceType.JOB_POSTING,
            employer_name="Another Company",
            job_title="Network and Information Security Field Engineer",
            job_location="Seoul",
            job_market=SOUTH_KOREA_JOB_MARKET,
        )

        with self.assertRaisesRegex(
            DiscoveryValidationError,
            "without semantic merging",
        ):
            RoleObservation(
                role_name="Network Security Solution and Infrastructure Engineer",
                suggested_category=item.suggested_category,
                description=item.description,
                key_responsibilities=item.key_responsibilities,
                required_skills=item.required_skills,
                team_description=item.team_description,
                product_context=item.product_context,
                discovery_reason=item.discovery_reason,
                experience_level=item.experience_level,
                evidence_sources=(mismatched_source,),
            )

    def test_global_informational_source_is_allowed_as_supporting_evidence(self) -> None:
        source = EvidenceSource(
            "Global Engineering Blog",
            "https://engineering.example/global-agent-security",
            date(2026, 9, 15),
        )

        self.assertEqual(source.source_type, EvidenceType.INFORMATIONAL)
        self.assertIsNone(source.job_market)

    def test_candidate_requires_a_south_korea_job_posting(self) -> None:
        item = observation()
        informational_only = RoleObservation(
            role_name=item.role_name,
            suggested_category=item.suggested_category,
            description=item.description,
            key_responsibilities=item.key_responsibilities,
            required_skills=item.required_skills,
            team_description=item.team_description,
            product_context=item.product_context,
            discovery_reason=item.discovery_reason,
            experience_level=item.experience_level,
            evidence_sources=(
                EvidenceSource(
                    "Global Report",
                    "https://reports.example/agent-security",
                    date(2026, 9, 14),
                ),
                EvidenceSource(
                    "Global Engineering Blog",
                    "https://engineering.example/agent-security",
                    date(2026, 9, 15),
                ),
            ),
        )

        with self.assertRaises(DiscoveryValidationError):
            select_new_candidates(
                (informational_only,),
                (),
                date(2026, 9, 15),
                default_period(date(2026, 9, 15)),
            )


if __name__ == "__main__":
    unittest.main()
