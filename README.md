# Codex Harness · SK hynix AI Hackathon

180분 개발 과제를 위한 Codex 전문 에이전트 팀과 검증 도구입니다. **설치된 Codex를 그대로 사용**하며 Python 3.11+ 외에 런타임 의존성이 없습니다. 실제 과제의 요구사항·기존 코드·AGENTS.md를 우선합니다. 연습 예제는 실제 제출물의 대체품이 아닙니다.

```sh
git clone https://github.com/HyeongiJeon/CodexHarness.git
cd CodexHarness
python3 -m harness doctor
make check
python3 -m harness launch --dry-run
```

## 가장 쉬운 사용법

CodexHarness와 작업할 프로젝트가 **같은 상위 폴더**에 있다면, 작업 프로젝트 폴더에서 시작합니다. 경로가 다르면 `../CodexHarness` 부분만 실제 CodexHarness 경로로 바꾸세요.

```bash
cd /path/to/my-project
../CodexHarness/start.sh dev
```

명령 끝의 이름만 바꾸면 됩니다. `start.sh`가 Python 3.11+ 실행 파일을 `python3` 또는 `python`에서 자동으로 찾아 사용합니다. 각 전문 세션은 **별도 터미널에서 실행**할 수 있습니다.

| 명령 끝 | 하는 일 |
| --- | --- |
| `dev` | 개발·수정 (기본) |
| `explain` | 기존 코드 쉽게 설명, 읽기 전용 |
| `optimize` | 속도·알고리즘 최적화 (별도 Git 작업공간) |
| `qa` | 기능·API·DB 테스트, 오류 보고 |
| `preview` | 웹 서버·포트·미리보기 오류 진단 |

예를 들어 개발 후 검사를 맡기려면 다른 터미널에서 `../CodexHarness/start.sh qa`를 실행하면 됩니다. 모든 모드의 모델은 **`gpt-6.1-sol`**입니다.

### 세션 간 결과 공유도 말로 요청하면 됩니다

세션의 **대화 내용 전체가 자동 공유되지는 않지만**, 같은 프로젝트의 주요 결정·QA 결함·최적화 결과는 공유 상태(`state`)에 기록하고 다른 세션에서 읽을 수 있습니다.

- QA 채팅: **“검사 결과와 발견한 결함을 공유 상태에 기록해줘.”**
- DEV 채팅: **“공유 상태를 읽고 QA가 발견한 결함을 정리해줘.”**

직접 기록을 보고 싶다면 작업 프로젝트 폴더에서 `PYTHONPATH=../CodexHarness python3 -m harness state show`를 실행하세요. 세션 간 공유는 **기록된 내용만** 전달하며, 최적화 작업공간의 미병합 결과는 원본 프로젝트에 아직 적용되지 않은 것으로 표시됩니다.

### `--exam`은 언제 붙이나요?

```bash
# 일반 개발
../CodexHarness/start.sh dev

# 180분 실전 시험 진행
../CodexHarness/start.sh dev --exam
```

| 구분 | `dev` | `dev --exam` |
| --- | --- | --- |
| 시작 지침 | `sessions/dev.md` | `EXAM_START.md` |
| 작업 방식 | 요구사항·계획 설명 → 승인 후 구현 | 시험 환경 확인 → 180분 시간 관리 → 승인 후 단계별 구현 |
| 별도 기록 | 필요 시 공유 상태 기록 | 시험 후 본인이 설명할 수 있도록 개발 근거·결정·검증 기록 강조 |
| 모델·역할·Skill | Sol 6.1 / 전문팀 | 동일 |

**차이는 모델이나 권한이 아니라 시작 지침과 시간 관리 방식**입니다. `--exam`은 `dev` 전용이며, 시험 환경의 금지사항(Git push·외부 전송·브라우저 자동화 등)은 플래그와 무관하게 지켜야 합니다. `--exam` 자체가 해당 작업을 기술적으로 차단하는 보안 장치는 아닙니다.

이미 열려 있는 Codex 세션에서 새 런처를 실행할 수 없다면 `CodexHarness/EXAM_START.md 읽고 시작해줘.`라고 요청할 수 있습니다([EXAM_START.md](EXAM_START.md)). 다만 기존 세션에는 새 모델·역할 설정이 소급 적용되지 않습니다. 사전체험은 [START_HERE.md](START_HERE.md)를 참고하세요.

웹 미리보기 진단 명령: `python3 -m harness web-probe http://127.0.0.1:PORT/ --path /api/...` (CodexHarness 폴더에서 실행; localhost HTTP 전용, 브라우저 미사용).

`gpt-6.1-sol`은 이 준비 환경에서 실행 확인한 ID입니다. 시험에서도 모델은 `gpt-6.1-sol` 하나뿐이며, 접근이 확인되지 않으면 다른 모델로 대체하지 말고 오류로 보고합니다. Codex나 Python 설치·업데이트 스크립트는 포함하지 않습니다. `make`가 없으면 Makefile에 적힌 Python 명령을 직접 실행합니다.

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
| `.codex/config.toml`, `.codex/agents/` | 모든 역할 `gpt-6.1-sol` 고정 + 역할별 추론 강도, 최대 4개 설정값·깊이 1 |
| `.agents/skills/` | 조건별 24개 Skill·필요할 때만 읽는 references |
| `harness/` | doctor·명시적 역할 실행기·계획 검사·안전한 Skill 복사·CSV·HTTP 예제·실제 benchmark |
| `examples/`, `tests/`, `benchmarks/` | 합성 입력·의도적 결함·회귀 검사·재현 가능한 측정 결과 |
| `.harness/` | 원시 실행 증거의 로컬 보관; Git 제외 |

프로젝트 설정 자동 로딩은 **신뢰된 프로젝트 여부와 설치 버전**에 달려 있습니다. `launch`는 선택한 번들의 역할 경로를 절대 경로 `-c` 인자로 전달합니다. 홈 설정·인증·신뢰·권한·관리 제한을 바꾸지 않습니다. 제공 환경에서 역할 선택이 금지된 경우 실행기를 쓰지 않고 허용된 순차 작업으로 전환합니다.

| 역할 | 모델 | 추론 | 책임 |
| --- | --- | --- | --- |
| Main / lead | `gpt-6.1-sol` | high | 기준·시간·위임·파일 소유권·최종 실행 |
| requirements | `gpt-6.1-sol` | high | 필수·선택·질문·수용 기준 |
| architect | `gpt-6.1-sol` | high | 최소 구조·인터페이스·의존성 |
| explorer | `gpt-6.1-sol` | medium | 기본 읽기 전용 저장소·문서 Corpus 탐색 |
| core | `gpt-6.1-sol` | high | 핵심 로직·API·복잡한 수정 |
| frontend | `gpt-6.1-sol` | medium | 화면·상태·접근성·핵심 흐름 |
| data | `gpt-6.1-sol` | high | 정제·대용량 JOIN·정확한 계산 검증 |
| qa | `gpt-6.1-sol` | high | 실제 재현·테스트·회귀 |
| reviewer | `gpt-6.1-sol` | high | 새 문맥의 독립 결함·원문 근거 감사 |
| docs | `gpt-6.1-sol` | medium | 사실 기반 결정·사용법·증거 |
| synthesizer | `gpt-6.1-sol` | high | 근거팩 종합·상충·조건부 결론 |

**모델 정책: `gpt-6.1-sol` 단일 모델.** 모든 메인 세션과 서브에이전트가 같은 모델을 쓰며 역할별 모델 라우팅·대체 모델·`--model`/`--routing` 옵션은 없다(Sol을 쓸 수 없으면 오류로 중단). 역할별 전문 지침과 추론 강도만 다르다. 설정 등록이나 모델 카탈로그 목록은 호출 성공의 증거가 아니며 실제 실행으로만 확인한다. 과거 benchmark·리뷰 문서(`docs/benchmark-results.md`, `docs/reviews/`, `docs/prose-trial-results.md`, `benchmarks/`)의 Terra/Luna 기록은 당시 실행의 **역사적 증거**이며 현재 정책으로 바꾸지 않았다. 모든 역할을 항상 실행하지 않습니다. 작은 수정은 리드가 처리하고, 독립 작업이 충분할 때만 병렬화합니다. Astra는 사용하지 않습니다.

설치 CLI는 **0.163.0**입니다. [공식 문서·버전별 소스 조사](docs/codex-research.md)는 최신 소스 스냅샷과 설치 버전을 분리합니다. V1의 `fork_context=false`, hosted 도구의 `fork_turns="none"`, 동시 한도 계산은 같은 API라고 가정하지 않습니다. 이 환경의 실제 실행에는 hosted 형태가 노출됐습니다. 새 문맥도 파일 시스템은 공유합니다. [계획 계약](examples/task-plan.json)과 `plan-check`는 소유권 충돌·의존성을 확인하지만 파일 잠금은 아닙니다.

## 전문 세션 원클릭 실행 (V2)
```bash
./CodexHarness/start.sh dev|explain|optimize|qa|preview [--project DIR] [--dry-run] [--exam]
```
Codex가 **시작되기 전에** 프로젝트 탐지(`--project` 또는 현재 git 루트)·`validate`·스택에 맞는 Skill 설치(기존 파일 보존, 반복 실행 안전)·`gpt-6.1-sol` 모델 카탈로그 참고 확인(목록에 없어도 실행을 차단하지 않으며, 실제 호출 실패 시 다른 모델로 대체하지 않음)·Skill 인식 확인(`codex debug prompt-input`, 모델 호출 없음)을 하고 보고한 뒤 세션을 시작한다. 이미 실행 중인 Codex(Cofa 등)에는 소급 적용되지 않는다: `--dry-run`으로 준비하고 새 세션에서 시작한다.

| 모드 | 내용 | 강제되는 것 / 지침뿐인 것 |
|---|---|---|
| `dev` | 협업 개발 팀(`--exam`이면 `EXAM_START.md` 승인 게이트) | 승인 게이트는 지침 |
| `explain` | 읽기 전용 코드·구조 설명 | `codex -s read-only` 플래그로 강제(플랫폼이 더 엄격하면 그쪽) |
| `optimize` | 측정 기반 최적화, `harness measure` | 별도 git worktree(마지막 커밋 기준, 미커밋 변경 제외); git이 아니면 `--in-place` 필요 |
| `qa` | QA Lead(기존 qa/data/reviewer 재사용), PASS/FAIL/UNVERIFIED 보고(`templates/qa-report.md`) | 제품 코드 비수정은 지침뿐 |
| `preview` | 웹/미리보기 계층 진단, `preview-baseline`, [Cofa 런북](docs/preview/cofa-runbook.md) | 지침 |

세션 공유 기록은 프로젝트 밖(`.harness/sessions/`)에 `harness state add|show`로 남기며, 기록마다 작업공간(worktree·브랜치·커밋)을 저장하며, 그 작업공간이 기록 이후 바뀌면 `stale`, 별도 worktree 결과가 프로젝트에 병합되지 않았으면 `not_integrated`로 따로 표시한다. 추가 CLI: `measure`(반복 시간·최대 RSS·출력 해시 비교), `data sqlite`(읽기 전용 스키마·정합성·SELECT), `data profile`의 수치 통계·이상치 후보·중복, `web-probe --host-header/--origin`과 바인드 주소 보고.

## 기존 과제 프로젝트에서 사용

하네스 저장소의 AGENTS.md나 설정을 원래 프로젝트에 덮어쓰지 않습니다. 다음 명령은 하네스 디렉터리에서 실행합니다.

```sh
python3 -m harness install-skills --project /path/to/assignment --skill parallel-implementation --skill completion-verification
python3 -m harness role lead
python3 -m harness launch --project /path/to/assignment --dry-run
python3 -m harness launch --project /path/to/assignment
```

`install-skills`는 동명 스킬을 보존하고 결과를 출력합니다. 새 세션에서 Skill 발견을 확인하고 리드 프롬프트를 원래 과제 지침에 맞게 전달합니다. 다른 프로젝트는 하네스 경로의 Skill을 자동 발견하지 않습니다. 역할 파일에서 모델을 지정할 수 없는 환경은 `role NAME`으로 프롬프트만 출력해 제공된 새 에이전트에 전달합니다. 서브에이전트도 없으면 순차 수행하며 독립 검토 제한을 기록합니다.

`launch`는 체크인된 `.codex/` 번들(모든 역할 `gpt-6.1-sol`)을 절대 경로 `-c` 인자로 전달하고 `-m gpt-6.1-sol`을 명시한다. 별도 번들은 `configure NEW_DIRECTORY`로 만들고 `launch --bundle NEW_DIRECTORY`로 선택하며, `gpt-6.1-sol` 이외 모델이 들어 있으면 거부한다. 기존 번들은 덮어쓰지 않는다. 실제 모델은 로그로 확인해야 한다.

## Skill과 도구

[24개 Skill의 전체 목록과 자동 선택 조건](docs/skills.md)을 제공합니다. 기존 17개에 문서 검색·근거 종합·출처 검증 3개, 웹 런타임 디버깅·UI 패턴·흐름 검증 3개를 추가했으며 `name`·`description`으로 후보를 발견하고 본문과 references를 필요한 때만 읽습니다. 모든 Skill을 한꺼번에 로딩하지 않습니다. 기존 smoke에서는 requirements 에이전트가 선택한 Skill을 실제 읽었습니다. 새 Skill·역할은 새 세션에서 발견을 확인합니다.

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
python3 -m harness benchmark --mode smoke --timeout 180
python3 -m harness benchmark --mode single --timeout 480
python3 -m harness benchmark --mode multi --timeout 480
```

원시 로그·자식 세션·요청/실제 모델·파일·실행 시간을 `.harness/runs/`에 보관합니다. CLI JSONL에서 생성 이벤트가 누락되는 환경은 자식 세션의 실제 부모 관계·문맥 요청·타임스탬프로 보완합니다. 증거가 없으면 검증 성공으로 처리하지 않습니다. 세션 저장 방식이 다르면 모델·문맥·병렬 검증은 미확인일 수 있습니다. 원시 로그나 인증을 공개 커밋하지 않습니다.

검증 결과와 한계는 [측정 보고서](docs/benchmark-results.md), 결함과 수정은 [초기 독립 리뷰](docs/reviews/initial.md)·[최종 감사](docs/reviews/final.md)에 기록합니다. 작은 합성 과제 한 번의 결과를 180분 실제 과제 성능으로 일반화하지 않습니다.

초기 하네스 실측: **단일 91.7초 / 멀티 207.2초**, 두 구성 모두 A/B/C 통과입니다. 이 작은 과제에서 멀티가 더 느렸습니다. 초기 33개 검사·익명 clone 검증 기록은 위 보고서에 보존했습니다. 데이터·문서 강화 후의 현재 검사와 측정은 아래 보고서에 구분합니다. 화면 수동 검증과 시험 당일 기능·모델 접근성은 미확인입니다.

## 대용량 데이터·다중 문서

기존 작은 예제와 별도로 스트리밍 CSV/JSONL·디스크 JOIN/중복 제거, 혼합 문서 추출·SQLite 검색, 크기 제한 Evidence Pack, 원문 해시/위치/인용 검증과 사실·충돌·근거 부족 판정을 제공합니다. 원문 전체를 모델에 넣거나 외부 업로드하지 않습니다.

```sh
python3 -m harness resources
python3 -m harness data profile examples/intelligence/data-a.csv
python3 -m harness corpus index examples/intelligence/documents --db .harness/corpus.db
python3 -m harness corpus evidence-pack --db .harness/corpus.db --query FACT --max-chars 10000 --output .harness/pack.json
python3 -m harness evidence verify .harness/pack.json
python3 -m harness evidence synthesize .harness/pack.json --entity LOT-42 --as-of 2026-10-30
```

100만 행 JOIN은 **26.36초·피크 RSS 34.6MiB**, 120문서의 핵심 근거 5개는 **7,066자** 팩으로 보존했습니다. 일반 자연어의 자동 의미 이해나 모든 자료의 정확도를 보장하는 수치는 아닙니다. 일반 문서 해석은 제공 Codex와 독립 원본 감사를 이용하며 결정적 종합 엔진은 명시적 FACT 원문 레코드를 처리합니다. [실행법·지원 범위](docs/intelligence.md), [정확한 벤치마크 조건·한계](docs/intelligence-results.md), [독립 감사](docs/reviews/intelligence.md)를 확인하세요.

## 시험 당일

[시험 실행 안내](docs/exam-runbook.md)의 환경 확인 → 요구사항/탐색 → 작업 계약 → 필요한 병렬 구현 → 독립 검증 → 리드 통합 → 로컬 전달을 따릅니다. 180분 중 검증 30분·전달 10분을 확보합니다. 시험 중 Git Push·외부 업로드·업무 데이터 전송·브라우저/GUI/Computer Use 자동 조작·Codex 업데이트를 하지 않습니다. 플랫폼 인증·보안·감독 제한을 변경하지 않습니다. AI 금지 필기 평가가 시작되면 AI 사용을 중단합니다.
