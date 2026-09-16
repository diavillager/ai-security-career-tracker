# Role Discovery

사용자가 새롭게 등장하는 Role Name을 찾거나 검토해 달라고 요청할 때 Role Discovery를 사용합니다. 검토할 후보만 만들며 Trends DB에는 아무것도 저장하지 않습니다.

## 검색 기간과 범위

- 요청한 기간을 설정된 timezone의 명확한 시작일과 종료일로 변환합니다.
- 기간이 없으면 실행일을 포함한 최근 7일을 사용합니다.
- 날짜 표현에 따라 기간이 크게 달라질 수 있으면 검색 전에 질문합니다.
- AI, Security, AI × Security를 각각 검색합니다.
- 채용시장을 대한민국으로 제한합니다. 한국어와 영어로 검색하고 출처 원문에서 실제 근무지를 확인합니다.
- 기업 공식 채용 페이지, Saramin·JobKorea·Wanted·Jumpit 같은 국내 채용 플랫폼, 필요시 다른 채용 사이트 순서로 검색합니다. 이 목록은 우선순위를 안내하며 완전한 허용 목록이 아닙니다.

seed 이름은 검색을 시작하는 데 사용하지만 검색 범위를 제한하지 않습니다.

- AI: Applied AI Engineer, AI Agent Engineer, Agent Engineer, LLM Engineer, Generative AI Engineer, AI Platform Engineer, Agent Platform Engineer, Agent Infrastructure Engineer, AI Evaluation Engineer
- Security: Product Security Engineer, Application Security Engineer, Cloud Security Engineer, Security Platform Engineer, IAM Engineer, Security Engineer
- AI × Security: AI Security Engineer, Agent Security Engineer, GenAI Security Engineer, LLM Security Engineer, AI Product Security, AI Platform Security

agent, tool use, RAG, evaluation, model serving, orchestration, observability, IAM, authorization, OAuth, OIDC, sandbox, threat modeling, workload identity, policy enforcement, audit logging, data governance, Zero Trust 같은 책임 관련 검색어로 검색 범위를 넓힙니다.

## 영역별 Agent 위임

부모 workflow는 [role-discovery-agent-contract.md](role-discovery-agent-contract.md)에 따라 AI는 `ai_role_researcher`, Security는 `security_role_researcher`, AI × Security는 `ai_security_role_researcher`에 동시에 위임합니다. 세 Agent는 같은 `run_id`, 검색 기간, 대한민국 채용시장, 기존 Roles DB snapshot을 사용합니다.

각 Agent는 할당된 영역의 조사와 원본 근거 정리만 담당합니다. 세 영역 결과가 모두 성공한 뒤 부모 workflow가 URL 중복을 제거하고 기존 Python 검증으로 Candidate 요건을 판정합니다. 영역 하나가 실패하거나 누락되면 나머지 결과만으로 전체 조사가 끝났다고 보고하거나 Candidate를 저장하지 않습니다. 같은 Role Name이 서로 다른 Category로 반환되면 자동 선택하지 않고 검토가 필요한 충돌로 처리합니다.

세 응답이 `parse_agent_discovery_result`를 통과하면 [role-evidence-reviewer-contract.md](role-evidence-reviewer-contract.md)에 따라 `role_evidence_reviewer`를 순차 실행합니다. 검토 Agent는 반환된 근거 URL의 접근성, 같은 공고 복제본 여부, 출처 충돌, 의미 중복과 Category 모호성을 표시합니다. `flagged` 결과는 Candidate를 자동 승인하거나 거절하지 않으며, 최종 보고에서 사용자가 확인할 항목으로 함께 보여줍니다.

## 근거와 분류

채용 근거는 기업 공식 채용 페이지와 Saramin, JobKorea, Wanted, Jumpit 같은 국내 채용 플랫폼을 우선합니다. 이 목록을 완전한 허용 목록으로 사용하지 않습니다. 다른 국내외 채용 사이트도 공고 자체에서 대한민국 근무지를 명확히 확인할 수 있으면 사용할 수 있으며, 가능하면 기업의 원본 채용 공고와 함께 검증합니다. 글로벌 채용 집계 사이트를 최초 검색 대상으로 사용하거나 확인 가능한 기업 원본 공고 대신 단독으로 의존하지 않습니다.

채용 정보가 아닌 보조 맥락에는 공식 문서, 기업·엔지니어링 블로그, 보도자료, 조사 보고서, 공개 논문, 학회 자료, 정부 출처, 신뢰할 만한 편집 매체, 공식 GitHub 프로젝트 자료를 사용합니다. Reddit, Hacker News, 소셜 네트워크, 일반 포럼, 익명 게시물, 출처가 불명확한 커뮤니티 자료는 제외합니다.

Role Discovery는 대한민국 채용시장 조사입니다. 모든 후보에는 실제 근무지가 대한민국으로 명시된 채용 공고가 최소 1개 있어야 합니다. remote 직무는 대한민국에서 고용될 수 있다고 공고에 명시된 경우에만 인정합니다. 회사 본사의 위치, 회사 국적, 페이지 언어, 전 세계 공개 여부는 대한민국 근무지의 근거가 아닙니다. 해외 근무 또는 근무지가 불명확한 공고는 모두 제외합니다. 채용 정보가 아닌 출처는 어느 국가의 자료든 책임이나 기술 맥락을 보조할 수 있지만, 대한민국 채용시장에 해당 직무가 있다는 근거로는 사용할 수 없습니다.

요청한 검색 기간 안에 있는 원본 Published Date를 확인해야 합니다. 검색엔진 수집일, 접속일, 현재 모집 중이라는 상태는 Published Date가 아닙니다. 원본 Published Date를 확인할 수 없는 출처는 제외합니다.

각 후보 직무에서 다음 항목을 추출합니다.

- 정확한 Job title
- 공고에 명시된 Experience Level: 신입, 경력, 신입·경력, 미확인
- Job description
- Responsibilities
- Required skills
- Team description
- Product 또는 domain 맥락
- source name, original URL, 확인된 Published Date
- source type, 그리고 Job Posting이면 확인된 대한민국 근무지

모든 근거를 종합해 분류합니다. Agent Platform 직무에 Security 책임이 포함돼 있으면 AI × Security로 볼 수 있으며, Product Security 직무도 실제 범위에 LLM application이나 agent tool abuse가 포함되면 AI × Security로 볼 수 있습니다. 근거가 약하거나 충돌하면 억지로 분류하지 말고 불확실하다고 표시합니다.

## 기존 직무 비교

새 결과를 평가하기 전에 Roles DB의 모든 Role Name과 Status를 불러옵니다. 이름은 Unicode normalization, 앞뒤 공백 제거, 연속 공백 축소, case folding만 적용해 정규화합니다. MVP에서는 의미가 비슷한 직무명을 중복으로 판정하지 않습니다.

- 기존 Candidate: 새 레코드를 만들지 않습니다.
- 기존 Approved: 새 레코드를 만들지 않습니다.
- 기존 Rejected: 새 레코드를 만들거나 Status를 바꾸지 않습니다.
- 한 번의 실행에서 같은 직무가 여러 번 관찰되면 책임과 서로 다른 근거 URL을 하나의 제안 Candidate로 합칩니다.

## Candidate 저장

직무가 새롭고 검색 기간 안의 Published Date가 확인된 서로 다른 원본 HTTP 또는 HTTPS 근거 URL이 2개 이상일 때만 Roles DB 항목을 만듭니다.

두 출처 중 하나 이상은 대한민국 Job Posting이어야 합니다. 추가로 사용하는 비채용 정보는 국내외 출처 모두 허용합니다.

- Role Name: 관찰된 정확한 Role Name
- Category: 추천하는 AI, Security 또는 AI × Security
- Status: Candidate
- Experience Level: 공고에 명시된 값을 신입, 경력, 신입·경력, 미확인 중 하나로 정규화
- Description: 책임에 기반한 요약
- Key Responsibilities: 줄바꿈으로 구분한 책임
- First Discovered: 실행일
- Last Reviewed: 실행일
- Evidence Sources: 줄바꿈으로 구분한 Source Name — Original URL
- Notes: Job market: South Korea, 확인된 근무지, 간결한 발견 이유, 불확실한 점

같은 실행에서 실행 전 Approved 직무 목록을 바꾸거나 Trend Update를 호출하거나 새 Candidate로 검색 범위를 넓히지 않습니다.

## 결과 보고

명확한 시작일과 종료일, Job market: South Korea, 검색한 세 domain, 출처 수, 해외 근무 또는 근무지 불명확으로 제외한 공고 수, 그 밖의 제외 수, 번호가 붙은 새 Candidate, 기존 직무 일치 항목을 보고합니다. 각 후보에는 확인된 대한민국 근무지, Experience Level, 추천 Category, Description, Key Responsibilities, 발견 이유, Evidence Sources를 포함합니다. 마지막에는 후보의 승인 또는 거절을 명확히 요청하며 사용자가 응답하기 전에는 Status를 바꾸지 않습니다.
