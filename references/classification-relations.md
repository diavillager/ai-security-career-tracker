# 분류와 직무 관계

이 기능은 Trend Update가 찾은 원문을 `출처 유형`, `관련 분야`, `관련 직무`, `요약`, `핵심 시사점` 구조로 검증하고 Notion 속성에 연결합니다. 분류값을 추측으로 채우거나 Candidate와 Rejected 직무를 관계에 포함하지 않습니다.

## Source Type

다음 값 중 하나만 사용합니다.

- News
- Industry Media
- Company Blog
- Engineering Blog
- Press Release
- Job Posting
- Official Documentation
- Research Report
- Newsletter
- GitHub
- Paper
- Conference
- Government
- Other

`Other`는 허용된 출처이지만 다른 값으로 설명하기 어려운 경우에만 사용합니다. 커뮤니티와 소셜 출처는 `Other`로 우회하지 않고 제외합니다.

위 목록은 Agent JSON과 Python 내부 enum 계약입니다. Notion의 `출처 유형`에는 순서대로 뉴스, 업계 매체, 기업 블로그, 기술 블로그, 보도자료, 채용 공고, 공식 문서, 연구 보고서, 뉴스레터, GitHub, 논문, 컨퍼런스, 정부, 기타로 저장합니다.

## Domain

`관련 분야`는 콘텐츠의 실질적 주제를 기준으로 AI, Security, AI × Security 중 하나 이상을 선택합니다. 같은 값을 반복하지 않습니다.

- AI × Security 직무 하나가 연결되면 AI, Security, AI × Security를 모두 뒷받침할 수 있습니다.
- AI 직무와 Security 직무가 함께 연결되면 AI × Security를 뒷받침할 수 있습니다.
- 관련 직무의 Category로 설명할 수 없는 Domain은 저장하지 않습니다.

Trends DB에는 단일 `Select`가 아니라 `Multi-select`로 저장합니다.

## Related Roles

실행 시작 시점에 `Approved`인 직무만 연결합니다. 제목 exact match만 사용하지 않고 원문 본문, 책임, 기술과 제품 맥락을 근거로 판단합니다. 여러 직무에 관련되면 모두 연결하되 근거가 약한 직무를 과도하게 추가하지 않습니다.

Python은 반환된 Role Name을 실행 시작 snapshot의 정확한 record ID로 변환합니다. snapshot에 없거나 Candidate 또는 Rejected인 직무, 중복된 Role Name이 포함되면 Notion 쓰기 전에 전체 계획을 거부합니다.

## Summary와 Key Insight

- `요약`은 원문이 말하는 사실을 간결하게 정리합니다.
- `핵심 시사점`은 그 사실이 연결된 직무의 형성, 책임, 기술 요구나 시장 이해에 주는 의미를 설명합니다.

두 값은 모두 필요하며 같은 문장을 복제할 수 없습니다.

## 적용 순서

1. `parse_trend_observations`로 `source_type`, `domains`, `related_roles`, `summary`, `key_insight`, `classification_basis`를 구조화합니다. `classification_basis`에는 본문의 어떤 책임, 기술 또는 제품 맥락을 근거로 분류하고 연결했는지 적습니다.
2. `validate_classification_fields`로 값의 누락과 중복을 검사합니다.
3. `resolve_related_roles`로 모든 관계를 Approved snapshot의 page ID에 연결합니다.
4. `validate_domain_role_support`로 Domain과 연결 직무 Category의 일관성을 검사합니다.
5. 모든 항목이 통과한 뒤 `build_notion_trend_pages`가 `관련 분야`를 `multi_select`, `관련 직무`를 `relation`으로 변환합니다.
6. 실제 Notion 쓰기 직전에 새 page, 분류 근거와 schema 변경 필요 여부를 사용자에게 보여주고 확인을 받습니다. `classification_basis`는 검토용이며 PRD에 없는 Notion 속성을 임의로 추가하지 않습니다.
