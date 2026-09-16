# Role Discovery Agent Contract

이 계약은 `ai_role_researcher`, `security_role_researcher`, `ai_security_role_researcher`가 공통으로 지킬 입력, 근거, 출력 경계를 정의합니다. Skill과 부모 workflow가 기준을 통제하고 각 Agent는 할당된 영역의 조사 방법만 자율적으로 선택합니다.

## 부모 workflow가 제공할 입력

- `category`: AI, Security, AI × Security 중 Agent에 고정된 하나
- `run_id`: 한 번의 Role Discovery 실행을 식별하는 세 Agent 공통 값
- `search_start`, `search_end`: Asia/Seoul 기준 시작일과 종료일
- `job_market`: 반드시 South Korea
- `search_query`: Python `build_agent_search_tasks`가 해당 영역에 생성한 질의
- `preferred_sources`: Employer career pages, Saramin, JobKorea, Wanted, Jumpit
- `existing_roles`: 실행 시작 전에 조회한 모든 Role Name과 Status의 고정된 목록

입력이 없거나 `category` 또는 `job_market`이 Agent의 범위와 다르면 임의로 보완하지 말고 `blockers`에 기록해 반환합니다.

## 공통 조사 규칙

- 기업 공식 채용 페이지를 먼저 확인하고 국내 채용 플랫폼을 다음으로 확인합니다. 출처 목록은 완전한 허용 목록이 아닙니다.
- 다른 국내외 채용 사이트도 사용할 수 있지만 공고 원문에서 근무지가 대한민국임을 확인하고, 가능하면 기업 원본 공고를 함께 검증합니다.
- 해외 근무, 근무지 불명확, 원본 Published Date 미확인, 검색 기간 밖의 공고는 후보 근거에서 제외합니다.
- 검색엔진 수집일, 접속일, 현재 모집 중이라는 상태를 Published Date로 사용하지 않습니다.
- 채용 정보가 아닌 해외 공식 문서·기업 블로그·보고서·논문은 보조 맥락으로 사용할 수 있습니다. 커뮤니티·소셜·익명 자료는 제외합니다.
- Experience Level은 공고 원문에 명시된 내용만 신입, 경력, 신입·경력, 미확인 중 하나로 정규화합니다.
- 기존 Candidate, Approved, Rejected와 정규화된 Role Name이 같은 관찰 결과는 `existing_matches`로 반환합니다.
- 같은 실행에서 발견한 새 직무를 추가 검색의 seed로 사용하지 않습니다.
- Agent는 Candidate 여부를 확정하지 않습니다. 관찰 결과와 근거만 반환하며 최종 후보 검증은 부모 workflow의 `select_new_candidates`가 수행합니다.
- `observations`에는 `key_responsibilities`와 `required_skills`를 각각 1개 이상 원문에서 확인하고, 서로 다른 원본 근거 URL 2개 이상을 확보한 항목만 넣습니다. 두 근거 중 하나 이상은 대한민국 `Job Posting`이어야 합니다.
- 위 요건을 채우지 못한 항목은 값을 추측하거나 빈 목록으로 반환하지 않습니다. 확인한 공고 URL을 `exclusions`에 `other`로 기록합니다.

## 출력 계약

부모 workflow가 병합할 수 있도록 아래 키를 가진 하나의 JSON 객체만 반환합니다. JSON 앞뒤에 설명문이나 Markdown 코드 블록을 추가하지 않습니다. 값의 설명은 한국어로 작성하되 속성명과 enum 값은 아래 표기를 유지합니다.

- `run_id`, `agent_name`, `category`, `job_market`
- `search_period`: `start`, `end`를 `YYYY-MM-DD`로 가진 객체
- `sources_checked`: 확인한 원본 URL 수
- `exclusions`: 제외한 각 URL과 `overseas`, `unclear_location`, `missing_published_date`, `outside_period`, `domain_mismatch`, `other` 중 하나인 사유
- `observations`: 각 항목에 `role_name`, `suggested_category`, `description`, `key_responsibilities`, `required_skills`, `team_description`, `product_context`, `discovery_reason`, `experience_level`, `evidence_sources` 포함
- `evidence_sources`: 각 항목에 `name`, `url`, `published_on`, `source_type`, Job Posting이면 `job_location`, `job_market` 포함
- `existing_matches`: `observed_role_name`, `existing_role_name`, `existing_status`
- `blockers`: 누락 입력, 접근 실패, 상충 근거처럼 부모 workflow가 알아야 할 문제

날짜와 enum 값은 위 표기를 그대로 사용합니다. 부모 workflow는 Agent 응답을 `parse_agent_discovery_result`로 변환한 뒤에만 병합합니다. 필수 키가 없거나 형식이 다르면 해당 실행을 실패로 처리합니다.

후보가 없으면 빈 `observations`를 반환합니다. 값을 추측하거나 최소 후보 수를 맞추지 않습니다. Notion 쓰기, Status 변경, Trend Update, 프로젝트 파일 수정은 수행하지 않습니다.

부모 workflow는 같은 `run_id`의 세 영역 결과가 모두 성공한 뒤에만 병합합니다. Agent 누락, 중복, `blockers` 존재 또는 다른 실행 결과 혼입이 있으면 부분 결과를 Candidate로 처리하지 않습니다.
