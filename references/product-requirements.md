# MVP 제품 요구사항

## 기능 구분

Role Discovery는 새로운 Role Name을 발견하고 새 직무만 Candidate로 저장합니다. Trend Update는 현재 Status가 Approved인 직무만 사용합니다. 한 번의 Role Discovery 실행에서 발견한 Candidate를 같은 실행의 추가 검색어로 재귀적으로 사용하지 않습니다.

## 기본 동작

- JSON이나 명령줄 형식을 요구하지 않고 자연어 요청을 받습니다.
- 기간이 지정되지 않으면 최근 7일을 적용합니다.
- 기본 검색 범위는 AI, Security, AI × Security입니다.
- Codex 웹 검색을 초기 검색 수단으로 사용합니다.
- 직무명에만 의존하지 않고 책임, 기술, 팀 맥락, 제품 맥락을 평가합니다.
- Role Discovery와 모든 채용·구인구직 근거는 근무지가 대한민국으로 명시된 공고로 한정합니다. 회사의 국적이나 전 세계에서 접속 가능한 공고라는 사실만으로는 충분하지 않습니다.
- Role Discovery에서는 기업 공식 채용 페이지와 Saramin, JobKorea, Wanted, Jumpit 같은 국내 채용 플랫폼을 우선합니다. 이는 출처 우선순위이며 완전한 허용 목록이 아닙니다.
- 다른 국내외 채용 사이트는 공고 자체에서 대한민국 근무지를 확인할 수 있을 때만 사용하고, 가능하면 기업 원본 공고와 함께 검증합니다. 글로벌 채용 집계 사이트를 최초 검색 대상으로 사용하지 않습니다.
- 기술, 산업, 연구, 제품, 보안 동향처럼 채용 정보가 아닌 자료에는 해외 출처를 허용합니다.
- MVP에서는 Reddit, Hacker News, 소셜 네트워크, 일반 포럼, 익명 게시물 같은 커뮤니티 출처를 제외합니다.
- 원본 Published Date를 확인할 수 없는 자료는 제외합니다.
- Experience Level은 직무명으로 추정하지 않고 공고에 명시된 근거를 사용해 신입, 경력, 신입·경력, 미확인 중 하나로 기록합니다.
- Candidate에는 독립 근거가 2개 이상 필요합니다. 같은 회사의 같은 직무 공고가 여러 채용 플랫폼에 복제된 경우 URL이 달라도 하나로 셉니다.
- Job Posting에는 원문의 정확한 `job_title`을 기록하며, 서로 다른 원문 직무명은 책임이 비슷해도 하나의 후보로 합치지 않습니다.

## 언어 지침

- PR 제목·설명·검토 코멘트는 한국어로 작성합니다.
- 커밋 메시지는 feat:, fix:, docs:, test: 같은 영어 유형 뒤에 한국어 설명을 작성합니다.
- SKILL.md와 사용자가 읽는 참고 문서는 한국어로 작성합니다.
- Skill 이름, 기능명, Notion 속성·상태값, 브랜치명, 코드 식별자, 설정 키, 명령어는 영어로 유지합니다.
- 과거 커밋과 병합된 PR의 기록은 다시 작성하지 않고, 이 지침을 반영한 이후의 작업부터 적용합니다.

## Notion 구조

확인된 프로젝트 페이지 아래에 Roles DB와 Trends DB를 각각 하나씩 만듭니다. 처음 만든 뒤 식별자를 저장해 재사용합니다. 저장된 식별자를 찾을 수 없다는 이유만으로 중복 데이터베이스를 만들지 않습니다.

Roles DB는 Role Name, Category, Status, Experience Level, Description, Key Responsibilities, First Discovered, Last Reviewed, Evidence Sources, Notes를 지원해야 합니다.

Trends DB는 Title, Summary, Key Insight, Source Type, Source Name, Original URL, Published Date, Collected Date, Related Roles, Domain을 지원해야 합니다.

## 구현 순서

1. 프로젝트 기본 구조
2. Notion 데이터베이스와 식별자 재사용
3. Role Discovery
4. Candidate 승인과 거절
5. Trend Update
6. URL 정규화와 중복 방지
7. 분류와 직무 관계
8. 최종 Skill 패키징

각 기능은 최신 main에서 별도의 feature branch를 만들어 개발합니다. 관련 테스트를 실행하고 branch를 push한 뒤 PR을 만듭니다. 사용자가 명시적으로 승인한 뒤에만 병합합니다.

## MVP 제외 범위

- 의미 기반 이벤트 중복 판정
- 새 직무 자동 승인
- 새로 발견한 Candidate를 사용한 재귀 검색
- 커뮤니티와 소셜 콘텐츠
- 이메일 뉴스레터 직접 수집
- 예약 실행과 자동 주간 보고서
- 급여, 성장률 또는 회사 단위 채용 동향 분석
- GitHub 저장소 자동 생성
