# 180분 시험 실행 안내

시험에서는 제공된 Codex만 사용한다. 업데이트·Git push·외부 업로드·외부 서비스로 과제 데이터 전송·브라우저/GUI/computer-use 자동 조작·Astra 선택을 하지 않는다. 플랫폼 권한, 인증, 감독, 관리 제한을 변경하지 않는다. 준비 단계의 공개 저장소 게시 허가는 시험 게시 허가가 아니다. 기존 과제의 `AGENTS.md`, 요구사항, 코드, 설정을 먼저 읽는다.

## 시작 전 확인과 실행

Python 3.11 이상이 필요하며 외부 Python 런타임 의존성은 없다. 아래 명령은 이 harness 저장소에서 실행한다. `doctor`는 제공 CLI 버전·기능·로컬 모델 메타데이터를 읽으며 설정이나 인증을 바꾸지 않는다. 캐시의 모델 이름은 실제 접근 권한 증거가 아니다.

```sh
python3 -m harness --help
python3 -m harness doctor
python3 -m harness validate
python3 -m harness launch --help
```

기본 `inherited`는 역할 파일에 모델·추론 강도를 고정하지 않는다. 검증된 부모 세션 모델을 상속하려는 경우 사용한다. 새 CLI의 부모 기본 모델이 현재 IDE 세션과 같다고 가정하지 않는다. 실행 전 `--dry-run`으로 실제 인자를 확인하고, 필요하면 `--model`로 확인된 부모 모델을 명시한다. 아래의 `gpt-6.1-sol`도 해당 환경에서 접근이 확인되어야 한다.

```sh
python3 -m harness launch --project /absolute/path/to/assignment --mode inherited --model gpt-6.1-sol --dry-run
python3 -m harness launch --project /absolute/path/to/assignment --mode inherited --model gpt-6.1-sol
```

역할별 라우팅을 사용하려면 `--mode routed`를 명시한다. 이 모드는 저장소 `.codex/`의 모델·강도와 역할 파일을 명시적 일회성 `-c` 인자로 전달한다. `inherited`는 `configs/inherited/`를 사용한다. 두 모드 모두 역할 파일 경로를 절대 경로로 전달하므로 프로젝트 설정의 자동 발견에만 의존하지 않는다. 기존 프로젝트의 다른 설정이나 관리 제한은 계속 적용된다. 홈 설정, `CODEX_HOME`, 프로젝트 신뢰, 인증 파일을 변경하지 않는다.

```sh
python3 -m harness launch --project /absolute/path/to/assignment --mode routed --dry-run
```

역할 파일의 모델·강도는 자식 생성 요청의 모델·강도보다 나중에 적용되어 우선할 수 있다. `launch --model`은 부모 모델 선택이며 routed 역할의 모델을 일괄 교체하지 않는다. 현재 라우팅 설정의 요청값과 실제 세션의 모델·강도를 구분해 기록한다. `data`·`qa`의 요청 ID는 `gpt-5.6-terra`이고 접근 검증 전에는 사용 성공으로 쓰지 않는다. 근거는 [버전별 조사](codex-research.md)에 있다.

`configure NEW_DIRECTORY --mode inherited|routed`는 비어 있는 새 디렉터리에 번들을 만들며 기존 파일 덮어쓰기를 거부한다. 생성한 설정은 자동 적용되지 않는다. 역할 파일을 해당 환경에서 확인된 모델로 조정한 뒤 `launch --bundle NEW_DIRECTORY`로 명시적으로 선택한다. 이 안내의 앞선 명령은 체크인된 두 번들을 사용한다.

다른 과제 프로젝트는 harness 저장소의 스킬을 자동 발견하지 않는다. 필요한 스킬만 원래 스킬을 덮어쓰지 않고 복사하고 Codex 세션을 새로 시작한다. 기존 `AGENTS.md`와 `.codex/`는 이 명령이 수정하지 않는다.

```sh
python3 -m harness install-skills --project /absolute/path/to/assignment --skill parallel-implementation --skill completion-verification
python3 -m harness role lead
```

두 번째 명령의 리드 지침은 실제 과제의 지침에 맞게 메인에게 전달한다. harness의 AGENTS.md나 `make check`를 원래 프로젝트의 지침·검사로 대체하지 않는다. 원래 프로젝트와 충돌하는 스킬은 보존되며 `preserved_existing`에 표시된다.

CLI나 역할 선택 기능이 없으면 제공 IDE의 네이티브 에이전트 도구를 사용한다. `python3 -m harness role requirements`처럼 프롬프트를 출력해 검증된 부모 모델을 상속하는 새 에이전트에 전달한다. 에이전트 기능도 금지되거나 없으면 순차 작업으로 전환하고 한계를 남긴다. 외부 CLI 설치, 업데이트, 권한 완화로 복구하지 않는다.

## 시간 배분 예시

시작 시각과 실제 종료 시각을 기록하고 절대 마감을 기준으로 재계산한다. 이 표의 30분은 검증, 마지막 10분은 전달에 예약되어 있다. 구현 지연을 이유로 예약 시간을 모두 소비하지 않는다.

| 경과 | 시간 | 완료 기준 |
| --- | --- | --- |
| 0–15분 | 15분 | 제한·기준선 확인, requirements와 explorer 병렬 조사 |
| 15–30분 | 15분 | architect 계약, 필수 수용 기준, 경로·인터페이스 합의 |
| 30–110분 | 80분 | 독립 구현, 60분 시점 핵심 흐름 시연 가능한지 점검 |
| 110–140분 | 30분 | 핵심 흐름 연결, 실패 수정, 필수 범위 동결 |
| 140–170분 | 30분 | QA·독립 리뷰·리드 통합 검사, 중대 결함 재검사 |
| 170–180분 | 10분 | 실행 안내·산출물·Git 상태·미확인 항목 정리와 로컬 전달 |

60분 시점에 핵심 흐름이 실행되지 않으면 선택 기능을 줄인다. 110분에는 새로운 프레임워크나 구조 변경을 멈추고 연결·정확성에 집중한다. 140분부터 필수 결함만 수정하며, 마지막 변경 뒤에는 영향받는 검사를 다시 한다. 실제 절차는 [A–F 워크플로](workflow.md)를 따른다. 리드와 작업자 3명 운영을 기준으로 하되 노출된 호스트 한도에 맞춰 줄이고, 완료 슬롯을 QA·리뷰에 재사용한다.

## 연습용 실행과 검증

아래는 이 저장소의 합성 예제용 명령이다. 실제 시험 프로젝트의 검사를 대체하지 않는다. `make check`는 단위 테스트와 harness 설정·스킬 검증을 실행하며, 의도적으로 실패하는 `examples/bugfix/starter`의 검사는 별도다.

```sh
make check
python3 -m harness plan-check examples/task-plan.json
python3 -m harness demo --host 127.0.0.1 --port 8765
```

데모는 실행 프로세스 메모리에 저장하며 종료하면 변경이 사라진다. 별도 터미널에서 Python `urllib.request` 등으로 로컬 HTTP를 점검할 수 있다. 이 검사는 시각 검사를 포함하지 않는다. 서버 종료는 실행한 터미널에서 `Ctrl-C`로 한다.

다음 benchmark는 준비 단계에서 실제 Codex 실행·시간·토큰 증거를 수집한다. 인증된 제공 CLI 호출이며 무료 정적 검사가 아니다. 기본 smoke는 실제 새 자식 두 개와 반환 파일을 검사한다. 설치 CLI V1의 문맥 인자를 예시로 안내하지만 실제 노출된 도구가 hosted 스키마를 쓰면 그 스키마를 따른다. 실제 생성 요청과 자식 세션을 확인하고 실패를 사실대로 기록한다. 시험 중에는 과제와 규칙이 허용하는 경우에만 사용한다.

```sh
python3 -m harness benchmark --mode smoke --routing inherited --model gpt-6.1-sol --timeout 120
python3 -m harness benchmark --mode single --routing inherited --model gpt-6.1-sol --timeout 600
python3 -m harness benchmark --mode multi --routing inherited --model gpt-6.1-sol --timeout 600
```

실행 결과는 로컬 `.harness/runs/`에 남으며 Git에서 제외된다. 실제 모델·강도, 생성 이벤트, 병렬 시간 겹침, 성공 기준을 `summary.json`과 대조한다. 토큰 수의 집계 범위를 확인하며 부모 사용량만으로 전체 비용을 주장하지 않는다. 원시 세션 로그·인증·업무 데이터는 복사하거나 공개 커밋하지 않는다. 공개 기록이 필요하면 합성 실행에서 비밀 없는 집계만 선별한다.

## 사용자가 직접 확인할 화면 항목

다음은 체크리스트이며 자동 통과 결과가 아니다. 담당자가 직접 확인한 시각·환경·결과를 증거에 적기 전에는 `미확인`이다. 제공 미리보기의 사용도 해당 시험 규칙을 따른다.

- 좁은 화면과 넓은 화면에서 입력·버튼·내용이 잘리지 않는가.
- 키보드로 필수 입력과 제출·필터·상태 변경이 가능한가.
- 등록·상태 변경·필터·빈 결과·잘못된 입력이 화면에 올바르게 나타나는가.
- 서버 오류 안내가 보이며 불필요한 데이터 손실이 없는가.

최종 전달은 실제 경로·실행법·검사 결과·알려진 한계를 포함한다. 이후 AI 금지 필기 평가가 시작되면 모든 AI 작업을 중단한다. 개발 노트에는 실제 선택과 관찰만 남긴다.
