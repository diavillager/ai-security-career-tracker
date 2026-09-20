---
name: ai-security-career-tracker
description: 대한민국 AI, Security, AI Security 채용 공고를 찾아 공고별로 검증하고, 관련 국내외 동향을 수집합니다. Job Discovery와 Trend Update에 사용하며 일반 취업 상담이나 무관한 보안 뉴스에는 사용하지 않습니다.
---

# AI Security Career Tracker

AI, Security, AI × Security 영역의 대한민국 채용 공고와 국내외 동향을 서로 독립적으로 추적합니다.

## 지원 기능

- `Job Discovery`: 대한민국 근무 채용 공고를 찾고, 공고 본문에서 직무를 인식해 공고별 저장 계획을 만듭니다.
- `Trend Update`: AI, Security, AI × Security 분야의 기술·산업·연구·정책·채용시장 동향을 수집합니다.

운영 Notion은 Jobs·Trends 구조로 이전되었습니다. 기존 Roles DB와 원본 행은 보관 페이지에 남아 있으며, Job Discovery 결과를 기존 Roles DB나 Candidate 승인·거절 흐름으로 보내지 않습니다. 새 공고의 자동 저장 경계와 Trend Update의 Jobs 독립형 흐름은 아직 구현 전이므로 실제 수집 결과를 곧바로 Notion에 쓰지 않습니다.

## 언어 지침

- PR 제목·설명·검토 코멘트는 한국어로 작성합니다.
- 커밋 메시지는 feat:, fix:, docs:, test: 같은 영어 유형 뒤에 한국어 설명을 작성합니다.
- 사용자가 읽는 문서는 한국어로 쓰되 Skill 이름, 기능명, branch명, 코드 식별자, 설정 키, 명령어와 내부 enum은 영어로 유지합니다.
- Notion 속성명과 옵션은 한글을 사용하되 `AI`, `Security`, `AI × Security`, `GitHub`는 유지합니다.

기능을 변경하기 전에 [제품 요구사항](references/product-requirements.md)을 읽습니다. Job Discovery 개편의 확정 기준과 새 DB 제안은 [Job Discovery 중심 개편 설계안](references/job-discovery-redesign.md)을 따릅니다.

## Job Discovery

조사 Agent의 입력·출력은 [Job Discovery 조사 Agent 계약](references/job-discovery-agent-contract.md), 종합 검토는 [Job Discovery 종합 검토 Agent 계약](references/job-evidence-reviewer-contract.md)을 따릅니다.

1. 부모 workflow가 `run_id`, 검색 기간, 수집일과 기존 Jobs snapshot을 확정합니다. 기간을 지정하지 않으면 오늘을 마지막 날로 하는 최근 7일을 사용합니다.
2. Python `build_job_search_tasks`로 AI, Security, AI × Security의 검색 작업을 만듭니다.
3. `ai_job_researcher`, `security_job_researcher`, `ai_security_job_researcher`를 병렬로 시작합니다. 검색 경로는 최종 분류의 허용 목록이 아닙니다.
4. 완료된 결과를 각각 `parse_job_agent_result`로 변환합니다. 한 경로가 실패하거나 `blockers`가 있어도 다른 경로의 확인된 공고를 버리지 않습니다.
5. 구조를 통과한 observation 전체를 `job_evidence_reviewer`에 한 번 전달하고 `parse_job_evidence_review`로 변환합니다. 검토 flag와 누락은 해당 공고만 `검토 필요`로 보냅니다.
6. `consolidate_job_agent_results`로 공고별 `적합`, `검토 필요`, `제외`, `중복`을 판정합니다. 공고 한 건에 두 번째 독립 근거를 요구하지 않습니다.
7. 출처별 질의 수, 확인 결과 수, 연 원문 수, 접근 실패, 완료·미완료 검색 경로와 공고별 판정을 보고합니다. 미완료 경로나 blocker가 있으면 전체 검색을 완료했다고 표현하지 않습니다.
8. 현재는 검증된 저장 계획만 보고합니다. 새 공고 저장 연결이 구현되기 전에는 운영 Jobs DB에 자동으로 쓰지 않습니다.

Job Discovery 채용 정보는 공고 원문에서 대한민국 근무가 확인된 경우만 사용합니다. 기업 공식 채용 페이지와 Saramin, JobKorea, Wanted, Jumpit을 우선하지만 완전한 허용 목록으로 쓰지 않습니다. 게시일이 없더라도 현재 모집 중임을 확인하면 `published_on: null`로 검토 대상으로 남깁니다. 원문 공고명과 모든 확인 URL을 보존하며, 중복은 URL, 플랫폼 공고 ID, 회사명·원문 공고명·근무지·날짜 순으로 공고 단위에서 판단합니다.

## Notion 전환 경계

운영 DB의 확인과 Jobs·Trends 구조는 [Notion 데이터베이스 지침](references/notion-databases.md)과 [Job Discovery Notion 이전 계획](references/notion-job-discovery-migration-plan.md)을 따릅니다. 2026-09-20 이전은 검증을 마쳤으며, 이후 schema나 데이터 변경에도 읽기 전용 재조회와 사용자 승인을 먼저 받습니다.

- 저장된 식별자에 접근할 수 없거나 구조가 다르면 대체 DB를 만들지 않습니다.
- 기존 Roles DB와 데이터를 즉시 삭제하지 않습니다.
- Job Discovery 계획을 기존 Roles DB schema에 억지로 맞춰 쓰지 않습니다.
- 새 Jobs DB와 Trends DB 변경 목록, 이전 행과 보관 대상을 사용자에게 보여준 뒤 승인된 범위만 적용합니다.
- `jobs_schema_ddl`, `trends_schema_migration_statements`, `plan_notion_job_migration`으로 schema와 기존 행 변환을 먼저 검증합니다.
- 설정 전환은 검증된 기존 Roles·Trends snapshot과 새 Jobs 식별자를 사용해 `migrate_database_config`로 한 번에 적용합니다.

## Trend Update

현재 Trend Update 실행은 중단합니다. 기존 구현은 보관된 Roles DB의 Approved 직무 snapshot과 relation에 의존하므로 새 Trends schema에 쓰면 안 됩니다. 다음 단계에서 [Trend Update 지침](references/trend-update.md)과 [분류·관계 기준](references/classification-relations.md)을 Jobs DB 상태와 무관한 AI, Security, AI × Security 분야 검색 흐름으로 개편한 뒤 다시 활성화합니다.

비채용 동향은 해외 출처도 허용하지만 커뮤니티와 소셜 출처는 제외합니다. 채용 자료는 대한민국 근무가 확인된 경우만 허용합니다. 모든 저장 항목은 원문 URL과 게시일을 보존하며, 실행하지 않은 검색이나 저장을 완료했다고 보고하지 않습니다.

## 승인 경계

- 데이터베이스를 만들거나 schema·행을 변경하기 전에 연결된 Notion workspace와 대상을 확인하고 사용자에게 변경 목록을 보여줍니다.
- 인증정보를 저장소 파일, 로그, 커밋 또는 PR 본문에 저장하지 않습니다.
- 사용자의 명시적 승인 없이 feature branch를 main에 병합하지 않습니다.
