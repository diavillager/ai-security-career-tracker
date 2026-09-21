# Role Evidence Reviewer Contract

> **레거시 참고 문서:** 현재 종합 검토는 `job_evidence_reviewer`가 담당합니다. 이 계약은 호환 코드와 변경 이력 확인용이며 운영 workflow에서 실행하거나 Roles DB를 다시 만드는 근거로 사용하지 않습니다.

이 계약은 `role_evidence_reviewer`가 세 영역 조사 결과를 종합 검토할 때 지킬 입력, 판단 범위, 출력 경계를 정의합니다. 이 Agent는 근거의 의미 품질을 표시하지만 Candidate 결정이나 데이터베이스 변경은 수행하지 않습니다.

## 실행 시점

1. `ai_role_researcher`, `security_role_researcher`, `ai_security_role_researcher`가 모두 끝납니다.
2. 부모 workflow가 각 응답을 `parse_agent_discovery_result`로 변환합니다.
3. 누락, 형식 오류, `blockers`, 실행 ID·기간·시장 불일치가 없을 때만 `role_evidence_reviewer`를 순차 실행합니다.
4. 부모 workflow가 검토 결과를 `parse_role_evidence_review_result`와 `validate_role_evidence_review`로 검사합니다.
5. 검토가 끝난 뒤 부모 workflow가 `consolidate_agent_results`로 Candidate 초안을 만듭니다.

동시 실행 한도 3은 조사 Agent에만 사용합니다. 검토 Agent는 조사 Agent가 모두 끝난 뒤 한 번 실행합니다.

## 부모 workflow가 제공할 입력

- `run_id`: 세 조사 Agent와 같은 실행 ID
- `search_start`, `search_end`, `job_market`
- 실행 시작 시 고정한 모든 기존 Role Name과 Status
- parser를 통과한 세 `AgentDiscoveryResult`
- 각 observation의 Role Name, 추천 Category, 설명, 책임, 기술, Experience Level과 Evidence Sources
- 각 Agent가 반환한 exclusions와 existing matches

입력이 누락됐거나 세 영역 결과가 모두 없으면 임의로 보완하지 않고 `blockers`에 기록합니다.

## 검토 범위

- `source_access_failure`: 반환된 원문에 접근할 수 없거나 핵심 날짜·근무지·직무 정보를 다시 확인할 수 없음
- `source_independence`: 서로 다른 URL이 같은 기업의 같은 공고를 복제한 페이지라 독립된 근거로 보기 어려움
- `evidence_conflict`: 출처 사이의 게시일, 근무지, Experience Level, 책임 또는 기술이 충돌함
- `category_ambiguity`: AI, Security, AI × Security 중 추천 Category가 책임과 제품 맥락에 비춰 모호함
- `semantic_duplicate`: 이름이 다르지만 같은 실행의 다른 observation 또는 기존 Role과 실질적으로 같은 역할일 가능성이 큼
- `unsupported_claim`: 설명, 책임, 기술 또는 발견 이유에 원문으로 확인되지 않는 주장이 포함됨

반환된 URL을 먼저 확인합니다. 필요한 경우 정확한 직무명과 기업명을 이용해 기업 원문을 찾는 검색만 허용합니다. 새 직무 발굴, 광범위한 채용 검색, 새로운 Candidate 제안은 금지합니다.

## 출력 계약

아래 키를 가진 하나의 JSON 객체만 반환합니다. JSON 앞뒤에 설명문이나 Markdown 코드 블록을 추가하지 않습니다. 설명 값은 한국어로 작성하되 속성명과 enum 값은 영어를 유지합니다.

- `run_id`
- `agent_name`: 반드시 `role_evidence_reviewer`
- `reviewed_roles`: 입력 observations의 정규화된 Role Name을 빠짐없이 한 번씩 포함
- `blockers`

각 `reviewed_roles` 항목은 다음을 포함합니다.

- `role_name`
- `assessment`: `clear` 또는 `flagged`
- `flags`: `type`, `summary`, `urls`를 가진 목록

`type`은 검토 범위에 정의된 여섯 enum 중 하나를 사용합니다. `clear`이면 `flags`는 빈 목록이어야 하고, `flagged`이면 하나 이상의 flag가 있어야 합니다. `urls`에는 검토 근거와 직접 관련된 원본 HTTP 또는 HTTPS URL만 넣습니다.

후보가 없으면 `reviewed_roles`를 빈 목록으로 반환합니다. 입력에 없던 Role Name을 추가하지 않습니다. Agent는 Candidate 여부, Status, Notion 저장 여부를 결정하지 않습니다.

## 부모 workflow의 처리

- `blockers`가 있거나 입력 observation의 Role Name을 빠뜨리거나 추가하면 검토 실행을 실패로 처리합니다.
- `flagged`는 자동 승인·거절 명령이 아닙니다. 부모 workflow는 Candidate 보고에서 flag와 근거를 사용자에게 함께 보여줍니다.
- Python의 기간, 대한민국 근무지, 근거 URL 수, 기존 직무 일치 검사를 되풀이하거나 대체하지 않습니다.
