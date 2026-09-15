---
name: ai-security-career-tracker
description: Notion에서 새로운 AI, Security, AI Security 직무를 발견하고 사용자 승인 상태를 관리하며, 승인된 직무의 최근 동향을 수집합니다. Role Discovery, 후보 검토, 승인·거절 변경, 승인된 직무의 Trend Update에 사용하며 일반적인 취업 상담이나 무관한 보안 뉴스에는 사용하지 않습니다.
---

# AI Security Career Tracker

AI, Security, AI × Security 영역에서 변화하는 직무를 추적하되, 직무 발견과 동향 수집을 분리합니다.

## 현재 개발 범위

MVP 기본 구조, Notion 데이터베이스 설정, Role Discovery까지 구현됐습니다. 승인·거절 변경과 Trend Update는 아직 구현되지 않았으므로 구현됐다고 안내하지 않습니다.

## 언어 지침

- PR 제목·설명·검토 코멘트는 한국어로 작성합니다.
- 커밋 메시지는 feat:, fix:, docs:, test: 같은 영어 유형 뒤에 한국어 설명을 작성합니다.
- SKILL.md와 사용자가 읽는 참고 문서의 설명은 한국어로 작성합니다.
- Skill 이름, 기능명, Notion 속성·상태값, 브랜치명, 코드 식별자, 설정 키, 명령어는 영어 원문을 유지합니다.

## 확정된 제품 규칙

- 자연어 요청을 Role Discovery, 승인·거절 또는 Trend Update로 해석합니다.
- 사용자가 기간을 지정하지 않으면 최근 7일을 사용합니다.
- Codex 웹 검색을 기본 검색 수단으로 사용합니다.
- 검색 수단별 가정을 전체 흐름에 넣지 말고, 나중에 교체할 수 있는 경계로 분리합니다.
- 기본 검색 범위에는 AI, Security, AI × Security를 모두 포함합니다.
- Role Discovery와 모든 채용·구인구직 정보는 근무지가 대한민국으로 확인된 공고로 한정합니다. 채용 정보가 아닌 해외 정보는 허용합니다.
- 기업 공식 채용 페이지와 Saramin, JobKorea, Wanted, Jumpit 같은 국내 채용 플랫폼을 우선합니다. 이 목록은 완전한 허용 목록이 아니라 우선순위입니다.
- 채용 근거가 신입, 경력, 신입·경력 또는 미확인 중 어디에 해당하는지 기록합니다.
- 새 직무는 Status Candidate로 저장합니다. 사용자가 승인하기 전에는 Trend Update에 사용하지 않습니다.
- Rejected 직무는 삭제하지 않고 검토 기록으로 보존합니다.
- 저장한 모든 직무와 동향에 원본 출처 URL을 보존합니다.
- MVP의 중복 판정은 정규화된 URL 또는 canonical URL의 동일 여부만 사용합니다.

기능을 구현하거나 변경하기 전에 [references/product-requirements.md](references/product-requirements.md)를 읽습니다.

## Notion 데이터베이스 설정

프로젝트 데이터베이스를 만들거나 확인하거나 다시 연결할 때는 [references/notion-databases.md](references/notion-databases.md)를 읽습니다.

- 쓰기 작업 전에 연결된 workspace와 프로젝트 페이지를 확인합니다.
- 먼저 config.toml을 확인합니다. 두 데이터베이스 식별자가 모두 저장돼 있으면 해당 데이터베이스를 조회해 재사용합니다.
- 식별자가 모두 없으면 새로 만들기 전에 프로젝트 페이지에 기존 Roles DB와 Trends DB가 있는지 확인합니다.
- 설정에 식별자가 하나만 있거나, 저장된 식별자에 접근할 수 없거나, 데이터베이스 구조가 다르면 작업을 중단합니다. 대체 데이터베이스를 만들지 말고 상황을 보고합니다.
- 먼저 Roles DB를 만들고, 이후 Related Roles가 Roles data source를 가리키는 Trends DB를 만듭니다.
- 두 구조를 모두 검증한 다음에만 python src/ai_security_career_tracker/notion_databases.py로 두 data source 식별자를 함께 저장합니다.

## Role Discovery

검색 계획, 근거 요건, Notion 필드 연결, 결과 보고 기준은 [references/role-discovery.md](references/role-discovery.md)를 읽습니다.

- 요청에 기간이 없으면 오늘을 마지막 날로 하는 최근 7일을 사용합니다.
- 검색 전에 모든 기존 Role Name과 Status를 불러옵니다. Candidate, Approved, Rejected는 모두 정규화된 Role Name이 같은 새 Candidate 생성을 막습니다.
- seed 이름과 책임 관련 검색어를 사용해 AI, Security, AI × Security를 각각 검색합니다. seed는 발견을 돕지만 허용 목록으로 사용하지 않습니다.
- 대한민국 채용시장을 한국어와 영어로 검색합니다. 기업 공식 채용 페이지를 먼저 보고 Saramin, JobKorea, Wanted, Jumpit 같은 국내 채용 플랫폼을 다음으로 확인합니다. 이 순서는 우선순위이지 완전한 허용 목록이 아닙니다.
- 다른 국내외 채용 사이트는 공고 원문에서 근무지가 대한민국임을 확인한 경우에만 사용합니다. 가능하면 글로벌 집계 사이트 하나에 의존하지 말고 기업의 원본 채용 공고와 함께 검증합니다.
- 허용된 공식 또는 편집 출처는 보조 맥락에 사용합니다. 해외 출처는 채용 정보가 아닌 경우에만 허용하고 커뮤니티와 소셜 출처는 제외합니다.
- 검색 기간 안의 원본 Published Date를 요구합니다. 검색엔진 수집일, 접속일, 현재 모집 중이라는 상태로 대신하지 않으며 게시일이 없는 자료는 제외합니다.
- 직무명뿐 아니라 책임, 기술, 팀, 제품 맥락을 함께 평가합니다. 직무명만으로 분류하지 않습니다.
- 채용 근거에 명시된 Experience Level을 신입, 경력, 신입·경력, 미확인 중 하나로 추출합니다. 직무명만으로 추정하지 않습니다.
- 충분한 근거가 있는 새 직무만 Status Candidate로 저장합니다. 서로 다른 출처를 최소 2개 요구하고 그중 하나 이상은 대한민국 근무가 확인된 채용 공고여야 하며, 모든 출처 이름과 원본 URL을 보존합니다.
- 실행 전에 조회한 Approved 직무 목록은 실행 중 바꾸지 않습니다. 같은 실행에서 Trend Update를 시작하거나 새 Candidate를 검색어로 사용하지 않습니다.
- 사용자가 검토할 수 있도록 번호가 붙은 후보와 기존 직무 일치 항목을 구분해 보고합니다.

## 승인 경계

- 데이터베이스를 만들거나 변경하기 전에 연결된 Notion workspace와 대상 프로젝트 페이지를 확인합니다.
- 저장된 데이터베이스 식별자가 없거나 접근할 수 없을 때 대체 데이터베이스를 만들지 않습니다. 상황을 보고하고 사용자가 기존 데이터베이스를 지정하도록 요청합니다.
- Candidate 또는 Rejected 직무를 Trend Update 검색에 추가하지 않습니다.
- 사용자의 명시적 승인 없이 feature branch를 main에 병합하지 않습니다.
- 인증정보를 저장소 파일, 로그, 커밋 또는 PR 본문에 저장하지 않습니다.
