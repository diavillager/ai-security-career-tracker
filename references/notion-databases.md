# Notion 데이터베이스 설정

이 절차는 확인된 AI Security Career Tracker 프로젝트 페이지 아래에서만 사용합니다.

## Roles DB

먼저 다음 속성을 가진 Roles DB를 만듭니다.

| Property | Type | 허용값 또는 용도 |
| --- | --- | --- |
| 직무명 | Title | 표준 직무명 |
| 직무 분야 | Select | AI, Security, AI × Security |
| 상태 | Select | 후보, 승인, 거절 |
| 경력 수준 | Select | 신입, 경력, 신입·경력, 미확인 |
| 직무 설명 | Rich text | 짧은 직무 정의 |
| 주요 업무 | Rich text | 근거에 기반한 핵심 책임 |
| 최초 발견일 | Date | 처음 확인한 날짜 |
| 최근 검토일 | Date | 최근 검토 날짜 |
| 근거 출처 | Rich text | 원본 근거 URL |
| 메모 | Rich text | 검토 메모 |

## Trends DB

Roles DB의 data source 식별자를 확인한 뒤에만 Trends DB를 만듭니다.

| Property | Type | 허용값 또는 용도 |
| --- | --- | --- |
| 제목 | Title | 출처 제목 |
| 요약 | Rich text | 간결한 출처 요약 |
| 핵심 시사점 | Rich text | 직무와 관련된 핵심 발견 |
| 출처 유형 | Select | 뉴스, 업계 매체, 기업 블로그, 기술 블로그, 보도자료, 채용 공고, 공식 문서, 연구 보고서, 뉴스레터, GitHub, 논문, 컨퍼런스, 정부, 기타 |
| 출처명 | Rich text | 발행자 또는 기관 |
| 원문 URL | URL | 원본 출처 URL |
| 게시일 | Date | 확인된 게시일 |
| 수집일 | Date | 수집일 |
| 관련 직무 | Relation | Roles DB data source |
| 관련 분야 | Multi-select | AI, Security, AI × Security 중 하나 이상 |

## 안전한 생성과 재사용

1. 연결된 Notion 사용자 정보와 설정된 프로젝트 페이지를 조회합니다.
2. load_database_config로 config.toml을 읽습니다.
3. 두 식별자가 모두 있으면 두 data source를 조회하고 제목, 필수 속성, 속성 유형을 확인합니다. 올바르면 재사용합니다. 기존 Trends DB의 `관련 분야`가 단일 `Select`이면 쓰기 전에 `Multi-select`로 변경할 대상을 사용자에게 보여주고 승인을 받습니다.
4. 두 식별자가 모두 없으면 새로 만들기 전에 프로젝트 페이지에서 제목이 정확히 일치하는 기존 데이터베이스를 찾습니다.
5. Roles DB를 만들고 구조를 확인한 다음, Roles data source로 향하는 단방향 `관련 직무` relation을 가진 Trends DB를 만듭니다.
6. 두 구조를 검증하고 두 식별자를 함께 저장합니다. config.toml은 절대 커밋하지 않습니다.

식별자가 하나만 있거나, 저장된 데이터베이스를 조회할 수 없거나, 구조가 맞지 않거나, 제목이 같은 기존 데이터베이스 중 대상을 확정할 수 없으면 작업을 중단하고 사용자에게 방향을 묻습니다. 대체 데이터베이스를 자동으로 만들지 않습니다.

Python 내부 enum과 Agent JSON 계약은 영어 값을 사용합니다. Notion을 읽고 쓸 때만 `notion_options.py`의 양방향 매핑을 사용하며, `직무 분야`와 `관련 분야`의 `AI`, `Security`, `AI × Security` 및 `출처 유형`의 `GitHub`는 번역하지 않습니다.
