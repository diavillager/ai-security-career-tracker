# AI Security Career Tracker

AI, Security, AI × Security 영역의 새로운 직무를 발견하고, 사용자가 승인한 직무를 기준으로 최신 산업 및 직무 동향을 Notion에 축적하는 Codex Skill 프로젝트입니다.

## 현재 단계

프로젝트 기본 골격과 Notion 데이터베이스 생성·식별자 재사용 기능까지 구현했습니다. Role Discovery, 승인과 거절, Trend Update는 아직 구현되지 않았습니다.

## 확정된 기본값

- 검색 수단: Codex 웹 검색
- 개발 언어: Python 3.12
- 기본 검색 기간: 최근 7일
- 기준 시간대: Asia/Seoul
- Git 기본 가지: main

검색 수단은 나중에 교체할 수 있도록 설정과 검색 정책을 분리합니다.

## 구성

- `SKILL.md`: Skill의 진입점과 핵심 안전 규칙
- `agents/openai.yaml`: Codex 화면에 표시할 Skill 정보
- `config.example.toml`: 비밀정보가 없는 설정 예시
- `references/product-requirements.md`: MVP 범위와 단계별 구현 기준
- `references/notion-databases.md`: Roles DB와 Trends DB의 스키마 및 재사용 절차
- `src/ai_security_career_tracker/notion_databases.py`: 로컬 DB 식별자 검증 및 저장 도구
- `tests/test_foundation.py`: 기본 구조와 설정 검증

실제 Notion 데이터베이스 식별자는 Git에 올라가지 않는 `config.toml`에 저장합니다. 두 식별자 중 하나만 있거나 기존 값과 다른 값으로 바꾸려 하면 도구가 중단됩니다.

## 테스트

프로젝트 루트에서 Python 3.12로 다음 명령을 실행합니다.

```powershell
python -m unittest discover -s tests -v
```
