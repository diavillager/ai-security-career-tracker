# Notion 데이터베이스 설정

이 절차는 확인된 AI Security Career Tracker 프로젝트 페이지 아래에서만 사용합니다.

## Roles DB

먼저 다음 속성을 가진 Roles DB를 만듭니다.

| Property | Type | 허용값 또는 용도 |
| --- | --- | --- |
| Role Name | Title | 표준 Role Name |
| Category | Select | AI, Security, AI × Security |
| Status | Select | Candidate, Approved, Rejected |
| Experience Level | Select | 신입, 경력, 신입·경력, 미확인 |
| Description | Rich text | 짧은 직무 정의 |
| Key Responsibilities | Rich text | 근거에 기반한 핵심 책임 |
| First Discovered | Date | 처음 확인한 날짜 |
| Last Reviewed | Date | 최근 검토 날짜 |
| Evidence Sources | Rich text | 원본 근거 URL |
| Notes | Rich text | 검토 메모 |

## Trends DB

Roles DB의 data source 식별자를 확인한 뒤에만 Trends DB를 만듭니다.

| Property | Type | 허용값 또는 용도 |
| --- | --- | --- |
| Title | Title | 출처 제목 |
| Summary | Rich text | 간결한 출처 요약 |
| Key Insight | Rich text | 직무와 관련된 핵심 발견 |
| Source Type | Select | News, Industry Media, Company Blog, Engineering Blog, Press Release, Job Posting, Official Documentation, Research Report, Newsletter, GitHub, Paper, Conference, Government, Other |
| Source Name | Rich text | 발행자 또는 기관 |
| Original URL | URL | 원본 출처 URL |
| Published Date | Date | 확인된 게시일 |
| Collected Date | Date | 수집일 |
| Related Roles | Relation | Roles DB data source |
| Domain | Multi-select | AI, Security, AI × Security 중 하나 이상 |

## 안전한 생성과 재사용

1. 연결된 Notion 사용자 정보와 설정된 프로젝트 페이지를 조회합니다.
2. load_database_config로 config.toml을 읽습니다.
3. 두 식별자가 모두 있으면 두 data source를 조회하고 제목, 필수 속성, 속성 유형을 확인합니다. 올바르면 재사용합니다. 기존 Trends DB의 `Domain`이 단일 `Select`이면 쓰기 전에 `Multi-select`로 변경할 대상을 사용자에게 보여주고 승인을 받습니다.
4. 두 식별자가 모두 없으면 새로 만들기 전에 프로젝트 페이지에서 제목이 정확히 일치하는 기존 데이터베이스를 찾습니다.
5. Roles DB를 만들고 구조를 확인한 다음, Roles data source로 향하는 단방향 Related Roles relation을 가진 Trends DB를 만듭니다.
6. 두 구조를 검증하고 두 식별자를 함께 저장합니다. config.toml은 절대 커밋하지 않습니다.

식별자가 하나만 있거나, 저장된 데이터베이스를 조회할 수 없거나, 구조가 맞지 않거나, 제목이 같은 기존 데이터베이스 중 대상을 확정할 수 없으면 작업을 중단하고 사용자에게 방향을 묻습니다. 대체 데이터베이스를 자동으로 만들지 않습니다.
