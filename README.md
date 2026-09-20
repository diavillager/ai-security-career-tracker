# AI Security Career Tracker

AI, Security, AI × Security 영역의 대한민국 채용 공고와 국내외 동향을 추적하는 Codex Skill 프로젝트입니다.

## 현재 단계

Job Discovery 개편의 두 번째 단계를 구현했습니다. 세 검색 Agent가 실제 공고를 수집하고, 종합 검토 Agent가 원문·근무지·분류·중복 위험을 공고별로 확인하며, Python 경계가 `적합`, `검토 필요`, `제외`, `중복`을 독립 판정합니다.

아직 새 Jobs DB와 Notion 쓰기는 연결하지 않았습니다. 기존 Roles DB, Candidate 관련 코드와 기존 Trend Update 구현은 데이터 이전 단계 전까지 호환용으로 남아 있지만, 새 Job Discovery 결과를 기존 Roles DB에 저장하지 않습니다.

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
- `tests/test_job_discovery.py`: 공고 판정·중복·부분 성공·검토 격리 시험
- `tests/test_job_discovery_agent.py`: Agent 설정과 역할 경계 시험

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

## 다음 구현 단계

새 Jobs DB schema와 Trends DB 변경 계획을 실제 Notion 상태와 대조해 제시하고, 사용자 승인 뒤 기존 데이터를 보존하며 이전합니다. 그 전에는 현재 운영 DB를 변경하지 않습니다.
