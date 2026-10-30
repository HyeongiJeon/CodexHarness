# CodexHarness — 사전체험 원클릭 설정 프롬프트

> Git Clone한 다음 Codex에게 다음 한 문장만 입력하세요.
>
> **`CodexHarness/START_HERE.md 읽고 사전체험 환경을 설정하고 검증해줘.`**
>
> Codex를 CodexHarness 폴더에서 실행했다면 `START_HERE.md 읽고 진행해줘.`라고 입력하면 됩니다.

## Codex 실행 지시

너는 사전체험의 Lead Engineer이자 Orchestrator다. **15분 이내**에 CodexHarness가 주어진 과제 환경에서 실제로 작동하는지 검증한다. 과제의 정식 구현이나 긴 벤치마크보다 **설정과 최소 스모크 테스트**가 우선이다.

1. 현재 디렉터리와 실제 과제 프로젝트 루트, Clone된 CodexHarness 경로를 확인한다. `README.md`와 `docs/exam-runbook.md`를 읽는다. 실제 과제의 지침·기존 코드·AGENTS.md가 최우선이다.
2. 사용 가능한 Python 및 Codex 버전을 확인하고, 하네스 위치에서 `python3 -m harness doctor` 및 `python3 -m harness validate`를 실행한다. 전체 벤치마크, 대량 설치, 프레임워크 재구축은 하지 않는다.
3. 기존 파일을 덮어쓰지 않는 `install-skills --project <과제 루트>`로 **과제에 필요한 Skill만** 연결한다. 웹 과제면 `web-application-development`, `frontend-design`, `rapid-mvp-development`, `parallel-implementation`, `completion-verification`을 우선한다. 필요에 따라 `api-backend-development`, `visualization-and-dashboard` 등을 추가한다. 문서·데이터 과제는 해당 전문 Skill을 선택한다.
4. 시험에 제공된 Codex가 네이티브 서브에이전트를 지원하는지 확인한다. 가능하면 Requirements와 Explorer를 **독립 컨텍스트로 병렬 호출**해 실제 결과를 받는다. 역할별 Sol/Terra/Luna 모델 라우팅을 실행 확인하되, 지원하지 않으면 검증된 inherited/네이티브 역할 방식으로 전환한다. 불필요하게 Codex를 중첩 실행하거나 모델·권한 제한을 우회하지 않는다.
5. 웹 프로젝트가 있다면 기존 실행 명령으로 서버를 시작하고, Cofa Browser 미리보기에 입력할 **실제 포트 번호**를 알려준다. 필요한 경우 서버를 `0.0.0.0`에 바인딩한다. 브라우저 미리보기 조작은 사용자가 직접 한다. 웹 프로젝트가 없다면 임의로 만들지 않는다.
6. 마지막에 **과제 경로 / Skill 연결 여부 / 서브에이전트 실제 실행 여부 및 모델 / 웹 서버 포트 / 해결되지 않은 문제**만 짧게 보고한다.

**제약:** 시험 규정을 따른다. Git Push, 외부 데이터 업로드·전송, 브라우저·GUI·Computer Use 자동 조작, Codex 업데이트, 관리형 인증·권한·감독 설정 변경은 하지 않는다. 파일 수정은 최소화하고 원래 과제 코드를 보존한다. 15분 내 핵심 확인을 끝낸다.
