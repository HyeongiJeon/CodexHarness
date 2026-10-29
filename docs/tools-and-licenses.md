# 도구·의존성·라이선스 범위

이 harness의 Python 런타임 의존성은 표준 라이브러리뿐이다. `pyproject.toml`의 `dependencies = []`가 기준이며 Python 3.11 이상을 요구한다. 실제 시험 프로젝트가 가진 의존성과 라이선스는 별도로 조사하고 기존 manifest·lockfile을 보존한다. 외부 패키지는 구체적 필요가 있을 때만 검토한다.

| 기본 도구 | 용도 | 범위와 대안 |
| --- | --- | --- |
| `csv`, `io` | 합성 CSV 입력·출력 | 고정 스키마·인코딩·잘못된 행 처리 규칙을 명시한다. [Python CSV 문서](https://docs.python.org/3/library/csv.html) |
| `decimal.Decimal` | 금액 합산·명시적 반올림 | 이진 부동소수점 오차를 피하고 NaN·무한대·소수 자릿수·0 분모를 검사한다. [Decimal 문서](https://docs.python.org/3/library/decimal.html) |
| `datetime.date` | 날짜 파싱·달력 유효성 | 과제의 날짜 형식·시간대를 따르며 모호한 날짜를 추측하지 않는다. [datetime 문서](https://docs.python.org/3/library/datetime.html) |
| `http.server`, `urllib.request` | 로컬 데모·HTTP 검증 | 로컬 개발용이다. HTTP 응답은 화면 동작을 증명하지 않는다. [서버 문서](https://docs.python.org/3/library/http.server.html), [클라이언트 문서](https://docs.python.org/3/library/urllib.request.html) |
| `unittest`, `json`, `tomllib` | 동작·증거·설정 검사 | 기능 검사와 설정 검사를 구분하고 실제 명령·종료 코드를 기록한다. |
| 제공 Codex·네이티브 에이전트 | 역할 위임·구현·리뷰 | 설치·업데이트 불필요. 역할·모델 접근이 없으면 상속·순차 프롬프트로 전환한다. |
| Git, `make`, `rg` | 로컬 상태·검사·검색 | 외부 게시 불필요. `rg`가 없으면 사용 가능한 로컬 검색 도구를 쓴다. |

현재 저장소의 Python·HTML·연습 데이터는 이 프로젝트에서 작성한 코드와 합성 입력이다. 외부 OSS 구현을 복사해 포함하는 구조가 아니다. 공식 문서 링크는 참고 자료이며 해당 문서·저장소를 vendoring했다는 뜻이 아니다. 향후 외부 코드·폰트·이미지·데이터를 넣으면 출처, 버전, 라이선스, 수정, 배포 의무를 따로 기록한다. 저작권·이용 조건 확인 없이 “표준 라이브러리만 사용하므로 모든 도구도 같은 라이선스”라고 주장하지 않는다.

| 구성 요소 | 라이선스·이용 조건 확인 위치 | 구분 |
| --- | --- | --- |
| Python·표준 라이브러리 | [Python 라이선스](https://docs.python.org/3/license.html): PSF License 및 포함 구성 요소 고지 | Python 배포물의 조건이며 harness 원본 코드의 라이선스 부여를 대신하지 않는다. |
| OpenAI Codex 공개 CLI 소스 | [공식 저장소 LICENSE](https://github.com/openai/codex/blob/main/LICENSE): Apache-2.0 | 제공 실행 파일·서비스의 실제 버전과 서비스 이용 조건은 별도다. 이 저장소에 CLI 소스를 복사하지 않는다. |
| Git | [공식 Git 라이선스 안내](https://git-scm.com/about/free-and-open-source): GPLv2 | 외부 개발 도구이며 harness의 런타임 Python 의존성이 아니다. |
| GNU Make | [공식 GNU Make 안내](https://www.gnu.org/software/make/): GPL | 외부 검사 편의 도구다. Makefile의 실제 Python 명령으로도 검사할 수 있다. |
| ripgrep | [공식 ripgrep 라이선스 안내](https://github.com/BurntSushi/ripgrep#license): MIT 또는 Unlicense | 선택 검색 도구다. |

## MCP·플러그인: 기본 사용 안 함

기본 작업에는 MCP·플러그인 설치나 인증이 필요 없다. 역할 TOML은 모델·지침을 정의하며 외부 계정 권한을 부여하지 않는다. 자식이 외부 도구를 사용할 수 있는지도 실제 제공 도구와 부모 세션 설정으로 확인한다. 시험의 외부 전송 금지가 우선하므로 과제 코드·입력·로그를 문서 검색 서비스로 보내지 않는다.

| 선택 통합 | 기본 상태 | 사용을 검토하기 전에 확인할 사항 | 사용할 수 없을 때 |
| --- | --- | --- | --- |
| 공개 공식 문서 MCP | **비활성·미설정** | 시험 규칙의 네트워크 허용, 공식 서버 주소·문서, 인증 필요 여부, 실제 전송 항목, 제공 도구와 권한. 준비 단계에서만 검증하고 규칙상 금지면 사용하지 않는다. | 제공 문서·로컬 저장 문서·설치 CLI `--help`를 읽는다. |
| 업무 계정 MCP·플러그인 | **비활성·미설정** | 과제에 필수인지, 명시적 허가, 별도 계정 인증, 데이터 반출 규정과 서비스 조건. 이 harness는 연결하지 않는다. | 합성 fixture와 로컬 입력을 사용하고 미확인 정보를 기록한다. |

MCP의 공식 설정 개념은 [Codex MCP 안내](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), 플러그인의 개념은 [공식 플러그인 안내](https://learn.chatgpt.com/docs/plugins)를 참조한다. 연결 필요성을 이유로 관리 제한을 바꾸거나 인증 파일을 복제하지 않는다. 이 링크 자체는 연결·접근·라이선스 검증을 수행했다는 증거가 아니다.
