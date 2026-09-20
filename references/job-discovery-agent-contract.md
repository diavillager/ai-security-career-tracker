# Job Discovery 조사 Agent 계약

## 목적과 경계

세 조사 Agent는 대한민국 근무 채용 공고를 폭넓게 찾고, 실제 공고 한 건마다 확인한 사실을 구조화해 반환한다. 할당된 `search_route`는 검색 누락을 줄이는 출발 경로일 뿐 최종 `domain`의 허용 목록이 아니다. AI 검색에서 AI × Security 공고를 발견했다면 실제 업무에 맞게 분류해 그대로 반환한다.

Agent는 Candidate를 만들거나 두 번째 독립 근거를 요구하지 않는다. 게시일이 없어도 현재 모집 상태를 확인할 수 있는 공고는 버리지 않고 `published_on: null`로 반환한다. Notion이나 프로젝트 파일을 수정하거나 다른 Agent를 시작하거나 Trend Update를 실행하지 않는다.

## 부모가 전달하는 입력

- `run_id`: 실행 식별자
- `search_route`: `AI`, `Security`, `AI × Security` 중 할당된 검색 경로
- `search_period.start`, `search_period.end`: ISO 날짜
- `collected_on`: 수집 기준일
- `job_market`: 항상 `South Korea`
- `queries`: 부모가 `build_job_search_tasks`로 만든 짧은 검색 질의 목록
- `preferred_sources`: 기업 공식 채용 페이지, Saramin, JobKorea, Wanted, Jumpit 우선순위
- `existing_jobs`: 기존 공고의 원문 URL, 공고 식별자와 중복 비교 사실 snapshot

입력 기간이나 시장을 임의로 바꾸지 않는다. 질의 순서와 추가 원문 확인은 출처 범위를 넓히는 범위에서 자율적으로 정할 수 있다.

## 조사 규칙

1. 기업 공식 채용 페이지와 국내 채용 플랫폼을 출처별로 확인한다. 출처 목록은 완전한 허용 목록이 아니다.
2. 다른 사이트를 사용할 때도 공고 원문에서 대한민국 근무를 확인하고 가능하면 기업 원본을 함께 확인한다.
3. 검색 결과 요약만으로 공고 사실을 만들지 않는다. 원문을 열어 회사명, 원문 공고명, 근무지, 업무·요건, 날짜와 상태를 확인한다.
4. 실제 공고 한 건을 하나의 observation으로 반환한다. 서로 다른 공고명을 직무 개념 하나로 합치지 않는다.
5. 공고 원문 한 건이면 observation을 반환할 수 있다. 복제 공고나 기업 원본을 찾으면 `related_urls`에 보존한다.
6. 게시일이 없으면 `null`을 사용한다. 현재 모집 여부를 확인했다면 `posting_status`에 기록한다.
7. 해외 근무, 기간 밖, 명백히 무관한 결과는 `exclusions`에 사유와 함께 남긴다. 원문 접근 실패도 누락하지 않는다.
8. 접근 제한이나 일부 출처 실패는 `blockers`에 기록하되, 확인된 다른 공고를 버리지 않는다.

## 출력 형식

설명이나 Markdown 없이 하나의 JSON 객체만 반환한다. key와 enum은 아래 영어 값을 그대로 사용하고, 설명 문장은 한국어로 작성한다.

```json
{
  "run_id": "job-run-001",
  "agent_name": "ai_job_researcher",
  "search_route": "AI",
  "job_market": "South Korea",
  "search_period": {"start": "2026-08-20", "end": "2026-09-20"},
  "collected_on": "2026-09-20",
  "search_queries_run": ["대한민국 AI 개발자 채용"],
  "source_coverage": [
    {"source_name": "Employer Careers", "queries_run": 2, "results_checked": 8, "originals_opened": 3}
  ],
  "sources_checked": ["Employer Careers", "Saramin"],
  "observations": [
    {
      "source_name": "Employer Careers",
      "source_type": "Employer",
      "source_url": "https://careers.example/jobs/123",
      "canonical_url": null,
      "platform_job_id": "123",
      "related_urls": [],
      "employer_name": "Example Corp",
      "original_title": "AI Security Engineer",
      "recognized_role": "AI 보안 엔지니어",
      "domain": "AI × Security",
      "classification_basis": "LLM 위협 모델링이 핵심 업무입니다.",
      "responsibilities": ["LLM 위협 모델링"],
      "requirements": ["Python과 보안 평가 경험"],
      "technology_keywords": ["LLM", "Threat Modeling"],
      "location": "서울",
      "job_market": "South Korea",
      "experience_level": "Experienced",
      "employment_type": "Full-time",
      "work_mode": "Hybrid",
      "published_on": "2026-09-10",
      "deadline": null,
      "posting_status": "Open",
      "collected_on": "2026-09-20",
      "search_routes": ["AI"]
    }
  ],
  "exclusions": [
    {"source_url": null, "reason": "access_failure", "summary": "원문 접근이 차단되었습니다."}
  ],
  "blockers": []
}
```

허용 enum은 Python `job_discovery.py`의 `JobDomain`, `JobSourceType`, `ExperienceLevel`, `EmploymentType`, `WorkMode`, `PostingStatus`, `AgentExclusionReason`을 따른다.
