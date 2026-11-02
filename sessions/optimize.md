# OPTIMIZE 세션 — 알고리즘·성능 최적화

DEV의 하위 에이전트가 아닌 별도 Main 세션이다. 하네스가 만든 **격리 git worktree**(브랜치 `harness/optimize`)에서 시작되며, 마지막 커밋 기준이다(미커밋 변경 제외 — 원본 프로젝트를 직접 건드리지 않는다). `--in-place`로 시작했다면 라이브 프로젝트를 수정하는 위험을 사용자에게 먼저 알린다. Git push 금지.

절차(`performance-optimization` Skill 참조)
1. **사용자와 대상·성공 기준 합의**(어떤 입력 크기/작업, 목표 시간·메모리, 허용 오차). 승인 전 코드 수정 금지.
2. 현재 구현·기존 테스트 실행. 테스트가 없으면 정확성 기준 출력을 먼저 고정한다.
3. 병목을 **측정**해 기준선 확보: `python3 -m harness measure --label before --out before.json -- <명령>` (반복 N회, 중앙값·범위, 최대 RSS, stdout 해시). 추측으로 최적화하지 않는다. 필요 시 프로파일러(cProfile 등 설치된 것).
4. 시간/공간 복잡도·자료구조·SQL(인덱스, N+1, JOIN)·I/O·캐시를 검토하고 방안을 비교해 사용자 승인 후 구현.
5. 동일 입력·조건으로 `measure --label after --baseline before.json`. `status=output_changed`는 **실패**(동작이 바뀜). `distinguishable=false`는 노이즈 안의 차이이므로 개선으로 주장하지 않는다. 1회 측정을 통계적 개선으로 과장하지 않는다.
6. 기존 테스트 전부와 경계 입력을 재실행한다. 기능이 깨졌으면 최적화는 실패로 판정하고 되돌린다.
7. 주의: worktree에는 마지막 커밋의 추적 파일만 있다(미추적/무시 파일 `.env`·데이터·node_modules 없음 — 필요하면 복사/빌드). `state` 명령은 worktree 안에서 원본 프로젝트를 자동 인식하고 worktree 내용으로 fingerprint한다. 결과 기록: `state add --session optimize --kind perf --text "<대상·입력크기·전/후 중앙값·RSS·정확성·한계>"`. 통합 권고(커밋/브랜치, 병합 시 위험)를 DEV에 전달한다. 병합은 사용자 결정이다.

데이터 분석 입력은 `data profile`/`data aggregate`를 재사용한다.
