# Trend Update 절차

Trend Update는 Jobs DB와 보관된 Roles DB의 상태를 입력으로 사용하지 않고 AI, Security, AI × Security 분야를 직접 조사합니다.

## 입력 확정

1. 연결된 Notion workspace, 프로젝트 페이지와 Trends DB가 `config.toml`의 식별자와 일치하는지 확인합니다.
2. Trends DB의 기존 `원문 URL`을 읽어 정규화 비교 키를 만듭니다.
3. 기간이 없으면 오늘을 마지막 날로 하는 최근 7일을 사용합니다.
4. `build_trend_search_tasks`로 AI, Security, AI × Security의 세 검색 작업을 만듭니다. Jobs나 Roles snapshot은 읽지 않습니다.

## 웹 검색과 출처 기준

- Codex 웹 검색으로 기술·산업·연구·제품·정책·위협·사고·채용시장 동향을 찾습니다.
- 비채용 자료는 국내외 출처를 사용할 수 있습니다. Reddit, Hacker News, 소셜 네트워크, 일반 포럼과 익명 게시물은 제외합니다.
- 원문 게시일을 확인할 수 없거나 요청 기간 밖이면 제외합니다. 검색 결과 표시일이나 접속일을 대신 쓰지 않습니다.
- 채용 공고를 동향 근거로 쓸 때만 원문에서 대한민국 근무지를 확인합니다. 해외 또는 불명확한 근무지는 제외합니다.
- 원문에서 직접 확인한 canonical URL이 있을 때만 `canonical_url`을 기록합니다.

## 구조와 검증

각 관찰값은 제목, 사실 중심 `summary`, 취업 관점의 `career_insight`, 출처 유형·이름, 원문 URL, 게시일, `related_roles`, 하나 이상의 `domains`와 `technology_keywords`, `trend_type`, `region_scope`, `classification_basis`를 포함합니다.

1. `parse_trend_observations`가 JSON 구조와 enum을 검사합니다.
2. `plan_trend_update`가 게시 기간, 차단 출처, 필수 분류값과 URL 중복을 검사합니다.
3. `관련 직무`는 특정 DB relation이 아니라 원문으로 영향을 확인한 직무 유형 이름입니다. 제목 exact match만으로 정하지 않습니다.
4. `요약`과 `취업 시사점`은 각각 사실과 취업 관련 해석으로 분리하며 같은 문장을 복제하지 않습니다.
5. 기존 Trends의 정규화 URL과 같으면 건너뜁니다. 한 실행 안의 중복 URL은 임의로 하나를 고르지 않고 오류로 처리합니다.

## Notion 저장

`build_notion_trend_pages`는 다음 13개 속성을 만듭니다.

- `제목`, `요약`, `취업 시사점`
- `출처 유형`, `출처명`, `원문 URL`, `게시일`, `수집일`
- `관련 직무` Multi-select, `관련 분야` Multi-select, `기술 키워드` Multi-select
- `동향 유형`, `지역 범위`

저장 직전에 설정 식별자, 13개 속성 유형과 모든 Select·Multi-select 선택지를 `TrendsDatabaseSnapshot`으로 재검증합니다. 필요한 직무나 기술 키워드 선택지가 없으면 행 생성 전에 변경 목록을 보여주고 별도 승인을 받습니다.

새 항목과 중복으로 건너뛸 URL을 사용자에게 보여주고 승인받은 뒤 `apply_trend_update_plan`으로 생성합니다. 실패하면 이미 생성된 URL과 실패 URL을 구분해 보고하며 자동 재시도나 자동 삭제를 하지 않습니다. 생성 뒤 Trends를 재조회해 제목·원문 URL·건수를 확인합니다.
