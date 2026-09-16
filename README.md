# AI Security Career Tracker

AI, Security, AI × Security 영역의 새로운 직무를 발견하고, 사용자가 승인한 직무를 기준으로 최신 산업 및 직무 동향을 Notion에 축적하는 Codex Skill 프로젝트입니다.

## 현재 단계

프로젝트 기본 골격, Notion 데이터베이스 생성·재사용, Role Discovery와 조사 전용 Agent까지 구현했습니다. 승인과 거절, Trend Update는 아직 구현되지 않았습니다.

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
- `.codex/config.toml`: 동시에 실행할 Agent 수 설정
- `.codex/agents/role_discovery.toml`: 대한민국 채용시장 직무 근거를 조사하는 읽기 전용 Agent
- `agents/openai.yaml`: Codex 화면에 표시할 Skill 정보
- `config.example.toml`: 비밀정보가 없는 설정 예시
- `references/product-requirements.md`: MVP 범위와 단계별 구현 기준
- `references/notion-databases.md`: Roles DB와 Trends DB의 스키마 및 재사용 절차
- `references/role-discovery.md`: 검색, 후보 판정, Notion 저장 및 결과 보고 기준
- `src/ai_security_career_tracker/notion_databases.py`: 로컬 DB 식별자 검증 및 저장 도구
- `src/ai_security_career_tracker/role_discovery.py`: 세 영역 검색 계획과 신규 Candidate 판정 도구
- `tests/test_foundation.py`: 기본 구조와 설정 검증
- `tests/test_role_discovery.py`: 검색 기간, 중복 차단, 다중 출처 및 Candidate 상태 검증
- `tests/test_role_discovery_agent.py`: Agent 설정과 역할 경계 검증

실제 Notion 데이터베이스 식별자는 Git에 올라가지 않는 `config.toml`에 저장합니다. 두 식별자 중 하나만 있거나 기존 값과 다른 값으로 바꾸려 하면 도구가 중단됩니다.

Role Discovery Agent는 웹 검색과 근거 정리만 담당합니다. Notion 저장, Candidate 승인·거절, Trend Update는 수행하지 않으며 부모 Skill이 결과를 검증한 뒤 다음 작업을 결정합니다.

## 테스트

프로젝트 루트에서 Python 3.12로 다음 명령을 실행합니다.

```powershell
python -m unittest discover -s tests -v
```
