# Job Discovery Notion 이전 계획

> **상태 — 역사 기록:** 2026-09-20에 이 계획에 따른 이전을 완료했고, 2026-09-21에 Trends 원본 data source의 소유 위치를 운영 container로 옮긴 뒤 보관 페이지와 기존 Roles DB를 삭제하는 최종 정리를 마쳤다. 아래 1~10절은 당시 확인값과 적용 절차이므로 운영 Notion에 다시 실행하지 않는다. 현재 점검과 변경은 [Notion 데이터베이스 지침](notion-databases.md)을 따른다.

## 1. 목적과 실행 경계

이 문서는 운영 Notion을 읽기 전용으로 확인한 결과를 바탕으로 Roles·Trends 구조를 Jobs·Trends 구조로 안전하게 전환하는 계획이다. 이 문서 작성 단계에서는 database, data source, view, page와 `config.toml`을 변경하지 않는다.

실제 적용은 다음 조건을 모두 만족한 뒤 별도 사용자 승인을 받아 진행한다.

- 새 schema와 속성 변환 코드의 자동 시험 통과
- 적용 직전 운영 data source와 행 수 재조회
- 생성·이전·보관 대상의 명시적 승인
- 기존 데이터를 삭제하지 않는 복구 경로 확인

## 2. 2026-09-20 당시 읽기 전용 확인 결과

연결된 workspace와 `config.toml`의 프로젝트 페이지·두 data source가 일치하고 모두 조회된다.

### 운영 화면

- 프로젝트 페이지 제목: `AI Security Career Tracker`
- 운영 database container: `Roles DB`
- 운영 database는 두 data source를 탭으로 표시한다.
  - `Roles` view → `Roles DB` data source
  - `Trends` view → `Trends DB` data source
- `Roles DB` data source: 10개 속성, 1개 행
- `Trends DB` data source: 10개 속성, 0개 행

### 보관 화면

- `AI Security Career Tracker 보관` 페이지가 존재한다.
- `Trends DB`의 원본 database container와 `테스트 초기화 보관 — 2026-09-18` 페이지가 있다.
- 운영 화면의 `Trends` 탭과 보관 화면의 `Trends DB`는 같은 data source를 가리킨다. 별도 복제본이 아니다.

### 기존 Roles 행

`기술 보안 엔지니어 채용` 1건이 있으며 다음 사실을 보존해야 한다.

- 기업: 피아스페이스(주)
- 원문 공고명: 기술 보안 엔지니어 채용
- 분야: Security
- 경력 수준: 경력
- 근무지: 서울 서초구
- 채용 공고 URL: Saramin 공고
- 보조 확인 URL: 피아스페이스의 AI 영상분석 솔루션 관련 기사
- 최초 발견일과 최근 검토일: 2026-09-18
- 게시일 기록: 2026-09-08이나 조사 Agent 사이에 확인 충돌이 있었음
- 원문 전문의 상세 책임·요건을 다시 확인해야 한다는 기존 경고

따라서 이 행은 자동으로 `적합`으로 확정하지 않고 새 Jobs data source의 `검토 필요` 행으로 이전한다.

## 3. 당시 목표 운영 구조

프로젝트 페이지에는 하나의 새 inline database container를 두고 다음 두 탭을 표시한다.

1. `Jobs`: 새 Jobs data source의 기본 table view
2. `Trends`: 기존 Trends data source를 연결한 table view

기존 `Roles DB` container는 이전 검증이 끝날 때까지 그대로 유지한다. 검증 완료 뒤 삭제하지 않고 `AI Security Career Tracker 보관` 페이지로 이동한다. 기존 Roles 행과 이전 당시 schema는 그 안에 보존한다.

새 운영 container를 먼저 만든 뒤 기존 container를 옮기므로, 적용 중 실패해도 기존 운영 화면으로 돌아갈 수 있다.

## 4. Jobs data source schema

| 속성 | 형식 | 옵션 또는 저장 규칙 |
| --- | --- | --- |
| 공고명 | Title | 원문 공고명 |
| 회사명 | Rich text | 원문 기업명 |
| 인식한 직무 | Rich text | 공고 본문에서 인식한 직무 설명 |
| 직무 분야 | Select | AI, Security, AI × Security |
| 검토 상태 | Select | 적합, 검토 필요 |
| 경력 수준 | Select | 신입, 경력, 신입·경력, 미확인 |
| 주요 업무 | Rich text | 원문에서 확인한 업무 |
| 자격 요건 | Rich text | 원문에서 확인한 필수·우대 요건 |
| 기술 키워드 | Multi-select | 기술·업무 키워드 |
| 근무지 | Rich text | 대한민국 내 원문 근무지 |
| 고용 형태 | Select | 정규직, 계약직, 인턴, 기타, 미확인 |
| 근무 방식 | Select | 출근, 하이브리드, 원격, 미확인 |
| 게시일 | Date | 없으면 비워 둠 |
| 마감일 | Date | 없으면 비워 둠 |
| 모집 상태 | Select | 모집 중, 마감, 미확인 |
| 관심 상태 | Select | 신규, 관심, 지원 예정, 지원, 제외 |
| 출처 유형 | Select | 기업 공식, Saramin, JobKorea, Wanted, Jumpit, 기타 |
| 원문 URL | URL | 대표 채용 공고 URL |
| 관련 URL | Rich text | 복제 공고와 보조 확인 URL을 줄 단위로 보존 |
| 게시일 상태 | Select | 확인, 미확인 |
| 공고 식별자 | Rich text | 플랫폼 또는 기업의 공고 ID |
| 검색 경로 | Multi-select | AI, Security, AI × Security |
| 수집일 | Date | Job Discovery 실행일 |
| 마지막 확인일 | Date | 모집 상태를 마지막으로 확인한 날짜 |
| 변경 상태 | Select | 신규, 변경됨, 변경 없음 |
| 검토 메모 | Rich text | 분류 근거, 접근 제한과 재확인 사항 |

기본 `Jobs` view에는 `공고명`, `회사명`, `인식한 직무`, `직무 분야`, `검토 상태`, `경력 수준`, `근무지`, `게시일`, `마감일`, `모집 상태`, `관심 상태`, `원문 URL`만 우선 표시한다. 나머지 속성은 삭제하지 않고 view에서 숨긴다.

## 5. Trends data source 변경

기존 Trends data source가 비어 있으므로 행 변환은 없다. 같은 data source 식별자를 재사용하고 다음 schema 변경만 적용한다.

| 현재 | 변경 |
| --- | --- |
| `핵심 시사점` Rich text | 이름을 `취업 시사점`으로 변경 |
| `관련 직무` Roles relation | 제거 후 `관련 직무` Multi-select 생성 |
| 없음 | `기술 키워드` Multi-select 추가 |
| 없음 | `동향 유형` Select 추가: 기술, 채용시장, 산업, 규제·정책, 위협·사고, 연구 |
| 없음 | `지역 범위` Select 추가: 국내, 해외, 글로벌 |

`제목`, `요약`, `출처 유형`, `출처명`, `원문 URL`, `게시일`, `수집일`, `관련 분야`는 유지한다. `출처 유형`의 기존 14개 옵션과 `관련 분야`의 AI, Security, AI × Security 옵션도 유지한다.

속성 유형을 relation에서 Multi-select로 직접 변환하지 않는다. 기존 행이 0개임을 적용 직전에 다시 확인하고, relation 속성을 제거한 뒤 같은 이름의 Multi-select를 만든다. 행이 생겼다면 중단하고 값별 이전 계획을 다시 작성한다.

## 6. 기존 1건의 속성 변환안

| Jobs 속성 | 이전 값 |
| --- | --- |
| 공고명 | 기술 보안 엔지니어 채용 |
| 회사명 | 피아스페이스(주) |
| 인식한 직무 | 기술 보안 엔지니어 |
| 직무 분야 | Security |
| 검토 상태 | 검토 필요 |
| 경력 수준 | 경력 |
| 주요 업무 | 기존 `주요 업무` 전문 보존 |
| 자격 요건 | 비움 — 원문 재확인 필요 |
| 기술 키워드 | VPN, Firewall, IAM, Endpoint Security, 보안 운영 |
| 근무지 | 서울 서초구 |
| 고용 형태 | 미확인 |
| 근무 방식 | 미확인 |
| 게시일 | 2026-09-08 |
| 마감일 | 비움 |
| 모집 상태 | 미확인 |
| 관심 상태 | 신규 |
| 출처 유형 | Saramin |
| 원문 URL | 기존 Saramin 채용 공고 URL |
| 관련 URL | 기존 보조 기사 URL 보존 |
| 게시일 상태 | 미확인 — 기존 기록에 확인 충돌이 있음 |
| 공고 식별자 | Saramin `rec_idx=54978708` |
| 검색 경로 | Security |
| 수집일 | 2026-09-18 |
| 마지막 확인일 | 2026-09-18 |
| 변경 상태 | 신규 |
| 검토 메모 | 기존 `직무 설명`, `메모`와 `근거 출처` 전문, 게시일 충돌·원문 재확인 경고 보존 |

게시일 값은 기존 기록을 보존하기 위해 옮기되, `검토 상태`와 `검토 메모`에 충돌 경고를 유지한다. 실제 비교 실사용 시험 전에 원문을 다시 열어 게시일과 모집 상태를 확인한다.

## 7. 당시 적용 순서

1. 코드에서 Jobs·Trends schema, 한글 옵션 매핑, Notion page 생성과 설정 키 이전을 구현하고 자동 시험을 통과시킨다.
2. 실제 적용 직전에 프로젝트 페이지, 보관 페이지, 두 data source schema와 행 수를 다시 조회한다.
3. 프로젝트 페이지에 새 inline database container와 Jobs data source를 만든다.
4. 기존 Trends data source를 새 container의 `Trends` 탭으로 연결한다.
5. 기존 Roles 1건을 위 변환안으로 Jobs에 복사한다. 기존 행은 수정하거나 삭제하지 않는다.
6. Jobs의 행 수, 원문 URL, 관련 URL, 업무·메모 전문과 핵심 옵션을 재조회해 원본과 대조한다.
7. Trends가 여전히 0건인지 확인한 뒤 승인된 schema 변경을 적용하고 다시 조회한다.
8. 새 container의 `Jobs`, `Trends` view와 표시 속성을 확인한다.
9. 검증이 모두 통과한 뒤에만 기존 `Roles DB` container를 보관 페이지로 이동한다.
10. 새 Jobs와 기존 Trends data source 식별자를 함께 `config.toml`에 저장한다. `roles_database_id`는 `jobs_database_id`로 명시적으로 교체하며 부분 저장을 허용하지 않는다.
11. 설치된 Skill을 새 버전으로 갱신하고 새 Codex 작업에서 두 식별자와 schema를 다시 확인한다.

## 8. 당시 중단 조건과 복구

다음 중 하나라도 발생하면 이후 쓰기를 중단한다.

- 운영 schema나 행 수가 이 문서와 달라짐
- 기존 Roles 행의 URL·업무·메모 전문을 읽을 수 없음
- 새 Jobs 행의 핵심 값이 원본과 다름
- Trends에 새 행이 생겨 relation 값을 별도로 보존해야 함
- 새 container에 기존 Trends data source를 연결할 수 없음
- 설정 식별자 한쪽만 저장되거나 기존 값과 충돌함

중단 시 새로 만든 container는 자동 삭제하지 않는다. 기존 운영 `Roles DB` container를 그대로 두고, 생성된 대상과 성공·실패 단계를 보고해 사용자가 판단할 수 있게 한다. 기존 Roles 행과 Trends data source는 모든 검증이 끝날 때까지 수정·삭제하지 않는다.

## 9. 당시 적용 완료 기준

- 프로젝트 페이지에서 `Jobs`와 `Trends` 두 탭이 보인다.
- Jobs에는 변환된 1건이 있고 원문 URL, 관련 URL, 주요 업무와 검토 메모가 보존된다.
- Trends는 기존 식별자를 유지하며 목표 13개 속성을 가진다.
- 기존 Roles container와 행은 보관 페이지에서 조회된다.
- `config.toml`에는 새 Jobs와 기존 Trends 식별자가 함께 저장된다.
- 새 Job Discovery 결과가 기존 Roles schema로 쓰이지 않는다.
- 재조회 결과와 작업일지에 실제 성공·실패 범위가 기록된다.

## 10. 1차 적용 결과 — 2026-09-20

- 프로젝트 페이지에 새 inline database container를 만들고 `Jobs`, `Trends` 두 탭을 구성했다.
- 기존 Roles 1건을 Jobs의 `검토 필요` 행으로 복사하고 원문 URL, 관련 URL, 주요 업무와 기존 경고를 재조회해 보존을 확인했다.
- Jobs의 `기술 키워드`에는 이전 행 저장에 필요한 VPN, Firewall, IAM, Endpoint Security, 보안 운영 선택지를 추가했다.
- Trends가 0건임을 다시 확인한 뒤 `관련 직무`를 Multi-select로 전환하고 `기술 키워드`, `동향 유형`, `지역 범위`를 추가했다.
- 기존 Roles container와 원본 행은 삭제하지 않고 보관 페이지로 이동했다.
- 로컬 설정은 새 Jobs 식별자와 기존 Trends 식별자를 함께 사용하도록 전환했다. 실제 식별자는 Git에서 제외되는 `config.toml`에만 저장한다.

## 11. 최종 정리 결과 — 2026-09-21

- Trends 원본 data source의 소유 위치를 운영 database container로 옮겼다. 이전 보관 container의 기본 view는 옮기지 않았다.
- 운영 프로젝트 페이지에서 `Jobs`, `Trends` 두 탭과 각 data source 접근을 다시 확인했다.
- Jobs 18건과 Trends 6건이 유지되는지 재조회했다.
- 이전된 Roles 1건이 Jobs의 `검토 필요` 행으로 남아 있는 상태에서 `AI Security Career Tracker 보관` 페이지와 그 아래 기존 Roles DB를 삭제했다.
- 현재 운영 구조에는 보관 페이지와 Roles DB가 없으며, 이후 workflow에서 이를 다시 만들거나 이 이전 계획을 재실행하지 않는다.
