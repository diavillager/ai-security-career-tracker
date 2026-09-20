# AI Security Career Tracker

AI, Security, AI × Security 영역의 새로운 직무를 발견하고, 사용자가 승인한 직무를 기준으로 최신 산업 및 직무 동향을 Notion에 축적하는 Codex Skill 프로젝트입니다.

## 현재 단계

MVP의 Role Discovery, Candidate 승인·거절과 Trend Update를 구현했습니다. 영역별 조사 Agent 세 개와 종합 근거 검토 Agent, URL 정규화, 분류·직무 관계 검증을 포함하며 실제 Notion 저장까지 전체 흐름을 확인했습니다.

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
- `references/job-discovery-redesign.md`: Role Discovery를 Job Discovery 중심으로 바꾸기 위한 개편 설계안이며 아직 구현되지 않은 다음 버전 제안
- `references/notion-databases.md`: Roles DB와 Trends DB의 스키마 및 재사용 절차
- `references/role-discovery.md`: 검색, 후보 판정, Notion 저장 및 결과 보고 기준
- `references/role-discovery-agent-contract.md`: 세 조사 Agent의 공통 입력·출력 계약
- `references/role-evidence-reviewer-contract.md`: 종합 근거 검토 Agent의 입력·출력 계약
- `references/candidate-review.md`: Candidate 자연어 결정, 검증, Notion 적용과 실패 보고 절차
- `references/trend-update.md`: Approved 직무 동향 검색, 검증, 중복 확인과 Notion 저장 절차
- `references/classification-relations.md`: 출처 유형, 복수 관련 분야, 관련 직무, 요약과 핵심 시사점 검증 기준
- `src/ai_security_career_tracker/notion_databases.py`: 로컬 DB 식별자 검증 및 저장 도구
- `src/ai_security_career_tracker/job_discovery.py`: 다음 버전 Job Discovery의 공고별 판정과 중복 처리 경계. 아직 Skill이나 Notion 쓰기에는 연결하지 않음
- `src/ai_security_career_tracker/role_discovery.py`: 세 영역 검색 계획과 신규 Candidate 판정 도구
- `src/ai_security_career_tracker/candidate_review.py`: Candidate 승인·거절 계획과 Notion 속성 적용 도구
- `src/ai_security_career_tracker/trend_update.py`: Approved 직무 검색 계획, 동향 검증과 Trends DB 속성 적용 도구
- `src/ai_security_career_tracker/source_urls.py`: 원본을 보존하는 URL 비교 키와 canonical URL 검증 도구
- `src/ai_security_career_tracker/classification.py`: 출처 유형, 복수 관련 분야와 Approved 직무 관계 검증 도구
- `tests/test_foundation.py`: 기본 구조와 설정 검증
- `tests/test_job_discovery.py`: 단일 공고 허용, 개별 판정, 세 검색 범주와 공고 중복 처리 검증
- `tests/test_role_discovery.py`: 검색 기간, 중복 차단, 다중 출처 및 Candidate 상태 검증
- `tests/test_role_discovery_agent.py`: Agent 설정과 역할 경계 검증
- `tests/test_candidate_review.py`: 승인·거절 계획, Notion 속성 연결과 쓰기 실패 검증
- `tests/test_trend_update.py`: Approved snapshot, 출처·기간·URL 검증과 Trends DB 쓰기 실패 검증
- `tests/test_source_urls.py`: 추적 매개변수, fragment, query 순서와 canonical URL 정규화 검증
- `tests/test_classification_relations.py`: PRD 출처 유형, 복수 관련 분야, 관련 직무와 요약·해석 분리 검증

실제 Notion 데이터베이스 식별자는 Git에 올라가지 않는 `config.toml`에 저장합니다. 두 식별자 중 하나만 있거나 기존 값과 다른 값으로 바꾸려 하면 도구가 중단됩니다.

Notion 속성명과 사용자에게 보이는 옵션은 한글로 저장합니다. 분류 기준과 Agent 계약에 쓰는 내부 enum은 영어로 유지하며, `AI`, `Security`, `AI × Security`, `GitHub` 옵션은 원문을 유지합니다.

세 Role Discovery 조사 Agent는 각 영역의 웹 검색과 근거 정리만 병렬로 담당합니다. 부모 Skill이 동일한 기간과 기존 직무 snapshot을 제공하고, 세 결과가 모두 구조 검사를 통과하면 `role_evidence_reviewer`가 출처 접근성·독립성, 의미 중복과 분류 모호성을 순차 검토합니다. 그 뒤 Python 검증으로 Candidate 초안을 판정합니다. 어떤 Agent도 Notion 저장, Candidate 승인·거절, Trend Update를 수행하지 않습니다.

Candidate 판정에는 독립 근거가 2개 이상 필요합니다. 같은 회사의 같은 직무 공고가 여러 채용 플랫폼에 복제된 경우 URL이 달라도 하나로 계산하며, 확인한 원본 URL은 검토를 위해 모두 보존합니다.

각 Job Posting은 원문에 표시된 정확한 `job_title`을 포함해야 합니다. Python은 이 값이 observation의 Role Name과 정규화 후 같은지 검사하며, 책임이 비슷해도 서로 다른 원문 직무명을 하나의 Candidate로 합치는 결과를 거부합니다.

Notion의 `근거 출처`에는 `[독립 근거 1 · 동일 공고] Source Name — Original URL` 형식으로 복제본을 포함한 모든 URL을 기록합니다. `메모`에는 독립 근거 수와 보존 URL 수를 따로 표시합니다.

Candidate 승인·거절은 사용자가 대상과 결정을 명시한 뒤에만 실행합니다. Python이 전체 요청을 먼저 검증하고 정확한 Notion 속성 변경을 만든 다음, 확인된 Roles DB의 `상태`, `최근 검토일`과 필요한 `메모`만 갱신합니다. 중간 실패가 발생하면 성공한 page와 실패한 page를 구분해 보고하고 데이터베이스를 다시 조회합니다.

Trend Update는 실행 시작 시점에 `Approved`인 직무만 검색합니다. 비채용 동향은 해외 출처도 허용하지만 커뮤니티와 소셜 출처는 제외하며, Job Posting은 대한민국 근무지가 확인된 경우만 사용합니다. PRD의 전체 `출처 유형`, 하나 이상의 `관련 분야`, 복수 `관련 직무`, 분리된 `요약`과 `핵심 시사점`을 검증합니다. 추적 매개변수와 fragment를 제거한 비교 키 또는 원문에서 확인한 canonical URL이 Trends DB의 기존 `원문 URL`과 같으면 다시 저장하지 않습니다. 실제 Notion 쓰기 직전에 새 항목을 보여주고 확인을 받습니다.

## 설치와 호출

저장소 루트를 Codex Skill `ai-security-career-tracker`로 설치합니다. Python 경계 코드를 어느 작업 위치에서도 불러올 수 있게 저장소 루트에서 editable 설치를 한 번 실행합니다.

```powershell
python -m pip install -e .
```

실제 Notion 식별자는 `config.example.toml`을 복사한 `config.toml`에 저장합니다. `config.toml`은 Git에서 제외되므로 커밋하지 않습니다. Skill을 설치하거나 설정한 뒤에는 새 Codex 작업에서 다음처럼 자연어로 호출합니다.

- `$ai-security-career-tracker`를 사용해 최근 7일의 새 AI 보안 직무를 찾아줘.
- `$ai-security-career-tracker`를 사용해 지정한 Candidate를 승인해줘.
- `$ai-security-career-tracker`를 사용해 Approved 직무의 최근 7일 동향을 수집해줘.

각 요청은 독립 실행입니다. Role Discovery에서 새로 만든 Candidate를 같은 실행의 Trend Update에 자동으로 포함하지 않으며, Notion 쓰기 직전에는 변경 대상을 보여주고 사용자 확인을 받습니다.

## 테스트

프로젝트 루트에서 Python 3.12로 전체 자동 시험과 Skill 구조 검사를 실행합니다. Windows에서는 한국어 `SKILL.md`를 일관되게 읽도록 UTF-8 모드를 지정합니다.

```powershell
python -m unittest discover -s tests -v
$env:PYTHONUTF8 = "1"
python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
```
