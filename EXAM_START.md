# CodexHarness — 실전(180분) 원클릭 시작

> Git Clone 후 제공된 Codex에 다음 한 문장만 입력하세요.
>
> **`CodexHarness/EXAM_START.md 읽고 현재 과제를 진행해줘.`**

사전체험용 [START_HERE.md](START_HERE.md)는 그대로 유지한다. 이 문서는 실제 시험용이다.

## Codex 실행 지시

너는 Lead Engineer / Orchestrator다. 실제 과제의 지침·README·AGENTS.md·요구사항이 이 문서보다 **항상 우선**한다. CodexHarness는 개발 도구이며 제출물이 아니다. 시작 시각을 기록하고 절대 마감(시작+180분)을 기준으로 시간을 관리한다.

### 0. 시험 제한 (변경 금지)
Git push 금지, 외부 서비스로 과제 데이터 전송 금지, 브라우저·GUI·Computer Use 자동화 금지, Codex 업데이트 금지, 인증·권한·감독·관리 설정 변경 금지, Astra 금지. AI 사용이 금지된 평가에서는 모든 AI 작업을 중단한다. 이 제한과 Cofa의 제한이 충돌하면 더 엄격한 쪽을 따른다.

### 1. 환경과 과제 분석 (0–15분)
1. 현재 디렉터리에서 실제 과제 프로젝트 루트와 CodexHarness 경로를 찾는다(`ls`, `git rev-parse --show-toplevel`). 과제 README, AGENTS.md, 요구사항 문서, 기존 실행·테스트 명령을 읽는다. 과제 프로젝트가 없으면 만들지 말고 사용자에게 알린다.
2. CodexHarness 경로에서 `python3 -m harness doctor`, `python3 -m harness validate`를 실행한다. 대량 설치·전체 벤치마크·프레임워크 재구축은 하지 않는다.
3. 과제에 필요한 Skill만 연결한다(기존 파일은 덮어쓰지 않음). 웹 과제 예:
   `python3 -m harness install-skills --project <과제 루트> --skill web-application-development --skill web-runtime-debugging --skill web-flow-verification --skill web-ui-patterns --skill frontend-design --skill rapid-mvp-development --skill parallel-implementation --skill completion-verification --skill decision-and-evidence-recording`
   API는 `api-backend-development`, 대시보드는 `visualization-and-dashboard`, 데이터는 `data-processing`, 문서·다중 문서는 해당 Skill을 추가한다. **새로 설치한 Skill은 새 세션에서 발견된다.** 현재 세션에 소급 적용되지 않으면 해당 `SKILL.md`를 직접 읽어 따른다.
4. 위임 수단을 확인한다. 이 세션에 네이티브 서브에이전트 도구가 있으면 사용한다. 사용자가 역할 설정으로 시작하려면 알려 준다:
   `python3 -m harness launch --project <과제 루트> --mode routed --dry-run` 후 필요 시 `--mode inherited --model <확인된 모델>`. 이미 실행 중인 세션에는 소급 적용되지 않으며, 설정 파일을 읽은 것을 에이전트 가동의 증거로 쓰지 않는다. 역할 지정이 불가하면 `python3 -m harness role <이름>` 출력을 새 에이전트 프롬프트로 전달하고 inherited fallback을 기록한다. 서브에이전트가 금지·불가이면 순차로 진행하고 그 한계를 보고한다.

### 2. 전문 에이전트 운영
모든 에이전트를 무조건 띄우지 않는다. 필요한 역할만, 독립 작업은 병렬로 위임한다. 모델 정책은 기존 설정(routed: Sol/Terra/Luna, inherited: 부모 모델 상속)을 유지하되 **실제로 관찰한 모델·역할만** 기록한다.

| 역할 | 사용 시점 | 쓰기 경로 |
| --- | --- | --- |
| requirements | 항상 먼저: 필수/선택 구분, 수용 기준 ID, 이해관계자 질문 | 없음 |
| explorer | 항상 먼저(병렬): 코드·자료 지도 | 지정 출력만 |
| architect | 다중 파일 변경: 최소 구조·인터페이스·작업 계약 | 없음 |
| frontend | 화면·사용성 | UI 파일 |
| core | API·상태·비즈니스 로직 | 서버/로직 파일 |
| data | 대용량·분석 자료 | 지정 출력 |
| qa | 통합 후 실행 검증 | 없음 |
| reviewer | 통합 후 독립 리뷰 1회 | 없음 |
| synthesizer | 다중 문서 종합이 필요할 때만 | 없음 |

작업자에게는 목표·입력·출력·수용 기준·**겹치지 않는 쓰기 경로**·검증 명령을 준다. 공유 lockfile/manifest는 Lead 소유다. 동시 에이전트 수는 세션의 한도를 확인해 맞춘다.

### 3. 진행 순서
1. 요구사항·수용 기준 확정 (requirements + explorer 병렬)
2. 핵심 사용자 흐름 설계 (architect; 작은 과제면 Lead가 직접)
3. 독립 작업 병렬 구현
4. **조기 통합**: 60분 시점에 실제로 실행되는 핵심 흐름이 있어야 한다. 선택 기능은 줄인다.
5. QA와 독립 reviewer 검증 (구현자 자체 검증 후 통합 리뷰 **한 번**)
6. 중요 결함만 일괄 수정, 110분 이후 새 프레임워크·구조 변경 금지
7. 최종 실행·제출물 확인, 마지막 10분은 전달 정리

필수 기능 먼저, 선택 개선은 뒤로. 불필요한 에이전트·가드레일·과잉 테스트를 만들지 않는다. Lead는 diff를 직접 읽고 통합 코드에서 명령을 직접 실행한다. 작업자 보고만으로 완료를 주장하지 않는다.

### 4. 웹 과제를 감지했을 때
(UI·서버·브라우저 미리보기·HTML/React/Vite/Flask/Express 등이 보이면)
- requirements와 explorer를 병렬로 실행한다. architect가 최소 구조와 API 계약(경로·JSON 형태)을 정의한다.
- frontend는 화면·사용성(`web-ui-patterns`, `frontend-design`), core는 API·상태·저장을 담당한다. 파일 소유권을 분리하고 계약을 먼저 합의한다. 분석이 필요하면 data를 추가한다.
- **서버 실행과 미리보기 확인은 마지막까지 미루지 않는다.** 첫 통합 시점에 서버를 실행하고 `python3 -m harness web-probe http://127.0.0.1:<포트>/ --path /api/<경로>`를 실행한다. 서버는 필요하면 `0.0.0.0`에 바인딩하되, `0.0.0.0`은 접속 주소가 아니라는 점을 구분해 사용자에게 **실제 포트 번호**를 알려 준다.
- 빈 화면·오류가 보고되면 `web-runtime-debugging`으로 서버 정상 / 프런트엔드 오류 / 미리보기 연결 실패를 구분한다. 프로브가 정상인데 미리보기가 비면 해결되었다고 쓰지 말고, 사용자에게 브라우저 콘솔 첫 오류와 Network의 실패 요청을 확인하도록 요청한다. 공식 확인되지 않은 Cofa 기능·URL을 만들어내지 않는다.
- 완료 주장 전 `web-flow-verification`: 입력 → API → 저장 → 화면 반영 → 새로고침 → 오류 흐름. HTTP 200만으로 흐름 성공을 주장하지 않으며, 자동 검사와 사용자가 직접 할 브라우저 확인을 구분해 표로 정리한다.
- qa와 reviewer는 통합 이후에 실행한다.

### 5. 개발 기록 (서술형 평가 대비)
`templates/exam-notes.md`를 과제 밖 또는 과제가 허용하는 위치에 두고 작업하며 3~10줄씩만 갱신한다: 해결하려던 요구사항, 선택한 핵심 기술과 이유, AI가 제안한 도구·방법, 내가 확인한 호환성·실행 결과, 채택/제외 근거, 실제 테스트 명령과 결과, 해결하지 못한 문제. 더 자세한 결정·검증은 `decision-and-evidence-recording`과 `templates/`를 쓴다. 사실만 기록하고, AI 금지 서술형 평가의 답안을 AI로 작성하거나 대신 응답하지 않는다. 그 평가가 시작되면 AI 작업을 중단하고, 사용자가 자신의 기록을 직접 보고 설명한다.

### 6. 최종 보고
과제 경로 / 연결한 Skill / 서브에이전트 실제 실행 여부와 관찰한 모델 / 실행 명령과 포트 / 실제 실행한 검증(명령·종료 코드) / 사용자 확인이 필요한 항목 / 알려진 한계·미확인 사항을 짧게 보고한다. 실행하지 않은 검사를 통과했다고 쓰지 않는다.
