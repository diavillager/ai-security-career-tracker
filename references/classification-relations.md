# Trend 분류와 직무 유형

Trend Update는 원문을 `출처 유형`, `관련 분야`, `관련 직무`, `기술 키워드`, `동향 유형`, `지역 범위`, `요약`, `취업 시사점`으로 구조화합니다. Jobs의 상태나 레거시 Roles workflow를 분류 근거로 사용하지 않습니다.

## 출처 유형

내부 enum은 News, Industry Media, Company Blog, Engineering Blog, Press Release, Job Posting, Official Documentation, Research Report, Newsletter, GitHub, Paper, Conference, Government, Other를 사용합니다. Notion에는 각각 뉴스, 업계 매체, 기업 블로그, 기술 블로그, 보도자료, 채용 공고, 공식 문서, 연구 보고서, 뉴스레터, GitHub, 논문, 컨퍼런스, 정부, 기타로 저장합니다. 커뮤니티와 소셜 출처는 Other로 우회하지 않습니다.

## 관련 분야와 직무

- `관련 분야`는 AI, Security, AI × Security 중 원문의 실질적 주제를 하나 이상 Multi-select로 기록합니다.
- `관련 직무`는 영향을 받는 직무 유형 이름을 Multi-select로 기록합니다. 특정 Jobs 행이나 Roles page relation이 아닙니다.
- 직무명은 제목 exact match만으로 정하지 않고 본문의 책임, 기술, 제품과 시장 맥락을 근거로 선택합니다.
- 같은 분야, 직무 또는 기술 키워드를 한 항목에 중복해서 넣지 않습니다.

## 동향 유형과 지역 범위

- 동향 유형: 기술, 채용시장, 산업, 규제·정책, 위협·사고, 연구
- 지역 범위: 국내, 해외, 글로벌
- Job Posting은 대한민국 근무가 확인된 경우에만 허용하며 지역 범위는 국내로 기록합니다.

## 요약과 취업 시사점

- `요약`은 원문이 말하는 사실을 간결하게 정리합니다.
- `취업 시사점`은 그 사실이 관련 직무의 책임, 기술 요구, 채용시장이나 준비 방향에 주는 의미를 설명합니다.
- 두 값은 모두 필요하며 같은 문장을 복제하지 않습니다.

`classification_basis`에는 본문의 어떤 사실을 근거로 분야·직무·기술·동향 유형·지역 범위를 선택했는지 기록합니다. 이는 검토용 값이며 별도 Notion 속성을 임의로 추가하지 않습니다.
