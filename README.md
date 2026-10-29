# Codex Harness · SK hynix AI Hackathon

180분 개발 과제를 위한 Codex 전문 에이전트 팀과 검증 도구입니다. **설치된 Codex를 그대로 사용**하며 Python 3.11+ 외에 런타임 의존성이 없습니다. 실제 과제의 요구사항·기존 코드·AGENTS.md를 우선합니다. 연습 예제는 실제 제출물의 대체품이 아닙니다.

```sh
git clone https://github.com/HyeongiJeon/CodexHarness.git
cd CodexHarness
python3 -m harness doctor
make check
python3 -m harness launch --mode inherited --model gpt-6.1-sol
```

`gpt-6.1-sol`은 이 준비 환경에서 실행 확인한 ID입니다. 시험에서는 제공 `/model`·CLI 카탈로그와 실제 접근을 먼저 확인하고 허용된 모델을 지정합니다. Codex나 Python 설치·업데이트 스크립트는 포함하지 않습니다. `make`가 없으면 Makefile에 적힌 Python 명령을 직접 실행합니다.

## 구성과 실행 방식

```mermaid
flowchart LR
  Lead[Lead: 수용 기준·시간·통합] --> Discovery[Requirements + Explorer]
  Discovery --> Architect[Architect: 작업 계약]
  Architect --> Workers[필요한 Core / Frontend / Data]
  Workers --> Checks[QA + 독립 Reviewer]
  Checks --> Verify[Lead 직접 실행·검증]
  Verify --> Delivery[Docs·로컬 전달]
```

| 경로 | 실제 책임 |
| --- | --- |
| `AGENTS.md` | 리드 운영 원칙·과제 우선·시험 제한 |
| `.codex/config.toml`, `.codex/agents/` | 역할별 모델·추론 강도, 최대 4개 설정값·깊이 1 |
| `configs/inherited/` | 역할 모델·강도를 고정하지 않는 호환 번들 |
| `.agents/skills/` | 조건별 17개 Skill·필요할 때만 읽는 references |
| `harness/` | doctor·명시적 역할 실행기·계획 검사·안전한 Skill 복사·CSV·HTTP 예제·실제 benchmark |
| `examples/`, `tests/`, `benchmarks/` | 합성 입력·의도적 결함·회귀 검사·재현 가능한 측정 결과 |
| `.harness/` | 원시 실행 증거의 로컬 보관; Git 제외 |

프로젝트 설정 자동 로딩은 **신뢰된 프로젝트 여부와 설치 버전**에 달려 있습니다. `launch`는 선택한 번들의 역할 경로를 절대 경로 `-c` 인자로 전달합니다. 홈 설정·인증·신뢰·권한·관리 제한을 바꾸지 않습니다. 제공 환경에서 역할 선택이 금지된 경우 실행기를 쓰지 않고 허용된 순차 작업으로 전환합니다.

| 역할 | routed 모델 | 추론 | 책임 |
| --- | --- | --- | --- |
| Main / lead | `gpt-6.1-sol` | high | 기준·시간·위임·파일 소유권·최종 실행 |
| requirements | `gpt-6.1-sol` | high | 필수·선택·질문·수용 기준 |
| architect | `gpt-6.1-sol` | high | 최소 구조·인터페이스·의존성 |
| explorer | `gpt-6-luna` | medium | 기본 읽기 전용 저장소 탐색 |
| core | `gpt-6.1-sol` | high | 핵심 로직·API·복잡한 수정 |
| frontend | `gpt-6.1-sol` | medium | 화면·상태·접근성·핵심 흐름 |
| data | `gpt-5.6-terra` | high | 정제·스키마·계산 검증 |
| qa | `gpt-5.6-terra` | high | 실제 재현·테스트·회귀 |
| reviewer | `gpt-6.1-sol` | high | 새 문맥의 독립 결함 검토 |
| docs | `gpt-6-luna` | medium | 사실 기반 결정·사용법·증거 |

이 ID들은 설치 환경의 모델 메타데이터에서 확인했습니다. Sol 6.1·Luna 6·Terra 5.6의 실제 역할 라우팅도 실행 증거로 확인했습니다. 모든 역할을 항상 실행하지 않습니다. 작은 수정은 리드가 처리하고, 독립 작업이 충분할 때만 병렬화합니다. `gpt-5.6-terra`와 `gpt-6.1-terra`는 다른 모델입니다. `gpt-6-sol`은 로컬 카탈로그에서 확인했으나 이 benchmark의 실행 모델은 아닙니다. Astra는 사용하지 않습니다.

설치 CLI는 **0.163.0**입니다. [공식 문서·버전별 소스 조사](docs/codex-research.md)는 최신 소스 스냅샷과 설치 버전을 분리합니다. V1의 `fork_context=false`, hosted 도구의 `fork_turns="none"`, 동시 한도 계산은 같은 API라고 가정하지 않습니다. 이 환경의 실제 실행에는 hosted 형태가 노출됐습니다. 새 문맥도 파일 시스템은 공유합니다. [계획 계약](examples/task-plan.json)과 `plan-check`는 소유권 충돌·의존성을 확인하지만 파일 잠금은 아닙니다.

## 기존 과제 프로젝트에서 사용

하네스 저장소의 AGENTS.md나 설정을 원래 프로젝트에 덮어쓰지 않습니다. 다음 명령은 하네스 디렉터리에서 실행합니다.

```sh
python3 -m harness install-skills --project /path/to/assignment --skill parallel-implementation --skill completion-verification
python3 -m harness role lead
python3 -m harness launch --project /path/to/assignment --mode inherited --model gpt-6.1-sol --dry-run
python3 -m harness launch --project /path/to/assignment --mode inherited --model gpt-6.1-sol
```

`install-skills`는 동명 스킬을 보존하고 결과를 출력합니다. 새 세션에서 Skill 발견을 확인하고 리드 프롬프트를 원래 과제 지침에 맞게 전달합니다. 다른 프로젝트는 하네스 경로의 Skill을 자동 발견하지 않습니다. 역할 파일에서 모델을 지정할 수 없는 환경은 `role NAME`으로 프롬프트만 출력해 제공된 새 에이전트에 전달합니다. 서브에이전트도 없으면 순차 수행하며 독립 검토 제한을 기록합니다.

모델별 라우팅은 `launch --mode routed`로 선택합니다. 역할 파일 모델·강도가 spawn 인자보다 우선할 수 있습니다. `launch --model`은 부모만 지정합니다. 호환 번들은 역할에서 값을 강제하지 않으므로 부모·spawn·설치 환경의 기본값이 적용됩니다. 실제 모델은 로그로 확인해야 합니다. 별도 번들은 `configure NEW_DIRECTORY --mode inherited`로 만들고 `launch --bundle NEW_DIRECTORY`로 선택합니다. 기존 번들은 덮어쓰지 않습니다.

## Skill과 도구

[17개 Skill의 전체 목록과 자동 선택 조건](docs/skills.md)을 제공합니다. 공통 개발 7개, 유형별 6개, 시험 운영 4개이며 `name`·`description`으로 후보를 발견하고 본문과 references를 필요한 때만 읽습니다. 모든 Skill을 한꺼번에 로딩하지 않습니다. 이 세션에서 실제 자동 발견 목록에 표시됐고, smoke의 requirements 에이전트가 선택한 Skill을 읽었습니다.

기본 도구는 제공 Codex·터미널·Git·Python 표준 라이브러리입니다. CSV 스키마, 결측·중복·날짜·금액 검증, Decimal 집계·0 분모 처리, 로컬 JSON 오류 처리와 HTTP 회귀 검사를 제공합니다. MCP·플러그인은 기본으로 설치하거나 설정하지 않습니다. [도구·네트워크·인증·라이선스 범위와 대안](docs/tools-and-licenses.md)을 확인하세요.

## 실제 예제와 검사

```sh
make check
python3 -m harness data examples/data/sales.csv
python3 -m harness demo --port 8766
python3 -m harness plan-check examples/task-plan.json
python3 -m unittest discover -s examples/bugfix/starter -v
```

마지막 starter 명령은 의도한 결함으로 실패해야 합니다. 별도 `solution`은 `make check`에 포함됩니다. 업무 보드는 메모리에 저장하며 종료 시 초기화됩니다. 화면은 사용자가 브라우저 미리보기로 직접 확인합니다. HTTP 검사·HTML 검사는 실제 화면 수동 검증과 구분합니다.

실제 Codex 실행 benchmark는 정적 검사와 달리 AI 사용량을 소비합니다.

```sh
python3 -m harness benchmark --mode smoke --routing inherited --timeout 180
python3 -m harness benchmark --mode single --routing routed --timeout 480
python3 -m harness benchmark --mode multi --routing routed --timeout 480
```

원시 로그·자식 세션·요청/실제 모델·파일·실행 시간을 `.harness/runs/`에 보관합니다. CLI JSONL에서 생성 이벤트가 누락되는 환경은 자식 세션의 실제 부모 관계·문맥 요청·타임스탬프로 보완합니다. 증거가 없으면 검증 성공으로 처리하지 않습니다. 세션 저장 방식이 다르면 모델·문맥·병렬 검증은 미확인일 수 있습니다. 원시 로그나 인증을 공개 커밋하지 않습니다.

검증 결과와 한계는 [측정 보고서](docs/benchmark-results.md), 결함과 수정은 [초기 독립 리뷰](docs/reviews/initial.md)·[최종 감사](docs/reviews/final.md)에 기록합니다. 작은 합성 과제 한 번의 결과를 180분 실제 과제 성능으로 일반화하지 않습니다.

## 시험 당일

[시험 실행 안내](docs/exam-runbook.md)의 환경 확인 → 요구사항/탐색 → 작업 계약 → 필요한 병렬 구현 → 독립 검증 → 리드 통합 → 로컬 전달을 따릅니다. 180분 중 검증 30분·전달 10분을 확보합니다. 시험 중 Git Push·외부 업로드·업무 데이터 전송·브라우저/GUI/Computer Use 자동 조작·Codex 업데이트를 하지 않습니다. 플랫폼 인증·보안·감독 제한을 변경하지 않습니다. AI 금지 필기 평가가 시작되면 AI 사용을 중단합니다.
