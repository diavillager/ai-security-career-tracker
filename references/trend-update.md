# Trend Update 절차

Trend Update는 실행을 시작할 때 `Approved`인 직무만 기준으로 최근 동향을 수집해 기존 Trends DB에 추가합니다. 같은 실행 중 새로 승인되거나 발견된 직무는 검색 범위에 넣지 않습니다.

## 입력 확정

1. 연결된 Notion workspace, 프로젝트 페이지, Roles DB와 Trends DB가 `config.toml`의 식별자 및 필수 구조와 일치하는지 확인합니다.
2. Roles DB의 page ID, `직무명`, `직무 분야`, `상태`를 한 번 조회합니다.
3. Python `select_approved_roles`로 `Approved` 직무 snapshot을 확정합니다. `Candidate`와 `Rejected`는 검색과 `관련 직무` 연결에서 제외합니다.
4. Trends DB에서 기존 `원문 URL`을 조회해 정규화된 비교 키를 만듭니다.
5. 기간이 없으면 오늘을 마지막 날로 하는 최근 7일을 사용합니다.

`Approved` 직무가 없으면 검색하거나 Trends DB에 쓰지 않고 결과를 그대로 보고합니다.

## 웹 검색과 출처 기준

1. `build_trend_search_tasks`로 `Approved` 직무마다 검색 작업을 만듭니다.
2. Codex 웹 검색으로 기술, 산업, 연구, 제품과 보안 동향을 찾습니다. 비채용 정보는 해외 출처도 사용할 수 있습니다.
3. Reddit, Hacker News, 소셜 네트워크, 일반 포럼과 익명 게시물은 제외합니다.
4. 원문에서 게시일을 확인할 수 없거나 검색 기간 밖이면 제외합니다. 검색엔진 표시일이나 접속일을 게시일로 대신하지 않습니다.
5. Job Posting을 사용하는 경우 공고 원문에서 근무지가 대한민국임을 확인합니다. 근무지가 해외이거나 불명확하면 제외합니다.
6. 제목, 사실 중심의 `요약`, 직무 변화에 주는 의미인 `핵심 시사점`, 출처 유형·이름, `원문 URL`, 게시일, 관련 직무, 하나 이상의 영역과 본문 근거를 설명하는 `classification_basis`를 구조화합니다. 원문에서 `<link rel="canonical">`을 직접 확인한 경우에만 선택적인 `canonical_url`을 기록합니다.
7. `관련 직무`는 제목 exact match만으로 정하지 않고 원문 본문, 책임, 기술과 제품 맥락을 근거로 실행 시작 시점의 Approved 직무 중에서 선택합니다. 관련된 직무가 여러 개면 모두 포함합니다.

구조화된 결과는 `parse_trend_observations`를 통과해야 합니다. 검색 결과의 설명이나 요약 페이지가 아니라 실제 원문 URL을 보존합니다.

## 검증과 중복 처리

1. `plan_trend_update`로 모든 항목을 먼저 검증합니다.
2. `관련 직무`에 포함된 모든 직무가 실행 시작 snapshot에서 `Approved`였는지 확인합니다.
3. `관련 분야`는 AI, Security, AI × Security 중 하나 이상이어야 하며 중복될 수 없습니다. AI × Security 직무는 세 영역을 모두 뒷받침하고, AI 직무와 Security 직무가 함께 연결되면 AI × Security 영역을 뒷받침할 수 있습니다.
4. `관련 직무`가 중복되지 않고 모두 실행 시작 snapshot의 Approved 직무인지 확인합니다. 분류와 무관한 직무는 과도하게 연결하지 않습니다.
5. `요약`과 `핵심 시사점`은 각각 원문의 사실 요약과 직무 관련 해석으로 작성하며 동일한 값을 복제하지 않습니다.
6. 기간, 출처 종류, 커뮤니티 제외와 대한민국 Job Posting 조건을 검사합니다.
7. `normalize_source_url`로 scheme·host·기본 port·query 순서를 정리하고 fragment와 알려진 추적 매개변수를 비교 키에서 제거합니다. 원문에서 확인한 canonical URL이 있으면 비교 키와 저장 URL에 우선 사용합니다.
8. Trends DB에 정규화 후 같은 `원문 URL`이 있으면 새 page를 만들지 않고 건너뛴 URL로 보고합니다.
9. 한 실행 결과 안에 정규화 후 같은 URL이 두 번 있으면 자동으로 하나를 고르지 않고 오류로 처리합니다.

정규화는 비교에 필요한 최소 범위만 적용합니다. 원본 URL은 임의로 다시 쓰지 않으며, 경로·의미 있는 query 값·`http`와 `https`·서로 다른 host는 합치지 않습니다. 제목이나 내용이 비슷한 서로 다른 URL의 의미 기반 이벤트 중복 판정은 MVP 범위에서 수행하지 않습니다.

## Notion 필드 연결

`build_notion_trend_pages`는 검증이 끝난 항목을 다음 속성으로 변환합니다.

- `제목`: 원문 제목
- `요약`: 원문의 간결한 요약
- `핵심 시사점`: 연결된 직무에 중요한 이유
- `출처 유형`: 뉴스, 업계 매체, 기업 블로그, 기술 블로그, 보도자료, 채용 공고, 공식 문서, 연구 보고서, 뉴스레터, GitHub, 논문, 컨퍼런스, 정부, 기타 중 하나. Agent 계약과 내부 enum은 대응하는 영어 값을 유지합니다.
- `출처명`: 발행자 또는 기관
- `원문 URL`: 원문에서 직접 확인한 canonical URL이 있으면 그 URL, 없으면 확인한 원본 URL
- `게시일`: 원문에서 확인한 게시일
- `수집일`: 실행일
- `관련 직무`: 실행 시작 시점에 Approved였던 Roles DB page relation
- `관련 분야`: AI, Security, AI × Security 중 하나 이상을 `Multi-select`로 저장

기존 Trends DB의 `관련 분야`가 단일 `Select`이면 page를 쓰기 전에 schema 변경 대상을 사용자에게 보여주고 승인을 받습니다. schema가 맞지 않는 상태에서 page 생성을 시도하거나 대체 Trends DB를 만들지 않습니다.

실제 Notion 쓰기 직전에 새로 만들 항목과 건너뛸 URL을 사용자에게 보여주고 확인을 받습니다. 확인 뒤 `apply_trend_update_plan`으로 검증된 page만 만듭니다.

`TrendApplyError`가 발생하면 이미 생성된 URL과 실패한 URL을 구분해 보고하고 Trends DB를 다시 조회합니다. 자동 재시도하거나 이미 생성된 page를 자동 삭제하지 않습니다.
