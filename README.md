# AI Security Career Tracker

AI, Security, AI × Security 영역의 대한민국 채용 공고와 국내외 동향을 추적하는 Codex Skill 프로젝트입니다.

## 현재 상태

MVP의 Job Discovery와 Trend Update 구현 및 운영 Notion 실사용 시험을 완료했습니다. Job Discovery는 공고를 수집·검토하고, Trend Update는 Jobs나 보관된 Roles 상태와 무관하게 AI, Security, AI × Security 분야를 직접 검색합니다.

운영 Notion을 Jobs·Trends 두 탭 구조로 이전하고 기존 Roles 1건을 Jobs의 `검토 필요` 행으로 보존했습니다. 기존 Roles DB와 원본 행은 보관 페이지로 옮겼으며, 로컬 설정도 새 Jobs 식별자로 전환했습니다. Candidate 관련 코드는 호환 기록으로 남아 있지만 새 workflow에서는 실행하지 않습니다.

Job Discovery 저장은 설정 식별자와 실제 Jobs schema·옵션을 다시 대조하고 모든 행을 먼저 검증한 뒤 실행합니다. `적합`과 `검토 필요`만 생성하며, `제외`와 `중복`은 실행 보고에만 남깁니다. 실제 행 생성과 필요한 schema 옵션 추가는 사용자 승인 뒤 수행합니다.

## MVP 검증 결과

- 전체 자동 시험 153개, Python 문법 검사와 Skill 구조 검사를 통과했습니다.
- 2026-08-20~2026-09-20 Job Discovery 실사용에서 대한민국 근무 공고 17건을 새로 저장했습니다. 운영 Jobs는 이전한 1건을 포함해 18건이며 화면 확인까지 완료했습니다.
- 2026-09-14~2026-09-20 Trend Update 실사용에서 동향 6건을 저장했습니다. 운영 Trends의 재조회와 화면 확인까지 완료했습니다.
- 두 흐름 모두 실제 schema·선택지 전체를 저장 전에 검사하고, 사용자 승인 뒤에만 Notion을 변경했습니다.

현재 확인된 기능 차단 결함은 없습니다. 다만 구형 Role Discovery와 새 Job Discovery의 동일 기간·동일 출처 비교 지표는 완전하게 산출하지 못했습니다. 구형 실행과 신형 실행의 기준일이 다르고, 구형 실행의 URL별 전체 제외 자료가 남아 있지 않아 누락률과 무관 공고 포함률을 같은 표본에서 계산할 수 없습니다. 이 제한은 현재 Job Discovery의 저장 동작을 막지 않으며, 과거 결과를 추정값으로 채우지 않습니다. 정확한 비교가 필요하면 두 방식을 같은 고정 표본에 다시 적용하는 별도 평가로 수행합니다.

## 확정된 기본값

- 검색 수단: Codex 웹 검색
- 개발 언어: Python 3.12
- 기본 검색 기간: 최근 7일
- 기준 시간대: Asia/Seoul
- 검색 경로: AI, Security, AI × Security
- 채용 시장: 대한민국

## 주요 구성

- `SKILL.md`: Job Discovery와 Trend Update의 진입점·안전 경계
- `.codex/agents/ai_job_researcher.toml`: AI 검색 경로 Agent
- `.codex/agents/security_job_researcher.toml`: Security 검색 경로 Agent
- `.codex/agents/ai_security_job_researcher.toml`: AI × Security 검색 경로 Agent
- `.codex/agents/job_evidence_reviewer.toml`: 공고별 종합 검토 Agent
- `references/job-discovery-redesign.md`: 두 DB 구조와 단계별 전환 설계
- `references/job-discovery-agent-contract.md`: 세 검색 Agent의 공통 입력·출력 계약
- `references/job-evidence-reviewer-contract.md`: 종합 검토 Agent 계약
- `references/notion-job-discovery-migration-plan.md`: 운영 Notion 실측 결과와 Jobs·Trends 안전 이전 계획
- `src/ai_security_career_tracker/job_discovery.py`: 검색 작업, 구조 검사, 검토 반영, 공고별 판정과 중복 처리
- `src/ai_security_career_tracker/job_notion_write.py`: 운영 Jobs 대상 재검증, 전체 사전 검사와 승인 후 행 생성 경계
- `src/ai_security_career_tracker/notion_job_migration.py`: Jobs schema, Trends 변경문과 기존 Roles 행 변환 계획
- `src/ai_security_career_tracker/notion_databases.py`: Jobs·Trends 설정 검증과 Roles 설정의 원자적 이전
- `src/ai_security_career_tracker/trend_update.py`: 분야별 검색 작업, 분류·중복 검증, Trends 13개 속성과 안전한 저장 경계
- `tests/test_job_discovery.py`: 공고 판정·중복·부분 성공·검토 격리 시험
- `tests/test_job_discovery_agent.py`: Agent 설정과 역할 경계 시험
- `tests/test_job_notion_write.py`: Jobs 대상·옵션·부분 실패와 쓰기 제외 경계 시험
- `tests/test_notion_job_migration.py`: schema, 기존 행 보존과 Trends 비어 있음 경계 시험
- `tests/test_trend_update.py`: Jobs·Roles 독립성, 분류·중복, schema 옵션과 부분 실패 시험

## Job Discovery 처리 원칙

세 Agent의 할당 영역은 검색 경로이며 최종 분류의 허용 목록이 아닙니다. 예를 들어 AI 검색에서 발견한 공고도 실제 업무가 AI 보안이면 `AI × Security`로 분류합니다.

공고 한 건에는 두 번째 독립 근거를 요구하지 않습니다. 접근 가능한 원문에서 대한민국 근무와 관련 업무를 확인하면 저장 후보가 될 수 있습니다. 게시일이 없지만 현재 모집 중인 공고는 버리지 않고 `검토 필요`로 남깁니다. 일부 검색 경로나 검토가 실패해도 다른 정상 공고의 판정을 막지 않습니다.

중복은 공고 단위로 판정하며, 대표 URL 외에 확인한 복제·관련 URL도 보존합니다.

## 설치와 테스트

저장소 루트에서 editable 설치와 자동 시험을 실행합니다.

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
$env:PYTHONUTF8 = "1"
python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
```

실제 Notion 식별자는 Git에서 제외되는 `config.toml`에만 저장합니다. 인증정보는 저장소에 기록하지 않습니다.

## 후속 개선 범위

MVP 필수 구현은 완료됐습니다. 이후 작업은 정기 실행, 검색 출처 접근성 개선, 고정 표본 기반 구형·신형 비교 평가와 GitHub 자동 검사 도입 같은 선택적 개선으로 관리합니다.
