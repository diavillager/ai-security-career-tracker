# Notion 데이터베이스 설정

이 절차는 확인된 `AI Security Career Tracker` 프로젝트 페이지 아래에서만 사용한다. 목표 schema와 기존 1건의 변환값은 [Job Discovery Notion 이전 계획](notion-job-discovery-migration-plan.md)을 기준으로 한다.

## 목표 구조

운영 화면에는 하나의 inline database container와 두 탭을 둔다.

- `Jobs`: 대한민국 채용 공고를 공고별로 저장하는 Jobs data source
- `Trends`: AI, Security, AI × Security 분야 동향을 저장하는 Trends data source

Jobs와 Trends는 서로 독립적이다. Trends의 `관련 직무`는 Jobs relation이 아니라 직무 유형을 담는 Multi-select이다.

## 안전한 확인과 재사용

1. 연결된 Notion workspace와 사용자를 확인한다.
2. `config.toml`의 프로젝트 페이지, Jobs·Trends 식별자를 읽는다.
3. 저장된 식별자가 있으면 해당 data source의 제목, 필수 속성, 속성 유형과 옵션을 조회한다.
4. 식별자가 없으면 새로 만들기 전에 프로젝트 페이지와 보관 페이지에서 기존 database와 data source를 찾는다.
5. 제목이 같거나 연결된 data source가 여러 개면 URL, parent와 schema를 함께 확인해 대상을 구분한다.
6. 식별자가 하나만 있거나 접근할 수 없거나 schema가 다르면 대체 database를 자동 생성하지 않고 중단한다.

`config.toml`에는 data source 식별자가 저장되지만 기존 설정 키는 `*_database_id` 이름을 사용했다. 전환할 때 `roles_database_id`를 `jobs_database_id`로 바꾸고 기존 `trends_database_id`는 검증된 기존 Trends 식별자를 유지한다. 두 값을 한 번에 검증·저장하며 부분 저장을 허용하지 않는다.

## 생성과 이전

1. 적용 직전에 운영·보관 페이지, 기존 Roles·Trends schema와 행 수를 다시 조회한다.
2. 새 inline database container와 Jobs data source를 만든다.
3. 기존 Trends data source를 새 container의 `Trends` 탭으로 연결한다.
4. 기존 Roles의 실제 채용 공고 행만 Jobs schema로 복사한다. 원본 행을 수정하거나 삭제하지 않는다.
5. 새 Jobs 행을 재조회해 URL, 본문과 옵션이 원본 변환 계획과 일치하는지 확인한다.
6. Trends 행 수를 다시 확인한 뒤 승인된 schema 변경을 적용한다. 기존 행이 있으면 relation 제거 전에 별도 변환 계획을 작성한다.
7. 두 view와 표시 속성을 확인한 뒤에만 기존 Roles container를 보관 페이지로 이동한다.
8. 새 Jobs와 기존 Trends 식별자를 함께 저장하고 새 Codex 작업에서 재조회한다.

중간 실패 시 새로 만든 항목을 자동 삭제하거나 기존 운영 container를 옮기지 않는다. 성공한 단계, 실패한 단계와 생성된 대상을 보고하고 사용자의 판단을 기다린다.

## Notion 표시값

Python 내부 enum과 Agent JSON 계약은 영어 값을 사용한다. Notion 입출력 경계에서만 한글 표시값으로 변환한다.

- `AI`, `Security`, `AI × Security`, `GitHub`, `Saramin`, `JobKorea`, `Wanted`, `Jumpit`은 유지한다.
- 그 밖의 상태와 유형 옵션은 승인된 schema의 한글값을 사용한다.
- 원문 URL은 저장용 값을 임의로 다시 쓰지 않는다. 원문에서 확인한 canonical URL이 있을 때만 대표 URL로 사용한다.
