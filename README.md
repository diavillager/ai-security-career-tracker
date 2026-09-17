# AI Security Career Tracker

AI, Security, AI × Security 영역의 새로운 직무를 발견하고, 사용자가 승인한 직무를 기준으로 최신 산업 및 직무 동향을 Notion에 축적하는 Codex Skill 프로젝트입니다.

## 현재 단계

프로젝트 기본 골격, Notion 데이터베이스 생성·재사용, Role Discovery의 영역별 조사 Agent 세 개와 종합 근거 검토 Agent, Candidate 승인·거절까지 구현했습니다. Trend Update는 아직 구현되지 않았습니다.

## 확정된 기본값

- 검색 수단: Codex 웹 검색
- 개발 언어: Python 3.12
- 기본 검색 기간: 최근 7일
- 기준 시간대: Asia/Seoul
- Git 기본 가지: main

검색 수단은 나중에 교체할 수 있도록 설정과 검색 정책을 분리합니다.

## 언어 지침

- PR 제목·설명·검토 코멘트는 한국어로 작성합니다.
- 커밋 메시지는 feat:, fix:, docs:, test: 같은 영어 유형 뒤에 한국어 설명을 작성합니다.
- SKILL.md와 사용자가 읽는 참고 문서의 설명은 한국어로 작성합니다.
- Skill 이름, 기능명, Notion 속성·상태값, 브랜치명, 코드 식별자, 설정 키, 명령어는 영어를 유지합니다.

## 구성

- `SKILL.md`: Skill의 진입점과 핵심 안전 규칙
- `.codex/config.toml`: 영역별 조사 Agent 세 개의 동시 실행 설정
- `.codex/agents/ai_role_researcher.toml`: AI 직무 조사 Agent
- `.codex/agents/security_role_researcher.toml`: Security 직무 조사 Agent
- `.codex/agents/ai_security_role_researcher.toml`: AI × Security 직무 조사 Agent
- `.codex/agents/role_evidence_reviewer.toml`: 세 조사 결과의 의미 품질을 순차 검토하는 Agent
- `agents/openai.yaml`: Codex 화면에 표시할 Skill 정보
- `config.example.toml`: 비밀정보가 없는 설정 예시
- `references/product-requirements.md`: MVP 범위와 단계별 구현 기준
- `references/notion-databases.md`: Roles DB와 Trends DB의 스키마 및 재사용 절차
- `references/role-discovery.md`: 검색, 후보 판정, Notion 저장 및 결과 보고 기준
- `references/role-discovery-agent-contract.md`: 세 조사 Agent의 공통 입력·출력 계약
- `references/role-evidence-reviewer-contract.md`: 종합 근거 검토 Agent의 입력·출력 계약
- `references/candidate-review.md`: Candidate 자연어 결정, 검증, Notion 적용과 실패 보고 절차
- `src/ai_security_career_tracker/notion_databases.py`: 로컬 DB 식별자 검증 및 저장 도구
- `src/ai_security_career_tracker/role_discovery.py`: 세 영역 검색 계획과 신규 Candidate 판정 도구
- `src/ai_security_career_tracker/candidate_review.py`: Candidate 승인·거절 계획과 Notion 속성 적용 도구
- `tests/test_foundation.py`: 기본 구조와 설정 검증
- `tests/test_role_discovery.py`: 검색 기간, 중복 차단, 다중 출처 및 Candidate 상태 검증
- `tests/test_role_discovery_agent.py`: Agent 설정과 역할 경계 검증
- `tests/test_candidate_review.py`: 승인·거절 계획, Notion 속성 연결과 쓰기 실패 검증

실제 Notion 데이터베이스 식별자는 Git에 올라가지 않는 `config.toml`에 저장합니다. 두 식별자 중 하나만 있거나 기존 값과 다른 값으로 바꾸려 하면 도구가 중단됩니다.

세 Role Discovery 조사 Agent는 각 영역의 웹 검색과 근거 정리만 병렬로 담당합니다. 부모 Skill이 동일한 기간과 기존 직무 snapshot을 제공하고, 세 결과가 모두 구조 검사를 통과하면 `role_evidence_reviewer`가 출처 접근성·독립성, 의미 중복과 분류 모호성을 순차 검토합니다. 그 뒤 Python 검증으로 Candidate 초안을 판정합니다. 어떤 Agent도 Notion 저장, Candidate 승인·거절, Trend Update를 수행하지 않습니다.

Candidate 판정에는 독립 근거가 2개 이상 필요합니다. 같은 회사의 같은 직무 공고가 여러 채용 플랫폼에 복제된 경우 URL이 달라도 하나로 계산하며, 확인한 원본 URL은 검토를 위해 모두 보존합니다.

Candidate 승인·거절은 사용자가 대상과 결정을 명시한 뒤에만 실행합니다. Python이 전체 요청을 먼저 검증하고 정확한 Notion 속성 변경을 만든 다음, 확인된 Roles DB의 `Status`, `Last Reviewed`와 필요한 `Notes`만 갱신합니다. 중간 실패가 발생하면 성공한 page와 실패한 page를 구분해 보고하고 데이터베이스를 다시 조회합니다.

## 테스트

프로젝트 루트에서 Python 3.12로 다음 명령을 실행합니다.

```powershell
python -m unittest discover -s tests -v
```
