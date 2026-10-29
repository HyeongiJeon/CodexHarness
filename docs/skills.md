# Codex Harness 스킬 안내

`.agents/skills/`의 17개 스킬은 이름과 `SKILL.md`의 `description` 메타데이터를 바탕으로 요청에 맞는 경우 자동으로 후보가 됩니다. 사용자는 `$skill-name`으로 직접 지정할 수도 있습니다. 자동 후보 등록은 모든 스킬의 본문을 항상 읽는다는 뜻이 아닙니다. 관련성이 있는 스킬의 `SKILL.md`만 적용 시점에 읽고, 그 안에서 연결한 참고 문서는 해당 세부 작업이 필요할 때만 읽습니다. 이 점진적 공개 방식으로 전체 목록을 한꺼번에 불러오지 않습니다.

명시적인 프로젝트 지침과 과제의 운영 제한이 스킬 지침보다 우선합니다. 특히 시험 프로필은 브라우저·GUI·컴퓨터 사용 자동화를 허용하지 않습니다. 웹 결과 확인은 로컬 HTTP 요청, 사용자가 직접 조작하는 로컬 미리보기, 정적 파일 검사로 진행합니다.

| 스킬 | 자동 선택에 적합한 요청 | 진입점 |
|---|---|---|
| API 백엔드 개발 | HTTP API, 서비스, 저장 경계, 요청 검증 또는 트랜잭션 구현 | [api-backend-development](../.agents/skills/api-backend-development/SKILL.md) |
| 아키텍처 계획 | 여러 파일에 걸친 변경의 경계·인터페이스·순서 계획 | [architecture-planning](../.agents/skills/architecture-planning/SKILL.md) |
| 완료 검증 | 구현 후 요구사항별 동작 증거 확인 | [completion-verification](../.agents/skills/completion-verification/SKILL.md) |
| 데이터 처리 | 구조화 데이터 정제, 조인, 변환, 분석 | [data-processing](../.agents/skills/data-processing/SKILL.md) |
| 결정·증거 기록 | 중요한 선택, 실험, 검증 기록의 추적성 유지 | [decision-and-evidence-recording](../.agents/skills/decision-and-evidence-recording/SKILL.md) |
| 문서 처리 | PDF, DOCX, 스프레드시트, 프레젠테이션의 구조·레이아웃 작업 | [document-processing](../.agents/skills/document-processing/SKILL.md) |
| 최종 전달 검증 | 제출 직전 산출물·실행 방법·한계 점검 | [final-delivery-verification](../.agents/skills/final-delivery-verification/SKILL.md) |
| 프런트엔드 디자인 | 웹 화면의 위계, 반응형 레이아웃, 상호작용 상태 개선 | [frontend-design](../.agents/skills/frontend-design/SKILL.md) |
| 독립 코드 리뷰 | 변경 코드의 실제 결함·회귀 위험에 대한 별도 검토 | [independent-code-review](../.agents/skills/independent-code-review/SKILL.md) |
| 병렬 구현 | 명시적으로 허용된 독립 작업의 소유권 분리·통합 | [parallel-implementation](../.agents/skills/parallel-implementation/SKILL.md) |
| 신속한 MVP 개발 | 제한된 시간에 핵심 사용자 흐름을 실행 가능하게 구현 | [rapid-mvp-development](../.agents/skills/rapid-mvp-development/SKILL.md) |
| 요구사항 발견 | 모호한 구현 요청을 검증 가능한 기준으로 구체화 | [requirement-discovery](../.agents/skills/requirement-discovery/SKILL.md) |
| 체계적 디버깅 | 재현 가능한 오류·회귀의 원인을 좁혀 수정 | [systematic-debugging](../.agents/skills/systematic-debugging/SKILL.md) |
| 작업 우선순위 | 요구사항·의존성·위험·마감시간에 따른 작업 순서 결정 | [task-prioritization](../.agents/skills/task-prioritization/SKILL.md) |
| 시간 예산 관리 | 고정된 마감시간에서 구현·검증·전달 시간 배분 | [time-budget-management](../.agents/skills/time-budget-management/SKILL.md) |
| 시각화·대시보드 | 검증된 지표를 차트나 대시보드로 표현 | [visualization-and-dashboard](../.agents/skills/visualization-and-dashboard/SKILL.md) |
| 웹 애플리케이션 개발 | UI·상태·라우트·서비스를 잇는 웹 기능 구현 | [web-application-development](../.agents/skills/web-application-development/SKILL.md) |

스킬 목록 전체를 미리 읽을 필요는 없습니다. 실제 요청의 목적에 가장 가까운 항목을 선택하고, 필요한 경우에만 그 스킬의 참고 자료로 이동합니다.
