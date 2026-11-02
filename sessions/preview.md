# PREVIEW 세션 — 웹 서버·미리보기 진단

목적: 서버는 뜨는데 미리보기가 실패하거나 빈 화면인 문제를 **계층별 증거**로 분리한다. 증거 없이 "해결됨"을 선언하지 않는다. 브라우저 자동화 금지. Cofa 전용 URL·설정은 공식 문서나 직접 관찰로 확인된 것만 안내한다(그 외는 "가정"이라 표시). 전체 절차는 `<CodexHarness>/docs/preview/cofa-runbook.md`.

계층(아래에서 위로 좁힌다)
1. 프로세스·서버 로그 → 2. 포트 리스닝·바인딩(`ss -ltnp`, `web-probe`의 `bind_addresses`) → 3. HTML/JS/CSS/API 응답(`web-probe URL --path /api/...`) → 4. 빌드·정적 경로(Vite `base`, 빌드 산출물, SPA 폴백) → 5. 프록시·Host·CORS·HMR WebSocket(`--host-header`, `--origin`) → 6. 플랫폼 미리보기 연결 → 7. 사용자가 직접 확인할 브라우저 Console/Network.

기준선: `python3 -m harness preview-baseline --port <P>` 로 최소 정적 서버를 띄워 같은 포트/미리보기 경로로 열어 보게 한다. 기준선이 보이고 앱이 안 보이면 앱 문제, 기준선도 안 보이면 플랫폼 미리보기 연결 문제로 좁힌다(단, 사용자의 수동 확인 결과가 필요).

보고: 계층별 판정(server / frontend / proxy / preview-connection / unverified), 실제 명령·출력, 사용자가 확인해야 할 항목. 결과는 `state add --session preview --kind preview --text ...`.
