# Notion 데이터베이스 설정

이 절차는 확인된 `AI Security Career Tracker` 프로젝트 페이지의 현재 운영 구조를 점검하고 변경할 때만 사용한다. [Job Discovery Notion 이전 계획](notion-job-discovery-migration-plan.md)은 완료된 이전의 역사 기록이며 운영 절차로 다시 실행하지 않는다.

## 목표 구조

운영 화면에는 하나의 inline database container와 두 탭을 둔다.

- `Jobs`: 대한민국 채용 공고를 공고별로 저장하는 Jobs data source
- `Trends`: AI, Security, AI × Security 분야 동향을 저장하는 Trends data source

Jobs와 Trends는 서로 독립적이다. Trends의 `관련 직무`는 Jobs relation이 아니라 직무 유형을 담는 Multi-select이다.

## 안전한 확인과 재사용

1. 연결된 Notion workspace와 사용자를 확인한다.
2. `config.toml`의 프로젝트 페이지, Jobs·Trends 식별자를 읽는다.
3. 저장된 식별자가 있으면 해당 data source의 제목, 필수 속성, 속성 유형과 옵션을 조회한다.
4. 프로젝트 페이지에 하나의 inline database container와 `Jobs`, `Trends` 두 탭이 있는지 확인하고, 두 data source의 식별자·제목·schema·옵션·행 수를 함께 대조한다.
5. 제목이 같거나 연결된 data source가 여러 개면 URL, parent와 schema를 함께 확인해 대상을 구분한다.
6. 식별자가 없거나 접근할 수 없거나 schema가 다르면 대체 database를 자동 생성하지 않고 중단한다.
7. 보관 페이지와 Roles DB는 현재 운영 구조에 포함되지 않는다. 찾지 못한 것을 오류로 처리하거나 자동으로 다시 만들지 않는다.

`config.toml`에는 `jobs_database_id`와 `trends_database_id`로 현재 두 data source 식별자를 저장한다. 실제 식별자는 Git에 포함하지 않는다. `roles_database_id`를 운영 설정에 다시 추가하지 않으며, 식별자를 변경할 때는 두 대상을 모두 검증하고 부분 저장을 허용하지 않는다.

## 완료된 이전과 재실행 금지

- 2026-09-20에 Jobs data source 생성, 기존 Roles 1건 이전, Trends schema 변경과 `Jobs`·`Trends` 탭 구성을 완료했다.
- 2026-09-21에 Trends 원본 data source의 소유 위치를 운영 container로 옮기고 두 탭과 데이터가 유지되는지 확인한 뒤 `AI Security Career Tracker 보관` 페이지와 기존 Roles DB를 삭제했다.
- 현재 기대 구조는 운영 프로젝트 페이지의 하나의 container와 Jobs·Trends 두 data source뿐이다.
- `notion_job_migration.py`의 이전 함수와 이전 계획 문서는 호환성·시험·변경 이력 확인용이다. 현재 운영 Notion에 자동 재실행하지 않는다.
- 이후 구조를 바꾸려면 읽기 전용 snapshot과 변경 목록을 먼저 만들고 사용자 승인을 받는다. 누락된 것처럼 보이는 보관 페이지나 Roles DB를 자동 생성하지 않는다.

변경 중 실패하면 이미 바꾼 항목을 자동 삭제하거나 다른 container로 옮기지 않는다. 성공한 단계, 실패한 단계와 영향을 받은 대상을 보고하고 사용자의 판단을 기다린다.

## Job Discovery 행 저장

1. 실행 직전에 `config.toml`의 `jobs_database_id`와 운영 Jobs data source 식별자가 같은지 확인한다.
2. 운영 Jobs의 26개 속성명·유형과 Select·Multi-select 옵션을 읽어 `JobsDatabaseSnapshot`을 만든다.
   - Notion schema 조회에서 Rich text 속성 유형은 `text`로 반환된다. 행 생성 payload의 `rich_text` 키와 혼동하지 않고 schema snapshot에는 조회값인 `text`를 사용한다.
3. `build_notion_job_pages`로 `적합`과 `검토 필요` 공고 전체를 먼저 변환한다. `제외`와 `중복`은 행으로 만들지 않는다.
4. 공고에 필요한 기술 키워드가 운영 옵션에 없으면 쓰기를 시작하지 않는다. 필요한 옵션과 대상 공고를 사용자에게 보여주고 schema 변경 승인을 별도로 받는다.
5. 저장 대상, 검토 필요, 제외와 중복 건수를 사용자에게 보여주고 행 생성 승인을 받는다.
6. 승인 뒤 `apply_job_discovery_plan`으로 검증된 data source에 행을 만든다. 한 건이 실패하면 이후 쓰기를 중단하고 이미 생성된 URL과 실패 URL을 보고한다.
7. 생성된 행을 다시 조회해 URL, 공고명, 검토 상태와 건수를 대조한다. 재조회하기 전에는 저장 완료로 보고하지 않는다.

## Trend Update 행 저장

1. 실행 직전에 `trends_database_id`와 운영 Trends data source 식별자가 같은지 확인한다.
2. 13개 속성명·유형과 모든 Select·Multi-select 옵션을 `TrendsDatabaseSnapshot`으로 만든다.
3. 전체 관찰값을 먼저 변환하고 기존 URL 중복을 제외한다.
4. 필요한 `관련 직무` 또는 `기술 키워드` 선택지가 없으면 행을 만들지 않고 schema 변경 승인을 별도로 받는다.
5. 저장 후보와 건너뛸 URL을 보여주고 승인받은 뒤 `apply_trend_update_plan`을 실행한다.
6. 생성 결과를 다시 조회해 제목·원문 URL·건수를 대조한다.

## Notion 표시값

Python 내부 enum과 Agent JSON 계약은 영어 값을 사용한다. Notion 입출력 경계에서만 한글 표시값으로 변환한다.

- `AI`, `Security`, `AI × Security`, `GitHub`, `Saramin`, `JobKorea`, `Wanted`, `Jumpit`은 유지한다.
- 그 밖의 상태와 유형 옵션은 승인된 schema의 한글값을 사용한다.
- 원문 URL은 저장용 값을 임의로 다시 쓰지 않는다. 원문에서 확인한 canonical URL이 있을 때만 대표 URL로 사용한다.
